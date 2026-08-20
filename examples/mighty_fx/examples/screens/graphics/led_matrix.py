# An LED matrix simulated on the panel: content drawn one pixel to a lamp, scaled up, and a baked mask
# blitted over the top so each lamp reads as a round aperture behind a dark face.
#
# Two blits a frame whatever drew the content, so any source can feed it: shapes, text, an image, or a
# player's frame. The content here is the diagonal rainbow the LED matrix boards run, which shows the
# matrix off: every lamp carries its own colour at once.

from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import color, image, rect

# Constants for drawing
PIXEL = 8                       # Panel pixels across one lamp, so how coarse the matrix is
APERTURE = 0.7                  # The lit hole, as a fraction of a lamp's width
SOFTEN = 1.0                    # Panel pixels the aperture's edge fades over, which is what rounds it
MASK = color.black              # The face the lamps are set behind
RAINBOWS = 1.5                  # Full rainbows across the matrix corner to corner, so how dense it is
# A matrix moves its pattern in whole lamps, a lamp being the smallest thing it has, so the only even step
# is a whole number of them a frame. Timed off the clock instead, the wave travels a fraction of a lamp a
# frame and lands as 1, 1, 2, 1, 1, 2, which reads as choppy however steady the frames are
LAMPS_A_FRAME = 1

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# A matrix sign is wider than it is tall, so the canvas is drawn landscape and every update turns it a
# quarter onto the panel. From the screen rather than image(), which puts it in SRAM: the mask is read
# and the frame written every frame, so both halve
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height

# The matrix's own size, in lamps. Whatever the lamps do not divide is left as a border, so they stay
# square and land on whole pixels. A finer lamp buys resolution and loses the round aperture: below about
# 6px there is no room to shape one, and a 4px lamp comes out a soft square instead
COLUMNS = WIDTH // PIXEL
ROWS = HEIGHT // PIXEL
LEFT = (WIDTH - COLUMNS * PIXEL) // 2
TOP = (HEIGHT - ROWS * PIXEL) // 2
# Lamps one full rainbow covers. Set from the diagonal rather than from the width, so the matrix carries
# the same rainbow whatever the lamp size. The LED matrix boards work out to about 0.4 of one across their
# own diagonal, which on a panel this wide leaves it too sparse to read as a wave
CYCLE = round((COLUMNS + ROWS) / RAINBOWS)

# One pixel to a lamp, which is where the content is drawn. Everything else is scaling and masking
lamps = image(COLUMNS, ROWS)


def bake_lamp():
    """One lamp's mask: clear over the aperture and opaque over the face around it.

    Built a pixel at a time from the distance to the lamp's centre, which is the only way a circle this
    small comes out even. SOFTEN carrying the edge over a fraction of a pixel is what reads as round.
    """
    lamp = image(PIXEL, PIXEL)
    lamp.pen = color.transparent
    lamp.clear()

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
    """The whole panel's mask, laid out a row of lamps at a time.

    Baked once. Blitting a lamp per cell every frame is thousands of blits and is not affordable; a row
    of them costs one blit per column, and the panel then costs one per row.

    Transparent to begin with, the lamps carrying every opaque pixel between them. Filled with the face
    colour first, the apertures never open: compositing a clear hole over black leaves black, a hole
    being something a mask is built around rather than punched through.
    """
    face = image(WIDTH, HEIGHT)
    face.pen = color.transparent
    face.clear()

    lamp = bake_lamp()
    strip = image(WIDTH, PIXEL)
    strip.pen = color.transparent
    strip.clear()
    for column in range(COLUMNS):
        strip.blit(lamp, LEFT + column * PIXEL, 0)

    for row in range(ROWS):
        face.blit(strip, 0, TOP + row * PIXEL)

    return face


mask = bake_mask()
print(f"LED matrix of {COLUMNS}x{ROWS} lamps, {PIXEL}px each, aperture {round(PIXEL * APERTURE)}px,"
      f" {'round' if PIXEL >= 6 else 'a soft square at this size'}")


def bake_rainbow():
    """One full rainbow, a lamp to a pixel, with a matrix width of run-on on the end.

    Long enough that any row can take its own window out of it without running off the end, which is
    what saves wrapping each one.
    """
    strip = image(CYCLE + COLUMNS, 1)
    for at in range(strip.width):
        strip.pen = color.hsv(round(at * 256 / CYCLE) & 0xff, 255, 255)
        strip.hspan(at, 0, 1)

    return strip


rainbow = bake_rainbow()

# Every rect a frame needs, built once. A rect is an object, so making them in the loop allocated 60 a
# frame, and the couple of kilobytes that came to brought a collection round every eighth frame: a 70ms
# pause in a 90ms frame, which showed as the wave jumping rather than as a slow one
SCALE_FROM = rect(0, 0, COLUMNS, ROWS)
SCALE_TO = rect(LEFT, TOP, COLUMNS * PIXEL, ROWS * PIXEL)
ROW_TO = [rect(0, row, COLUMNS, 1) for row in range(ROWS)]
ROW_FROM = [rect(offset, 0, COLUMNS, 1) for offset in range(CYCLE)]


def draw_lamps(at):
    """The content, drawn one pixel to a lamp. Anything can go here, this being an ordinary image.

    A GIFPlayer's frame reaches the matrix the same way: blit it into this image at the matrix's own
    size, and draw() below lights it up.

    The rainbow's hue follows x + y, so a row is the row above it moved along by one lamp and the whole
    pattern is one strip read from a different place per row. That is a blit a row, where a lamp at a
    time is a thousand calls a frame here and four thousand at the finest setting.
    """
    start = round(at) % CYCLE
    for row in range(ROWS):
        lamps.blit(rainbow, ROW_FROM[(start + row) % CYCLE], ROW_TO[row])


def draw(at):
    """One frame of the matrix: the content lit up behind its mask.

    A lamp to a block, then the face over the top. NEAREST is what keeps a lamp's edges hard: anything
    interpolating would smear one lamp into the next and the matrix would read as a blur.
    """
    draw_lamps(at)

    # Only where the lamps leave a border: they cover the rest, and the mask covers all of it
    if LEFT or TOP:
        canvas.pen = MASK
        canvas.clear()

    canvas.blit(lamps, SCALE_FROM, SCALE_TO, image.NEAREST)
    canvas.blit(mask, 0, 0)


travelled = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        draw(travelled)
        screen.update(canvas, rotation=90)
        travelled += LAMPS_A_FRAME

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
