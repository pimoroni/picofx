import gc
import time

from mighty_fx import MightyFX, SPCE
from timing import Pacer
from playback import GIFPlayer
from screens import Screen280
from picovector import color, font, image, rect, shape

"""
Draw a status panel for the company that made the board, a wordmark over a cycling ribbon, a
coin badge, a few statuses, and the seven RGB outputs as its production line.

Everything is drawn at half the panel's size and doubled on the way out, so every pixel on the
glass is a square of four, for a quarter of the canvas and a quarter of the drawing. The ribbon
is dithered along its own direction, since 16 levels a channel turn a gradient into bands.

The seven outputs are a production line, one stage live at a time with its lamp lit on the glass
and its LED lit on the board below. One level per output, read by both, so the two cannot drift
apart. The interface is built once and blitted as the background, so a frame draws only what moves.

Press "Boot" to exit the program.

Section: Billboards and panels
"""

# Constants for drawing
EMBLEM = "/examples/assets/pirate_coin_emblem.gif"
WORDMARK_FACE = "/rom/fonts/PoppinsBlack.af"  # A vector face, drawn large and reduced with the render
# Poppins Black's measured lettering, its height and where it starts below the drawn y, as fractions of the size
LETTERING_TALL = 0.309
LETTERING_DOWN = 0.697
BODY_FACE = font.winds                  # The narrowest pixel face, which is what the statuses need
ROTATION = 90                           # Quarter turn, to suit how the screen is mounted
REDUCE = 2                              # The render is drawn this much larger and reduced onto the canvas

TEXT_COLOUR = color.black               # The type, the bullets and the wordmark
BACKGROUND = color.white
RULE = color.rgb(150, 150, 150)         # Structure and the numbers, which are not content
PLATE = color.rgb(228, 228, 228)        # Behind the badge and under the line, light so the screen stays white
PLATE_EDGE = color.rgb(190, 190, 190)
PLATE_SHADOW = color.rgb(206, 206, 206)  # A plate sits a pixel above the interface, so it casts one
PLATE_BEVEL = color.white               # And catches the light along its inside edge
SCREW = color.rgb(168, 168, 168)
PLATE_R = 3                             # Corner radius, in the interface's own pixels

WORDMARK = "PIMORONI"
TAGLINE = "PURVEYORS OF MAKER GOODS"

# The ribbon, two hues turning at one rate so the pair keeps its relationship
RIBBON_MS = 9000                        # One turn of the wheel
RIBBON_SPREAD = 70                      # How far apart the two hues sit on it, of 255
RIBBON_SAT = 255
RIBBON_VALUE = 210                      # Short of full, a hue at 255 having little to give against white type
RIBBON_STEP = 2                         # Pixels a band, the gradient being drawn band by band
RIBBON_DITHER = 8                       # Jitter on every other band, which scatters the panel's own banding

# The statuses, each a label, its value and the colour it carries. A count stays in the text colour
STATE_GOOD = color.rgb(0, 136, 0)       # Whole levels of the 16 the screens drive a channel at, and both
STATE_BAD = color.rgb(204, 0, 0)        # short of full, as a saturated hue gives little against white
STATUSES = (("CREW ON DUTY", "40", TEXT_COLOUR),
            ("FOOD VAN", "NOT HERE", STATE_BAD),
            ("ROOF", "NOT LEAKING", STATE_GOOD))

# The line, one stage to an output, so a stage's number is the number printed beside its LED
STAGES = ("PICK", "PLACE", "REFLOW", "TEST", "FLASH", "PACK", "SHIP")
HEADING = "ASSEMBLY LINE"               # What the row of lamps is, since seven lights alone say nothing
STAGE_MS = 900                          # How long a stage holds before the board moves on
DIM = 0.08                              # What every output but the live one holds, so the line is never dark
LAMP_R = 3
# The lamp's light is drawn as rings, as bloom() lifts only what is bright
# and leaves a saturated red or blue unlit
GLOW_R = LAMP_R + 3                     # How far a lit lamp's light reaches onto the plate around it
SPRITE_R = GLOW_R + 1                   # And the pixel of clear margin past it the sprite keeps
GLOW_STEPS = 5                          # Rings it is built from, drawn largest first so they build inwards
GLOW_ALPHA = 40                         # What the innermost ring adds out of 255, each outer one a share of it
DOME_LIGHT = 190                        # The core a lit lamp shows, and the light unlit glass catches
CONSOLE_PAD = 2                         # How far the plate under the line reaches past what sits on it

# Create a MightyFX object with SP/CE A set up for a screen, and its RGB outputs for the line
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a, rotation=ROTATION)

