from picovector import color, image, rect

"""
Drawing: LED matrix
A rainbow shown as an LED matrix sign, each pixel drawn as a round lamp behind a dark face.
Section: Animation
"""

# Entry: screenA rotation=90: graphics file=led_matrix.py

# Constants for drawing
PIXEL = 8
APERTURE = 0.7
SOFTEN = 1.0
MASK = color.black
RAINBOWS = 1.5
LAMPS_A_FRAME = 1

# Everything sized from the canvas, set on the first call
WIDTH = HEIGHT = COLUMNS = ROWS = LEFT = TOP = CYCLE = 0
lamps = mask = rainbow = None
SCALE_FROM = SCALE_TO = None
ROW_TO = ROW_FROM = None
travelled = 0


def bake_lamp():
    """Bake one lamp's mask, clear over the aperture and opaque around it."""
    lamp = image(PIXEL, PIXEL)
    centre = (PIXEL - 1) / 2
    radius = PIXEL * APERTURE / 2
    for y in range(PIXEL):
        for x in range(PIXEL):
            away = ((x - centre) ** 2 + (y - centre) ** 2) ** 0.5
            over = away - radius
            if over > 0:
                lamp.pen = MASK.with_alpha(min(255, round(over / SOFTEN * 255)))
                lamp.rectangle(rect(x, y, 1, 1))
    return lamp


def bake_mask():
    """Bake the panel's mask once and a row at a time."""
    face = image(WIDTH, HEIGHT)
    lamp = bake_lamp()
    strip = image(WIDTH, PIXEL)
    for column in range(COLUMNS):
        strip.blit(lamp, LEFT + column * PIXEL, 0)
    for row in range(ROWS):
        face.blit(strip, 0, TOP + row * PIXEL)
    return face


def bake_rainbow():
    """Bake a rainbow a lamp to a pixel, with a matrix width of run-on so no row's window wraps."""
    strip = image(CYCLE + COLUMNS, 1)
    for at in range(strip.width):
        strip.pen = color.hsv(round(at * 256 / CYCLE) & 0xff, 255, 255)
        strip.hspan(at, 0, 1)
    return strip


def setup(canvas):
    """Size the matrix to the canvas and bake what every frame uses."""
    global WIDTH, HEIGHT, COLUMNS, ROWS, LEFT, TOP, CYCLE
    global lamps, mask, rainbow, SCALE_FROM, SCALE_TO, ROW_TO, ROW_FROM
    WIDTH, HEIGHT = canvas.width, canvas.height
    COLUMNS, ROWS = WIDTH // PIXEL, HEIGHT // PIXEL
    LEFT = (WIDTH - COLUMNS * PIXEL) // 2
    TOP = (HEIGHT - ROWS * PIXEL) // 2
    CYCLE = round((COLUMNS + ROWS) / RAINBOWS)

    lamps = image(COLUMNS, ROWS)
    mask = bake_mask()
    rainbow = bake_rainbow()

    SCALE_FROM = rect(0, 0, COLUMNS, ROWS)
    SCALE_TO = rect(LEFT, TOP, COLUMNS * PIXEL, ROWS * PIXEL)
    ROW_TO = [rect(0, row, COLUMNS, 1) for row in range(ROWS)]
    ROW_FROM = [rect(offset, 0, COLUMNS, 1) for offset in range(CYCLE)]

    canvas.pen = MASK
    canvas.clear()


def draw(canvas, _elapsed):
    global travelled
    if lamps is None:
        setup(canvas)

    start = travelled % CYCLE
    for row in range(ROWS):
        lamps.blit(rainbow, ROW_FROM[(start + row) % CYCLE], ROW_TO[row])
    canvas.blit(lamps, SCALE_FROM, SCALE_TO, image.NEAREST)
    canvas.blit(mask, 0, 0)
    travelled += LAMPS_A_FRAME
