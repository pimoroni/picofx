from picovector import color, font, image, rect, shape, spritesheet

"""
Drawing: Status panel
A status panel for the company that made the board, a wordmark over a cycling ribbon, a coin
badge, a few statuses, and a production line of seven lamps.
Section: Billboards and panels
"""

# Entry: screenA rotation=90 pixel_double=true: graphics file=status_panel.py   (a 2.8" screen)

# Constants for drawing
EMBLEM = "/examples/assets/pirate_coin_emblem.gif"   # Stepped by hand, as a drawing cannot play a GIF
SPIN_MS = 80                            # Each frame of the spin, fixed as the file's own delays are not read
WORDMARK_FACE = "/rom/fonts/PoppinsBlack.af"
LETTERING_TALL = 0.309
LETTERING_DOWN = 0.697
BODY_FACE = font.winds
REDUCE = 2

TEXT_COLOUR = color.black
BACKGROUND = color.white
RULE = color.rgb(150, 150, 150)
PLATE = color.rgb(228, 228, 228)
PLATE_EDGE = color.rgb(190, 190, 190)
PLATE_SHADOW = color.rgb(206, 206, 206)
PLATE_BEVEL = color.white
SCREW = color.rgb(168, 168, 168)
PLATE_R = 3

WORDMARK = "PIMORONI"
TAGLINE = "PURVEYORS OF MAKER GOODS"

RIBBON_MS = 9000
RIBBON_SPREAD = 70
RIBBON_SAT = 255
RIBBON_VALUE = 210
RIBBON_STEP = 2
RIBBON_DITHER = 8

STATE_GOOD = color.rgb(0, 136, 0)
STATE_BAD = color.rgb(204, 0, 0)
STATUSES = (("CREW ON DUTY", "40", TEXT_COLOUR),
            ("FOOD VAN", "NOT HERE", STATE_BAD),
            ("ROOF", "NOT LEAKING", STATE_GOOD))

STAGES = ("PICK", "PLACE", "REFLOW", "TEST", "FLASH", "PACK", "SHIP")
HEADING = "ASSEMBLY LINE"
STAGE_MS = 900
DIM = 0.08
LAMP_R = 3
GLOW_R = LAMP_R + 3
SPRITE_R = GLOW_R + 1
GLOW_STEPS = 5
GLOW_ALPHA = 40
DOME_LIGHT = 190
CONSOLE_PAD = 2

# The canvas this drawing expects, half a 2.8" screen at rotation=90 with pixel_double, stated
# as the background is built before the first call
WIDTH, HEIGHT = 160, 120

wordmark_face = font.load(WORDMARK_FACE)

try:
    # An animated GIF loads as a sheet of every frame, stepped through by hand below
    sheet = spritesheet.load(EMBLEM)
    spin = [sheet.sprite(index) for index in range(sheet.sprites)]
    badge = spin[0]
except (ValueError, OSError):
    raise RuntimeError(f"'{EMBLEM}' is missing or corrupt! Check it is on the drive") from None

LINE_H = BODY_FACE.height + 1
RIBBON_TOP = 22
RIBBON_H = BODY_FACE.height + 1
BODY_TOP = RIBBON_TOP + RIBBON_H + 4
PLATE_PAD = 3
BADGE_AT = (4, BODY_TOP)
STATUS_LEFT = BADGE_AT[0] + badge.width + PLATE_PAD + 3
COIN_AT = rect(BADGE_AT[0], BADGE_AT[1], badge.width, badge.height)

NUMBER_TOP = HEIGHT - BODY_FACE.height
NUMBER_NUDGE = 1
LAMP_Y = NUMBER_TOP - LAMP_R - 1
HEADING_TOP = LAMP_Y - LAMP_R - BODY_FACE.height - 2
STATUS_DOWN = 1
BULLET_DOWN = 5
ROW_INSET = 4
CELL_W = (WIDTH - ROW_INSET * 2) / len(STAGES)