# Half the panel each way and doubled by update(), a quarter of the pixels for the same picture
canvas = screen.canvas(screen.height // 2, screen.width // 2)
WIDTH, HEIGHT = canvas.width, canvas.height
wordmark_face = font.load(WORDMARK_FACE)
canvas.font = BODY_FACE

try:
    player = GIFPlayer(EMBLEM)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{EMBLEM}' is missing! Check it is on the board") from None

LINE_H = BODY_FACE.height + 1           # One line of type to the next
RIBBON_TOP = 22                         # The render above it is a wordmark and nothing else
RIBBON_H = BODY_FACE.height + 1
BODY_TOP = RIBBON_TOP + RIBBON_H + 4    # Clear of the ribbon, so the badge reads as an object of its own
PLATE_PAD = 3
BADGE_AT = (4, BODY_TOP)
STATUS_LEFT = BADGE_AT[0] + player.width + PLATE_PAD + 3
COIN_AT = rect(BADGE_AT[0], BADGE_AT[1], player.width, player.height)

NUMBER_TOP = HEIGHT - BODY_FACE.height  # The numbers sit at the foot, the lamps above them
NUMBER_NUDGE = 1                        # A digit reads better a pixel right of its lamp's centre
LAMP_Y = NUMBER_TOP - LAMP_R - 1
HEADING_TOP = LAMP_Y - LAMP_R - BODY_FACE.height - 2
STATUS_DOWN = 1                         # Squares the statuses against the badge, not its plate
BULLET_DOWN = 5                         # Near the middle of the type, not the top of its line
ROW_INSET = 4                           # Nudges the lamps if the panel and the connectors do not line up
CELL_W = (WIDTH - ROW_INSET * 2) / len(STAGES)

# The plate under the line reaches past the heading above it and the numbers below, and to both edges
CONSOLE_AT = (1, HEADING_TOP - CONSOLE_PAD)
CONSOLE_W = WIDTH - 2
CONSOLE_H = HEIGHT - CONSOLE_AT[1] - 1

# The background, everything that never changes
background = image(WIDTH, HEIGHT)
background.font = BODY_FACE
background.antialias = image.X4


# A scratch image to measure on, so the background's font is never changed
asker = image(8, 8)


def measure(face, text, size):
    """The advance a drawing of the text takes."""
    asker.font = face
    return asker.measure_text(text, font_size=size)[0]


def glyph_blanks(face, glyph, size, tall, down):
    """
    Measure the blank a glyph carries before and after its lettering, as measure_text returns the advance.

    Only the two end glyphs need it.
    """
    advance = measure(face, glyph, size)
    scratch = image(round(advance) + 8, round(tall))
    scratch.antialias = image.X4
    scratch.font = face
    scratch.pen = TEXT_COLOUR
    scratch.text(glyph, 4, down, font_size=size)

    raw, stride = scratch.raw, scratch.stride
    left, right = scratch.width, -1
    for y in range(scratch.height):
        row = bytes(raw[y * stride:y * stride + scratch.width * 4])
        drawn = row.lstrip(b"\0")
        if not drawn:
            continue

        left = min(left, (len(row) - len(drawn)) // 4)
        right = max(right, (len(row.rstrip(b"\0")) - 1) // 4)

    if right < 0:
        # A glyph that draws nothing has no blank, or the line would be thrown across the interface
        return 0, 0

    return left - 4, advance - (right - 4) - 1


def centred_on_lettering(face, text, size, tall, down, across=None):
    """Find the x to draw the text at for its lettering to sit centred, calculated once, not every frame."""
    before = glyph_blanks(face, text[0], size, tall, down)[0]
    after = glyph_blanks(face, text[-1], size, tall, down)[1]
    return ((across or WIDTH) - (measure(face, text, size) - before - after)) / 2 - before


def cell_centre(index):
    """Where a stage sits across the interface, which is where its output sits along the board."""
    return ROW_INSET + CELL_W * (index + 0.5)


def plate(render, x, y, w, h):
    """
    Draw a raised plate in the interface's coordinates, shadow, face, lit edge and screws.

    It is drawn at twice size so its edges reduce to shading.
    """
    box = (x * REDUCE, y * REDUCE, w * REDUCE, h * REDUCE)
    corner = PLATE_R * REDUCE

    render.pen = PLATE_SHADOW
    render.shape(shape.rounded_rectangle(box[0] + REDUCE, box[1] + REDUCE, box[2], box[3], corner))
    render.pen = PLATE
    render.shape(shape.rounded_rectangle(*box, corner))
    render.pen = PLATE_BEVEL
    render.shape(shape.rounded_rectangle(box[0] + REDUCE, box[1] + REDUCE, box[2] - REDUCE * 2,
                                         box[3] - REDUCE * 2, corner).stroke(1))
    render.pen = PLATE_EDGE
    render.shape(shape.rounded_rectangle(*box, corner).stroke(2))

    for across in (x + PLATE_R, x + w - PLATE_R):
        for down in (y + PLATE_R, y + h - PLATE_R):
            render.pen = SCREW
            render.circle(across * REDUCE, down * REDUCE, 1.4 * REDUCE)
            render.pen = PLATE_BEVEL
            render.circle(across * REDUCE, down * REDUCE, 0.5 * REDUCE)


def build_render():
    """Render the continuous-tone half, wordmark and plates, large and reduce it onto the background once."""
    render = image(WIDTH * REDUCE, HEIGHT * REDUCE)
    render.antialias = image.X4
    render.font = wordmark_face
    render.pen = BACKGROUND
    render.clear()

    render.pen = TEXT_COLOUR
    room = RIBBON_TOP * REDUCE - 6                       # The render's own pixels, above the ribbon
    size = room / LETTERING_TALL
    wide = measure(wordmark_face, WORDMARK, size)
    across = render.width - 8
    if wide > across:                                    # A heavy face runs out of width before height
        size *= across / wide

    # Measured at the y it is drawn at, as this face draws below its line
    down = 3 - LETTERING_DOWN * size
    render.text(WORDMARK, centred_on_lettering(wordmark_face, WORDMARK, size, room + 8, down, render.width),
                down, font_size=size)

    plate(render, BADGE_AT[0] - PLATE_PAD, BADGE_AT[1] - PLATE_PAD,
          player.width + PLATE_PAD * 2, player.height + PLATE_PAD * 2)

    # One plate under the heading, lamps and numbers, so the three read as one instrument
    plate(render, CONSOLE_AT[0], CONSOLE_AT[1], CONSOLE_W, CONSOLE_H)

    # The rail is drawn first so each housing breaks it, which shows a board travels between lamps
    render.pen = PLATE_EDGE
    render.rectangle(cell_centre(0) * REDUCE, LAMP_Y * REDUCE - 1,
                     (cell_centre(len(STAGES) - 1) - cell_centre(0)) * REDUCE, 2)

    background.blit(render, rect(0, 0, render.width, render.height), rect(0, 0, WIDTH, HEIGHT), image.BILINEAR)
    del render
    gc.collect()


def build_background():
    """Lay the render, then the pixel-accurate type over it, as what is read is never reduced."""
    build_render()

    # Each status as a bullet, its label in the text colour and its state in its own
    for index, (label, state, tone) in enumerate(STATUSES):
        top = BODY_TOP + STATUS_DOWN + index * LINE_H
        lead = f"{label} = "
        background.pen = TEXT_COLOUR
        background.rectangle(STATUS_LEFT, top + BULLET_DOWN, 3, 3)
        background.text(lead, STATUS_LEFT + 6, top, 1)
        background.pen = tone
        background.text(state, STATUS_LEFT + 6 + measure(BODY_FACE, lead, 1), top, 1)

    # The numbers, which are read, not looked at, so they are type and not part of the render
    background.pen = RULE
    for index in range(len(STAGES)):
        number = str(index + 1)
        background.text(number, cell_centre(index) - background.measure_text(number, font_size=1)[0] / 2
                    + NUMBER_NUDGE, NUMBER_TOP, 1)


def lamp_origin(index):
    """The whole pixel a lamp's sprite is blitted at, as the sprite carries its centre's fraction."""
    return int(cell_centre(index)) - SPRITE_R, LAMP_Y - SPRITE_R


def build_lamp(index, lit):
    """Render one lamp, housing, light and halo, at twice size, reduced to a sprite clear outside it."""
    origin = lamp_origin(index)
    side = SPRITE_R * 2
    render = image(side * REDUCE, side * REDUCE)
    render.antialias = image.X4

    at = ((cell_centre(index) - origin[0]) * REDUCE, (LAMP_Y - origin[1]) * REDUCE)
    inside = (LAMP_R + 1) * REDUCE      # The housing's inside edge, where its rim begins

    if lit:
        # The plate around a lit lamp takes its colour, and the outer ring stops short of the sprite's edge
        for step in range(GLOW_STEPS):
            reach = GLOW_R - step * (GLOW_R - LAMP_R - 1) / GLOW_STEPS
            render.pen = LIT_HUES[index].with_alpha(GLOW_ALPHA * (step + 1) // GLOW_STEPS)
            render.circle(at[0], at[1], reach * REDUCE)

    # The rim is a disc with the face and light inside it,
    # as a one-pixel stroked ring takes the light's colour on its diagonals
    render.pen = PLATE_EDGE
    render.circle(at[0], at[1], inside + REDUCE)
    render.pen = PLATE                  # Opaque, so the rail passing behind the lamp stops at it
    render.circle(at[0], at[1], inside - 1)
    render.pen = LIT_HUES[index] if lit else HUES[index].with_alpha(round(255 * DIM))
    render.circle(at[0], at[1], inside - 1)

    # A lit lamp's core sits centred, an unlit one's is the light its glass catches from the room
    render.pen = color.white.with_alpha(DOME_LIGHT if lit else DOME_LIGHT // 3)
    if lit:
        render.circle(at[0], at[1], LAMP_R * 0.45 * REDUCE)
    else:
        render.circle(at[0] - LAMP_R * 0.4 * REDUCE, at[1] - LAMP_R * 0.4 * REDUCE,
                      LAMP_R * 0.35 * REDUCE)

    sprite = image(side, side)
    sprite.blit(render, rect(0, 0, render.width, render.height), rect(0, 0, side, side), image.BILINEAR)
    del render
    gc.collect()
    return sprite


def draw_ribbon(elapsed):
    """
    Draw the ribbon band by band, two hues cycling together.

    Every other band is nudged half a level, which stipples the banding.
    """
    turn = (elapsed % RIBBON_MS) * 255 // RIBBON_MS     # How far round the wheel the ribbon has turned, of 255
    for band in range(0, WIDTH, RIBBON_STEP):
        across = band / WIDTH
        hue = turn + round(RIBBON_SPREAD * across)
        value = RIBBON_VALUE + (RIBBON_DITHER if (band // RIBBON_STEP) % 2 else -RIBBON_DITHER)
        canvas.pen = color.hsv(hue, RIBBON_SAT, min(255, value))
        canvas.rectangle(band, RIBBON_TOP, RIBBON_STEP, RIBBON_H)

    canvas.pen = BACKGROUND
    canvas.text(TAGLINE, TAGLINE_AT, RIBBON_TOP, 1)


def levels_at(elapsed):
    """Which stage is live, and each output's level, that one full and the rest just alive."""
    live = (elapsed // STAGE_MS) % len(STAGES)
    return live, tuple(1.0 if index == live else DIM for index in range(len(STAGES)))


# Values short of full, as a hue at 255 washes out against white. A lit lamp goes to full
HUES = tuple(color.hsv(index * 255 // len(STAGES), 255, 210) for index in range(len(STAGES)))
LIT_HUES = tuple(color.hsv(index * 255 // len(STAGES), 255, 255) for index in range(len(STAGES)))


def draw(elapsed, live):
    """Draw one frame, the background, the ribbon, the badge, the line's heading and the lamps."""
    canvas.blit(background, 0, 0)
    draw_ribbon(elapsed)
    canvas.blit(player.image, COIN_AT)

    # The heading says what the lamps are, and names the stage that is live, so a number on a lamp means
    # something to somebody reading the screen cold
    canvas.pen = TEXT_COLOUR
    canvas.text(HEADINGS[live], HEADING_AT[live], HEADING_TOP, 1)

    for index in range(len(STAGES)):
        canvas.blit(lamps[index][index == live], *lamp_origin(index))


marked = time.ticks_ms()
build_background()

# Labels for the ribbon and the lamps, measured once and centred on their lettering
HEADINGS = tuple(f"{HEADING} = {stage}" for stage in STAGES)
TAGLINE_AT = centred_on_lettering(BODY_FACE, TAGLINE, 1, BODY_FACE.height + 2, 0)
HEADING_AT = tuple(centred_on_lettering(BODY_FACE, text, 1, BODY_FACE.height + 2, 0) for text in HEADINGS)

# Two sprites an output, since a lamp is either the stage the board is at or one of the rest
lamps = tuple((build_lamp(index, False), build_lamp(index, True)) for index in range(len(STAGES)))
print(f"a {WIDTH}x{HEIGHT} interface doubled onto the panel, badge {player.width}px,"
      f" {len(STAGES)} stages over {len(mighty.outputs)} outputs, built in"
      f" {time.ticks_diff(time.ticks_ms(), marked)}ms")

# Everything on the panel is drawn from how long the program has been running, so it
# looks the same however fast the frames come and the pacer names no rate to hold
pacer = Pacer()

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = pacer.elapsed
        live, levels = levels_at(elapsed)

        # The outputs, from the same numbers the glass is about to be drawn from
        for index in range(min(len(STAGES), len(mighty.outputs))):
            hue = HUES[index]
            level = levels[index]
            mighty.outputs[index].set_rgb(hue.r * level, hue.g * level, hue.b * level)

        draw(elapsed, live)
        screen.update(canvas, pixel_double=True)
        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
