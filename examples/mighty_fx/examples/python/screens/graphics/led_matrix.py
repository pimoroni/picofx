import sys
from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, image, rect

"""
Show a rainbow as an LED matrix sign, each pixel drawn as a round lamp behind a dark face.

It is two blits a frame whatever drew the content, so shapes, text, an image or a player's
frame can feed it. The rainbow runs diagonally, as on the LED matrix boards.

Press "Boot" to exit the program.
"""

# Constants for drawing
PIXEL = 8                       # Panel pixels across one lamp, so how coarse the matrix is
APERTURE = 0.7                  # The lit hole, as a fraction of a lamp's width
SOFTEN = 1.0                    # Panel pixels the aperture's edge fades over, which rounds it
MASK = color.black              # The face the lamps are set behind
RAINBOWS = 1.5                  # Full rainbows across the matrix corner to corner, so how dense it is
LAMPS_A_FRAME = 1               # Whole lamps a frame, as a clock-timed step reads as choppy

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

# Drawn landscape as a matrix sign is wider than tall, and turned a quarter onto the panel at each update
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height

# The matrix's size in lamps, any remainder left as a border so the lamps stay square
COLUMNS = WIDTH // PIXEL
ROWS = HEIGHT // PIXEL
LEFT = (WIDTH - COLUMNS * PIXEL) // 2
TOP = (HEIGHT - ROWS * PIXEL) // 2
# Lamps one full rainbow covers, taken from the diagonal so the lamp size does not change it
CYCLE = round((COLUMNS + ROWS) / RAINBOWS)

# One pixel to a lamp, which is where the content is drawn. Everything else is scaling and masking
lamps = image(COLUMNS, ROWS)


def bake_lamp():
    """
    Bake one lamp's mask, clear over the aperture and opaque around it. It goes a pixel at a
    time so a circle this small comes out even.
    """
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
    """
    Bake the panel's mask once and a row at a time, as a blit per lamp per frame is not affordable.

    A new image must start transparent, as a clear hole over a filled face leaves the face.
    """
    face = image(WIDTH, HEIGHT)

    lamp = bake_lamp()
    strip = image(WIDTH, PIXEL)
    for column in range(COLUMNS):
        strip.blit(lamp, LEFT + column * PIXEL, 0)

    for row in range(ROWS):
        face.blit(strip, 0, TOP + row * PIXEL)

    return face


mask = bake_mask()
print(f"LED matrix of {COLUMNS}x{ROWS} lamps, {PIXEL}px each, aperture {round(PIXEL * APERTURE)}px,"
      f" {'round' if PIXEL >= 6 else 'a soft square at this size'}")


def bake_rainbow():
    """Bake a rainbow a lamp to a pixel, with a matrix width of run-on so no row's window wraps."""
    strip = image(CYCLE + COLUMNS, 1)
    for at in range(strip.width):
        strip.pen = color.hsv(round(at * 256 / CYCLE) & 0xff, 255, 255)
        strip.hspan(at, 0, 1)

    return strip


rainbow = bake_rainbow()

# Every rect a frame needs, built once so the loop never stalls the wave for a garbage collection
SCALE_FROM = rect(0, 0, COLUMNS, ROWS)
SCALE_TO = rect(LEFT, TOP, COLUMNS * PIXEL, ROWS * PIXEL)
ROW_TO = [rect(0, row, COLUMNS, 1) for row in range(ROWS)]
ROW_FROM = [rect(offset, 0, COLUMNS, 1) for offset in range(CYCLE)]


def draw_lamps(at):
    """
    Draw the content one pixel to a lamp. Any image works here, a GIFPlayer's frame included.

    The hue follows x + y, so each row is a single blit of one rainbow strip from its own offset.
    """
    start = at % CYCLE
    for row in range(ROWS):
        lamps.blit(rainbow, ROW_FROM[(start + row) % CYCLE], ROW_TO[row])


def draw(at):
    """Draw one frame, scaling each pixel to a hard-edged lamp with NEAREST and masking it."""
    draw_lamps(at)
    canvas.blit(lamps, SCALE_FROM, SCALE_TO, image.NEAREST)
    canvas.blit(mask, 0, 0)


travelled = 0

# A PIXEL that leaves a border round the lamps has it filled once here, as nothing draws there
canvas.pen = MASK
canvas.clear()

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        draw(travelled)
        screen.update(canvas, rotation=90)
        travelled += LAMPS_A_FRAME

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