CONSOLE_AT = (1, HEADING_TOP - CONSOLE_PAD)
CONSOLE_W = WIDTH - 2
CONSOLE_H = HEIGHT - CONSOLE_AT[1] - 1

background = image(WIDTH, HEIGHT)
background.font = BODY_FACE
background.antialias = image.X4

asker = image(8, 8)


def measure(face, text, size):
    """The advance a drawing of the text takes."""
    asker.font = face
    return asker.measure_text(text, font_size=size)[0]


def glyph_blanks(face, glyph, size, tall, down):
    """Measure the blank a glyph carries before and after its lettering."""
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
        return 0, 0

    return left - 4, advance - (right - 4) - 1


def centred_on_lettering(face, text, size, tall, down, across=None):
    """Find the x to draw the text at for its lettering to sit centred."""
    before = glyph_blanks(face, text[0], size, tall, down)[0]
    after = glyph_blanks(face, text[-1], size, tall, down)[1]
    return ((across or WIDTH) - (measure(face, text, size) - before - after)) / 2 - before


def cell_centre(index):
    """Where a stage sits across the interface."""
    return ROW_INSET + CELL_W * (index + 0.5)


def plate(render, x, y, w, h):
    """Draw a raised plate in the interface's coordinates, shadow, face, lit edge and screws."""
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
    room = RIBBON_TOP * REDUCE - 6
    size = room / LETTERING_TALL
    wide = measure(wordmark_face, WORDMARK, size)
    across = render.width - 8
    if wide > across:
        size *= across / wide

    down = 3 - LETTERING_DOWN * size
    render.text(WORDMARK, centred_on_lettering(wordmark_face, WORDMARK, size, room + 8, down, render.width),
                down, font_size=size)

    plate(render, BADGE_AT[0] - PLATE_PAD, BADGE_AT[1] - PLATE_PAD,
          badge.width + PLATE_PAD * 2, badge.height + PLATE_PAD * 2)
    plate(render, CONSOLE_AT[0], CONSOLE_AT[1], CONSOLE_W, CONSOLE_H)

    render.pen = PLATE_EDGE
    render.rectangle(cell_centre(0) * REDUCE, LAMP_Y * REDUCE - 1,
                     (cell_centre(len(STAGES) - 1) - cell_centre(0)) * REDUCE, 2)

    background.blit(render, rect(0, 0, render.width, render.height), rect(0, 0, WIDTH, HEIGHT), image.BILINEAR)


def build_background():
    """Lay the render, then the pixel-accurate type over it."""
    build_render()

    for index, (label, state, tone) in enumerate(STATUSES):
        top = BODY_TOP + STATUS_DOWN + index * LINE_H
        lead = f"{label} = "
        background.pen = TEXT_COLOUR
        background.rectangle(STATUS_LEFT, top + BULLET_DOWN, 3, 3)
        background.text(lead, STATUS_LEFT + 6, top, 1)
        background.pen = tone
        background.text(state, STATUS_LEFT + 6 + measure(BODY_FACE, lead, 1), top, 1)

    background.pen = RULE
    for index in range(len(STAGES)):
        number = str(index + 1)
        background.text(number, cell_centre(index) - background.measure_text(number, font_size=1)[0] / 2
                        + NUMBER_NUDGE, NUMBER_TOP, 1)


def lamp_origin(index):
    """The whole pixel a lamp's sprite is blitted at."""
    return int(cell_centre(index)) - SPRITE_R, LAMP_Y - SPRITE_R


