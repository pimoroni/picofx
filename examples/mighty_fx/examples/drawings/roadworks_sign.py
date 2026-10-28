from picovector import color, font, image, rect, shape

"""
Drawing: Roadworks sign
A roadworks sign, its amber lamps behind a dark face holding a message a page at a time.
Section: Transport signs
"""

# Entry: screenA rotation=90: graphics file=roadworks_sign.py fps=50   (a 2.8" screen)

# Constants for drawing
LAMP = 4
APERTURE = 0.6
SOFTEN = 0.8
SIGN_FONT = font.sins
BEZEL = 1
LINE_BEZEL = 3
LIT = color.rgb(255, 170, 0)

MODULE = color.rgb(17, 17, 17)
FACE = color.black
UNLIT = color.rgb(68, 34, 0)

HOLD_MS = 8000
BEACON_R = 12
BEACON_MS = 500
BEACON_OFF = color.rgb(51, 17, 0)

PAGES = (
    ("ROADWORKS", "AHEAD", "EXPECT", "DELAYS"),
    ("LANE", "CLOSURE", "AHEAD", "MERGE LEFT"),
    ("QUEUE AHEAD", "SLOW DOWN", "20 MPH", "MAX"),
)

# The canvas this drawing expects, a 2.8" screen at rotation=90, stated as the mask is
# baked before the first call
WIDTH, HEIGHT = 320, 240

COLUMNS = WIDTH // LAMP
ROWS = HEIGHT // LAMP

lamps = image(COLUMNS, ROWS)
lamps.font = SIGN_FONT
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def lettering_extent(letters):
    """Measure which rows and columns these letters fill."""
    span = SIGN_FONT.height * 2
    probe = image(span, span)
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = SIGN_FONT
    for letter in letters:
        probe.text(letter, 0, 0, 1)

    raw, stride = probe.raw, probe.stride
    rows = [y for y in range(span) if any(raw[y * stride + x * 4] > 60 for x in range(span))]
    columns = [x for x in range(span) if any(raw[y * stride + x * 4] > 60 for y in range(span))]
    return rows, columns


LETTERING_ROWS, LETTERING_COLUMNS = lettering_extent(ALPHABET)
CELL_W = LETTERING_COLUMNS[-1] + 1
CELL_H = LETTERING_ROWS[-1] - LETTERING_ROWS[0] + 1
LETTERING_TOP = LETTERING_ROWS[0]

BEARING = max(int(lamps.measure_text(letter, font_size=1)[0]) for letter in ALPHABET) - CELL_W

MARGIN = (BEACON_R * 2 + LAMP - 1) // LAMP
PITCH_W = CELL_W + BEZEL
PITCH_H = CELL_H + LINE_BEZEL
LINES = (ROWS - MARGIN * 2 + LINE_BEZEL) // PITCH_H
ACROSS = (COLUMNS + BEZEL) // PITCH_W

LEFT = (COLUMNS - (ACROSS * PITCH_W - BEZEL)) // 2
TOP = (ROWS - (LINES * PITCH_H - LINE_BEZEL)) // 2


def bake_module():
    """Bake one module's mask, apertures over its lamps and the rest of its pitch opaque."""
    tile = image(PITCH_W * LAMP, PITCH_H * LAMP)
    tile.pen = color.transparent
    tile.clear()

    middle = (LAMP - 1) / 2
    radius = LAMP * APERTURE / 2
    for y in range(tile.height):
        for x in range(tile.width):
            if x // LAMP >= CELL_W or y // LAMP >= CELL_H:
                over, shade = SOFTEN, FACE
            else:
                away = (((x % LAMP) - middle) ** 2 + ((y % LAMP) - middle) ** 2) ** 0.5
                over, shade = away - radius, MODULE

            if over > 0:
                tile.pen = shade.with_alpha(min(255, round(over / SOFTEN * 255)))
                tile.rectangle(rect(x, y, 1, 1))

    return tile


def bake_mask():
    """Bake the sign's face, the modules laid a row at a time, then its margins filled."""
    face = image(WIDTH, HEIGHT)
    face.pen = color.transparent
    face.clear()

    module = bake_module()
    strip = image(WIDTH, module.height)
    strip.pen = color.transparent
    strip.clear()
    for column in range(ACROSS):
        strip.blit(module, (LEFT + column * PITCH_W) * LAMP, 0)

    for line in range(LINES):
        face.blit(strip, 0, (TOP + line * PITCH_H) * LAMP)

    top = TOP * LAMP
    bottom = (TOP + LINES * PITCH_H) * LAMP
    right = (LEFT + ACROSS * PITCH_W) * LAMP
    face.pen = FACE
    face.rectangle(rect(0, 0, WIDTH, top))
    face.rectangle(rect(0, bottom, WIDTH, HEIGHT - bottom))
    face.rectangle(rect(0, top, LEFT * LAMP, bottom - top))
    face.rectangle(rect(right, top, WIDTH - right, bottom - top))

    return face


mask = bake_mask()

SCALE_FROM = rect(0, 0, COLUMNS, ROWS)
SCALE_TO = rect(0, 0, COLUMNS * LAMP, ROWS * LAMP)

BEACONS = [shape.circle(x, y, BEACON_R)
           for x, y in ((BEACON_R, BEACON_R), (BEACON_R, HEIGHT - BEACON_R),
                        (WIDTH - BEACON_R, BEACON_R), (WIDTH - BEACON_R, HEIGHT - BEACON_R))]


def draw_lamps(page):
    """Draw the message a character to a module."""
    lamps.pen = UNLIT
    lamps.clear()
    lamps.pen = LIT

    lines = PAGES[page][:LINES]
    first = TOP + (LINES - len(lines)) // 2 * PITCH_H
    for line, text in enumerate(lines):
        text = text[:ACROSS]
        start = LEFT + (ACROSS - len(text)) // 2 * PITCH_W
        y = first + line * PITCH_H
        for column, letter in enumerate(text):
            wide = int(lamps.measure_text(letter, font_size=1)[0]) - BEARING
            lamps.text(letter, start + column * PITCH_W + (CELL_W - wide) // 2, y - LETTERING_TOP, 1)


def sign(canvas, page, on_the_left):
    """Draw one frame of the sign, the message lit up behind its face, and the beacons on the face itself."""
    draw_lamps(page)
    canvas.blit(lamps, SCALE_FROM, SCALE_TO, image.NEAREST)
    canvas.blit(mask, 0, 0)

    for index, beacon in enumerate(BEACONS):
        canvas.pen = LIT if (index < 2) == on_the_left else BEACON_OFF
        canvas.shape(beacon)


shown = None


def draw(canvas, elapsed):
    global shown
    if shown is None and (canvas.width, canvas.height) != (WIDTH, HEIGHT):
        raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                         f"rotation=90, and was given {canvas.width}x{canvas.height}")

    now = int(elapsed * 1000)
    frame = (now // HOLD_MS % len(PAGES), bool(now // BEACON_MS % 2))

    # Nothing on the sign moves, so it is only drawn again when the page or the beacons change
    if frame != shown:
        sign(canvas, *frame)
        shown = frame
