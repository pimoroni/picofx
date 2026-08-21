import gc
import time

from mighty_fx import MightyFX, SPCE
from playback import GIFPlayer
from screens import Screen280
from picovector import color, font, image, rect, shape

"""
Draw a status panel for the company that made the board: the wordmark over a cycling ribbon,
the coin as a badge, a few statuses, and the seven RGB outputs standing in for the line the
board came down.

Everything is drawn at half the panel's size and doubled on the way out, so every pixel on the
glass is a square of four, for a quarter of the canvas and a quarter of the drawing. The ribbon
is dithered along its own direction, since 16 levels a channel turn a gradient into bands.

The seven outputs are a production line, one stage live at a time with its lamp lit on the glass
and its LED lit on the board below. One level per output, read by both, so the two cannot drift
apart. The interface is built once and blitted as the ground, so a frame draws only what moves.

Press "Boot" to exit the program.
"""

# Constants for drawing
EMBLEM = "/examples/assets/pirate_coin_emblem.gif"
WORDMARK_FACE = "/rom/fonts/PoppinsBlack.af"  # A vector face, drawn large and reduced: part of the render
# Poppins Black's ink, measured on the board: 0.309 of the size asked for, starting 0.697 of it below the y it
# is drawn at. Neither is the em box, which is far taller than the space here, so the wordmark is sized and
# placed from the ink instead of being clipped by the box
INK_TALL = 0.309
INK_DOWN = 0.697
BODY_FACE = "winds"                     # The narrowest pixel face, which is what the statuses need
ROTATION = 90                           # Quarter turn, to suit how the screen is mounted
REDUCE = 2                              # The render is drawn this much larger and reduced onto the canvas

INK = color.black                       # The type, the bullets and the wordmark
GROUND = color.white
RULE = color.rgb(150, 150, 150)         # Structure and the numbers, which are not content
PLATE = color.rgb(228, 228, 228)        # Behind the badge and under the line, light so the screen stays white
PLATE_EDGE = color.rgb(190, 190, 190)
PLATE_SHADOW = color.rgb(206, 206, 206)  # A plate sits a pixel above the interface, so it casts one
PLATE_BEVEL = color.white               # And catches the light along its inside edge
SCREW = color.rgb(168, 168, 168)
PLATE_R = 3                             # Corner radius, in the interface's own pixels

WORDMARK = "PIMORONI"
TAGLINE = "PURVEYORS OF MAKER GOODS"

# The ribbon under the wordmark: two hues, both turning at the same rate, so the pair keeps its relationship
# while the colour travels
RIBBON_MS = 9000                        # One turn of the wheel
RIBBON_SPREAD = 70                      # How far apart the two hues sit on it, of 255
RIBBON_SAT = 255
RIBBON_VALUE = 210                      # Short of full, a hue at 255 having little to give against white type
RIBBON_STEP = 2                         # Pixels a band, the gradient being drawn band by band
RIBBON_DITHER = 8                       # Jitter on every other band, which scatters the panel's own banding

# The statuses: a label, what it says, and the colour that carries. A state is coloured for what it means and
# a count is not a state, so a number stays in the type's own ink. Measured, not estimated: the longest is 100
# of the 160 the interface has, which lets the bullets sit this close to the badge
STATE_GOOD = color.rgb(0, 136, 0)       # Both on the panel's own grid of 16 levels a channel, and both short
STATE_BAD = color.rgb(204, 0, 0)        # of full, a saturated hue having little to give against white
STATUSES = (("CREW ON DUTY", "40", INK),
            ("FOOD VAN", "NOT HERE", STATE_BAD),
            ("ROOF", "NOT LEAKING", STATE_GOOD))