HUES = tuple(color.hsv(index * 255 // len(STAGES), 255, 210) for index in range(len(STAGES)))
LIT_HUES = tuple(color.hsv(index * 255 // len(STAGES), 255, 255) for index in range(len(STAGES)))


def build_lamp(index, lit):
    """Render one lamp, housing, light and halo, at twice size, reduced to a sprite clear outside it."""
    origin = lamp_origin(index)
    side = SPRITE_R * 2
    render = image(side * REDUCE, side * REDUCE)
    render.antialias = image.X4

    at = ((cell_centre(index) - origin[0]) * REDUCE, (LAMP_Y - origin[1]) * REDUCE)
    inside = (LAMP_R + 1) * REDUCE

    if lit:
        for step in range(GLOW_STEPS):
            reach = GLOW_R - step * (GLOW_R - LAMP_R - 1) / GLOW_STEPS
            render.pen = LIT_HUES[index].with_alpha(GLOW_ALPHA * (step + 1) // GLOW_STEPS)
            render.circle(at[0], at[1], reach * REDUCE)

    render.pen = PLATE_EDGE
    render.circle(at[0], at[1], inside + REDUCE)
    render.pen = PLATE
    render.circle(at[0], at[1], inside - 1)
    render.pen = LIT_HUES[index] if lit else HUES[index].with_alpha(round(255 * DIM))
    render.circle(at[0], at[1], inside - 1)

    render.pen = color.white.with_alpha(DOME_LIGHT if lit else DOME_LIGHT // 3)
    if lit:
        render.circle(at[0], at[1], LAMP_R * 0.45 * REDUCE)
    else:
        render.circle(at[0] - LAMP_R * 0.4 * REDUCE, at[1] - LAMP_R * 0.4 * REDUCE,
                      LAMP_R * 0.35 * REDUCE)

    sprite = image(side, side)
    sprite.blit(render, rect(0, 0, render.width, render.height), rect(0, 0, side, side), image.BILINEAR)
    return sprite


def draw_ribbon(canvas, elapsed_ms):
    """Draw the ribbon band by band, two hues cycling together."""
    turn = (elapsed_ms % RIBBON_MS) * 255 // RIBBON_MS
    for band in range(0, WIDTH, RIBBON_STEP):
        across = band / WIDTH
        hue = turn + round(RIBBON_SPREAD * across)
        value = RIBBON_VALUE + (RIBBON_DITHER if (band // RIBBON_STEP) % 2 else -RIBBON_DITHER)
        canvas.pen = color.hsv(hue, RIBBON_SAT, min(255, value))
        canvas.rectangle(band, RIBBON_TOP, RIBBON_STEP, RIBBON_H)

    canvas.pen = BACKGROUND
    canvas.text(TAGLINE, TAGLINE_AT, RIBBON_TOP, 1)


build_background()

HEADINGS = tuple(f"{HEADING} = {stage}" for stage in STAGES)
TAGLINE_AT = centred_on_lettering(BODY_FACE, TAGLINE, 1, BODY_FACE.height + 2, 0)
HEADING_AT = tuple(centred_on_lettering(BODY_FACE, text, 1, BODY_FACE.height + 2, 0) for text in HEADINGS)

lamps = tuple((build_lamp(index, False), build_lamp(index, True)) for index in range(len(STAGES)))
started = False


def draw(canvas, elapsed):
    global started
    if not started:
        if (canvas.width, canvas.height) != (WIDTH, HEIGHT):
            raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                             f"rotation=90 with pixel_double=true, and was given {canvas.width}x{canvas.height}")
        canvas.font = BODY_FACE
        started = True

    elapsed_ms = int(elapsed * 1000)
    live = (elapsed_ms // STAGE_MS) % len(STAGES)

    canvas.blit(background, 0, 0)
    draw_ribbon(canvas, elapsed_ms)
    canvas.blit(spin[elapsed_ms // SPIN_MS % len(spin)], COIN_AT)

    canvas.pen = TEXT_COLOUR
    canvas.text(HEADINGS[live], HEADING_AT[live], HEADING_TOP, 1)

    for index in range(len(STAGES)):
        canvas.blit(lamps[index][index == live], *lamp_origin(index))