# The line, one stage to an output, so a stage's number is the number printed beside its LED
STAGES = ("PICK", "PLACE", "REFLOW", "TEST", "FLASH", "PACK", "SHIP")
HEADING = "ASSEMBLY LINE"               # What the row of lamps is, since seven lights alone say nothing
STAGE_MS = 900                          # How long a stage holds before the board moves on
DIM = 0.08                              # What every output but the live one holds, so the line is never dark
LAMP_R = 3
# The light on the plate is drawn as rings rather than added by bloom(). That lifts what is
# already bright, so a saturated red or blue lamp gets no glow at all: its luminance is below any
# threshold the paler hues need to be lifted at
GLOW_R = LAMP_R + 3                     # How far a lit lamp's light reaches onto the plate around it
SPRITE_R = GLOW_R + 1                   # And the pixel of clear margin past it the sprite keeps
GLOW_STEPS = 5                          # Rings it is built from, drawn largest first so they build inwards
GLOW_ALPHA = 40                         # What the innermost ring adds, of 255; each outer one a share of it
DOME_LIGHT = 190                        # The core a lit lamp shows, and the light unlit glass catches
CONSOLE_PAD = 2                         # How far the plate under the line reaches past what sits on it

# Create a MightyFX object with SP/CE A set up for a screen, and its RGB outputs for the line
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Half the panel each way, doubled by update(): a quarter of the pixels for the same picture
canvas = screen.canvas(screen.height // 2, screen.width // 2)
WIDTH, HEIGHT = canvas.width, canvas.height
wordmark_face = font.load(WORDMARK_FACE)
body_face = getattr(font, BODY_FACE)
canvas.font = body_face

player = GIFPlayer(EMBLEM)
emblem = player.sheet.sprite(0)

LINE_H = body_face.height + 1           # One line of type to the next
RIBBON_TOP = 22                         # The render above it is a wordmark and nothing else
RIBBON_H = body_face.height + 1
BODY_TOP = RIBBON_TOP + RIBBON_H + 4    # Clear of the ribbon, so the badge reads as an object of its own
PLATE_PAD = 3
BADGE_AT = (4, BODY_TOP)
STATUS_LEFT = BADGE_AT[0] + emblem.width + PLATE_PAD + 3
COIN_AT = rect(BADGE_AT[0], BADGE_AT[1], emblem.width, emblem.height)

NUMBER_TOP = HEIGHT - body_face.height  # The numbers sit at the foot, the lamps above them
NUMBER_NUDGE = 1                        # A digit reads better a pixel right of its lamp's centre
LAMP_Y = NUMBER_TOP - LAMP_R - 1
HEADING_TOP = LAMP_Y - LAMP_R - body_face.height - 2
STATUS_DOWN = 1                         # The statuses sit a pixel below the badge's own top, which is what
                                        # squares them against it, not against the plate behind it
BULLET_DOWN = 5                         # Where a bullet sits against its line, which is nearer the middle
                                        # of the type than the top of the space it is given
ROW_INSET = 4                           # Nudges the lamps if the panel and the connectors do not line up
CELL_W = (WIDTH - ROW_INSET * 2) / len(STAGES)

# The plate under the line reaches past the heading above it and the numbers below, and to both edges
CONSOLE_AT = (1, HEADING_TOP - CONSOLE_PAD)
CONSOLE_W = WIDTH - 2
CONSOLE_H = HEIGHT - CONSOLE_AT[1] - 1

# The ground: everything that never changes
ground = image(WIDTH, HEIGHT)
ground.font = body_face
ground.antialias = image.X4


# Measuring needs a font set, and setting one leaves it set, so it is asked of an image of its own. Asking the
# ground would leave the ground drawing in whichever face was measured last, and the statuses are drawn on it
asker = image(8, 8)


def measure(face, text, size):
    """The advance a drawing of the text takes. Any image answers the same, so a scratch one is asked."""
    asker.font = face
    return asker.measure_text(text, font_size=size)[0]


__blanks = {}


def glyph_blanks(face, glyph, size, tall, down):
    """The blank a glyph carries before and after its ink, out of the advance it takes.

    Centring on measure_text leaves a string off centre: what it returns is the advance, and a glyph's ink
    stops short of its own by whatever the face leaves around it. On an interface this wide that shows.

    Only the two end glyphs need measuring, advances adding up without kerning, and answers are kept.
    """
    kept = __blanks.get((glyph, size))
    if kept:
        return kept

    advance = measure(face, glyph, size)
    scratch = image(round(advance) + 8, round(tall))
    scratch.antialias = image.X4
    scratch.font = face
    scratch.pen = INK
    scratch.text(glyph, 4, down, font_size=size)

    raw, stride = scratch.raw, scratch.stride
    left, right = scratch.width, -1
    for y in range(scratch.height):
        row = bytes(raw[y * stride:y * stride + scratch.width * 4])
        inked = row.lstrip(b"\0")
        if not inked:
            continue

        left = min(left, (len(row) - len(inked)) // 4)
        right = max(right, (len(row.rstrip(b"\0")) - 1) // 4)

    if right < 0:
        # A glyph that inks nothing, a space among them, has no blank of its own to report. Answering from an
        # empty scratch would hand back its whole width and throw the line across the interface
        __blanks[(glyph, size)] = (0, 0)
    else:
        __blanks[(glyph, size)] = (left - 4, advance - (right - 4) - 1)

    return __blanks[(glyph, size)]


def centred_on_ink(face, text, size, tall, down, across=None):
    """The x to draw the text at for its ink to sit centred, worked out once, not every frame."""
    before = glyph_blanks(face, text[0], size, tall, down)[0]
    after = glyph_blanks(face, text[-1], size, tall, down)[1]
    return ((across or WIDTH) - (measure(face, text, size) - before - after)) / 2 - before


def cell_centre(index):
    """Where a stage sits across the interface, which is where its output sits along the board."""
    return ROW_INSET + CELL_W * (index + 0.5)


def plate(render, x, y, w, h, screws=True):
    """A raised plate, in the interface's coordinates: a shadow, a face, a lit inside edge, and screws.

    Both plates come from here, so the badge and the line read as parts of one machine. None of it is pixel
    aligned by design. It is drawn at twice the size and reduced, so an edge lands between two of the panel's
    pixels and arrives as shading, which is what a picture of a real plate does.
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

    if screws:
        for across in (x + PLATE_R, x + w - PLATE_R):
            for down in (y + PLATE_R, y + h - PLATE_R):
                render.pen = SCREW
                render.circle(across * REDUCE, down * REDUCE, 1.4 * REDUCE)
                render.pen = PLATE_BEVEL
                render.circle(across * REDUCE, down * REDUCE, 0.5 * REDUCE)


def build_render():
    """The rendered half of the interface, drawn large and reduced onto the ground.

    Everything here is continuous tone: a vector wordmark, a plate behind the badge, and a plate carrying
    the line with a rail and a housing for each lamp. Built once, so it costs nothing per frame.
    """
    render = image(WIDTH * REDUCE, HEIGHT * REDUCE)
    render.antialias = image.X4
    render.font = wordmark_face
    render.pen = GROUND
    render.clear()

    render.pen = INK
    room = RIBBON_TOP * REDUCE - 6                       # The render's own pixels, above the ribbon
    size = room / INK_TALL
    wide = measure(wordmark_face, WORDMARK, size)
    across = render.width - 8
    if wide > across:                                    # A heavy face runs out of width before height
        size *= across / wide

    # Measured at the same y it is drawn at: this face inks below the line it is given, so a scratch only as
    # tall as the wordmark holds the ink only if the draw is placed the same way
    down = 3 - INK_DOWN * size
    render.text(WORDMARK, centred_on_ink(wordmark_face, WORDMARK, size, room + 8, down, render.width),
                down, font_size=size)

    plate(render, BADGE_AT[0] - PLATE_PAD, BADGE_AT[1] - PLATE_PAD,
          emblem.width + PLATE_PAD * 2, emblem.height + PLATE_PAD * 2)

    # One plate under the heading, the lamps and their numbers, so the three read as an instrument and not as
    # text with lights beneath it
    plate(render, CONSOLE_AT[0], CONSOLE_AT[1], CONSOLE_W, CONSOLE_H)

    # The rail the lamps sit on, drawn first so each housing breaks it: seven lights in a row say nothing on
    # their own, and a track between them says a board travels from one to the next
    render.pen = PLATE_EDGE
    render.rectangle(cell_centre(0) * REDUCE, LAMP_Y * REDUCE - 1,
                     (cell_centre(len(STAGES) - 1) - cell_centre(0)) * REDUCE, 2)

    ground.blit(render, rect(0, 0, render.width, render.height), rect(0, 0, WIDTH, HEIGHT), image.BILINEAR)
    del render
    gc.collect()


def build_ground():
    """The render, then the pixel accurate type over it: the statuses and the lamps' numbers.

    The type is drawn after the reduction and never through it, so it stays exactly as its face draws it. That
    is the division the whole screen is built on: what is a picture is rendered, and what has to be read is
    not.
    """
    build_render()

    for index, (label, state, tone) in enumerate(STATUSES):
        top = BODY_TOP + STATUS_DOWN + index * LINE_H
        lead = f"{label} = "
        ground.pen = INK
        ground.rectangle(STATUS_LEFT, top + BULLET_DOWN, 3, 3)
        ground.text(lead, STATUS_LEFT + 6, top, 1)
        ground.pen = tone
        ground.text(state, STATUS_LEFT + 6 + measure(body_face, lead, 1), top, 1)

    # The numbers, which are read, not looked at, so they are type and not part of the render
    ground.pen = RULE
    for index in range(len(STAGES)):
        number = str(index + 1)
        ground.text(number, cell_centre(index) - ground.measure_text(number, font_size=1)[0] / 2
                    + NUMBER_NUDGE, NUMBER_TOP, 1)


def lamp_origin(index):
    """The interface pixel a lamp's sprite is blitted at. The lamps are spaced to match the connectors, so a
    centre falls between two pixels. The whole part places the sprite and the fraction is drawn into it, which
    keeps the row evenly spaced without asking a blit for a fractional position."""
    return int(cell_centre(index)) - SPRITE_R, LAMP_Y - SPRITE_R


def build_lamp(index, lit):
    """One lamp as a small rendered picture: its housing, its light, and the halo around it.

    A lamp is drawn rather than blitted per frame for the same reason the plates are: at twice the size and
    reduced, so the housing's edge and the light spilling from it arrive as shading. Outside itself the sprite
    is transparent, so it lays over the plate the ground already carries.
    """
    origin = lamp_origin(index)
    side = SPRITE_R * 2
    render = image(side * REDUCE, side * REDUCE)
    render.antialias = image.X4

    at = ((cell_centre(index) - origin[0]) * REDUCE, (LAMP_Y - origin[1]) * REDUCE)
    inside = (LAMP_R + 1) * REDUCE      # The housing's inside edge, where its rim begins

    if lit:
        # The plate around a lit lamp takes its colour, strongest against the housing. The outermost ring is
        # the faintest and stops short of the sprite's edge: a ring cut off by the edge leaves a straight run
        # of colour along it, which reads as loose pixels beside the lamp
        for step in range(GLOW_STEPS):
            reach = GLOW_R - step * (GLOW_R - LAMP_R - 1) / GLOW_STEPS
            render.pen = LIT_HUES[index].with_alpha(GLOW_ALPHA * (step + 1) // GLOW_STEPS)
            render.circle(at[0], at[1], reach * REDUCE)

    # The rim is a disc with the housing's face laid inside it, and the light inside that. Stroking a ring one
    # pixel wide instead leaves it part covered where it crosses a pixel diagonally, and there it takes the
    # light's colour and reads as a stray beside its solid grey neighbours
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
    """The ribbon, band by band: two hues that cycle together, dithered along the way across.

    Drawn every frame rather than baked, the colour being the thing that moves. Every other band is nudged by
    half a level of the panel's own grid, which turns the bands 12 bit colour would otherwise show into a
    stipple.
    """
    turn = (elapsed % RIBBON_MS) * 255 // RIBBON_MS
    for band in range(0, WIDTH, RIBBON_STEP):
        across = band / WIDTH
        hue = turn + round(RIBBON_SPREAD * across)
        value = RIBBON_VALUE + (RIBBON_DITHER if (band // RIBBON_STEP) % 2 else -RIBBON_DITHER)
        canvas.pen = color.hsv(hue, RIBBON_SAT, min(255, value))
        canvas.rectangle(band, RIBBON_TOP, RIBBON_STEP, RIBBON_H)

    canvas.pen = GROUND
    canvas.text(TAGLINE, TAGLINE_AT, RIBBON_TOP, 1)


def levels_at(elapsed):
    """Which stage is live, and how brightly each output is lit: that one full and every other just alive."""
    live = (elapsed // STAGE_MS) % len(STAGES)
    return live, tuple(1.0 if index == live else DIM for index in range(len(STAGES)))


# Values short of full: a hue at 255 washes out against a white ground, the yellows most of all. That is what
# an output is set to and what an unlit lamp is tinted with; a lit one goes to full, having light of its own
HUES = tuple(color.hsv(index * 255 // len(STAGES), 255, 210) for index in range(len(STAGES)))
LIT_HUES = tuple(color.hsv(index * 255 // len(STAGES), 255, 255) for index in range(len(STAGES)))


def draw(elapsed, live):
    """One frame: the ground, the ribbon, the badge, what the line is doing, and the seven lamps."""
    canvas.blit(ground, 0, 0)
    draw_ribbon(elapsed)
    canvas.blit(player.image, COIN_AT)

    # The heading says what the lamps are, and names the stage that is live, so a number on a lamp means
    # something to somebody reading the screen cold
    canvas.pen = INK
    canvas.text(HEADINGS[live], HEADING_AT[live], HEADING_TOP, 1)

    for index in range(len(STAGES)):
        canvas.blit(lamps[index][index == live], *lamp_origin(index))


marked = time.ticks_ms()
build_ground()

# What the ribbon and the lamps are labelled with, and where each sits to be centred on its own ink. Measured
# once here, not every frame, a string's width being fixed once its face is
HEADINGS = tuple(f"{HEADING} = {stage}" for stage in STAGES)
TAGLINE_AT = centred_on_ink(body_face, TAGLINE, 1, body_face.height + 2, 0)
HEADING_AT = tuple(centred_on_ink(body_face, text, 1, body_face.height + 2, 0) for text in HEADINGS)
# Two sprites an output, since a lamp is either the stage the board is at or one of the rest
lamps = tuple((build_lamp(index, False), build_lamp(index, True)) for index in range(len(STAGES)))
print(f"a {WIDTH}x{HEIGHT} interface doubled onto the panel, badge {emblem.width}px,"
      f" {len(STAGES)} stages over {len(mighty.outputs)} outputs, built in"
      f" {time.ticks_diff(time.ticks_ms(), marked)}ms")

started = time.ticks_ms()

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = time.ticks_diff(time.ticks_ms(), started)
        live, levels = levels_at(elapsed)

        # The outputs, from the same numbers the glass is about to be drawn from
        for index in range(min(len(STAGES), len(mighty.outputs))):
            hue = HUES[index]
            level = levels[index]
            mighty.outputs[index].set_rgb(hue.r * level, hue.g * level, hue.b * level)

        draw(elapsed, live)
        screen.update(canvas, rotation=ROTATION, pixel_double=True)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
