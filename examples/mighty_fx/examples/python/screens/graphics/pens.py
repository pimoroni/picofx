import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import brush, color, font, image, mat3, rect, shape

"""
Fill the same circle with six different pens, from a plain colour to a picture.

A colour, a linear gradient, a radial one, an image, a blur that takes what is already
under it, and an erase that takes the pixels away. The last two only make sense over
something, so the panel starts covered in a pattern for them to work on.

A gradient's axis lives in a 0 to 1 square, which a transform maps onto the shape.

Erase needs an opaque surface to punch through, so that one is drawn in a small image of
its own and blitted over the panel. Erasing on the panel would only take the backdrop out.

Press "Boot" to exit the program.

Section: Drawing from code
"""

# Constants for drawing
OVERLAY = color.rgb(8, 10, 14)          # Laid over the backdrop to calm it
CALM = 150                              # How far down, of 255, so the pens read over it
ACROSS = 2                              # Cells across the panel
DOWN = 3                                # And down it
REACH = 0.30                            # A circle's radius, as a fraction of the cell's narrower side
BLUR = 4                                # How far the blur pen reaches, in pixels
PAINT = 0.35                            # What the image pen scales its picture by
LABEL_DOWN = 0.34                       # Where a label sits below its circle, of the cell's height
BACKDROP = "/examples/assets/traces/traces3.png"
PICTURE = "/examples/assets/gold_macaw_card.png"  # What the image pen paints with
LABEL_FACE = font.match                 # A ROM pixel face, drawn at its own size

SUNSET = ((0.0, color.rgb(255, 94, 91)), (0.5, color.rgb(255, 209, 102)),
          (1.0, color.rgb(67, 138, 255)))
ORB = ((0.0, color.white), (0.35, color.rgb(120, 210, 255)), (1.0, color.rgb(18, 28, 84)))

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

canvas = screen.canvas()
canvas.antialias = image.X4
canvas.font = LABEL_FACE

CELL = canvas.width / ACROSS, canvas.height / DOWN
RADIUS = min(CELL) * REACH
# A gradient's 0 to 1 square mapped onto a circle's box about the origin
BOX = mat3().translate(-RADIUS, -RADIUS).scale(RADIUS * 2, RADIUS * 2)

try:
    backdrop_art = image.load(BACKDROP)
    picture = image.load(PICTURE)
except (ValueError, OSError):
    mighty.shutdown()
    raise RuntimeError(f"'{BACKDROP}' or '{PICTURE}' is missing or corrupt! Check both are on the board") from None

plate = image(round(CELL[0]), round(CELL[1]))


def middle(index):
    """Find where the cell at that place in the grid centres."""
    return (index % ACROSS + 0.5) * CELL[0], (index // ACROSS + 0.5) * CELL[1]


def placed(index):
    """Map a gradient's 0 to 1 square onto the circle in the cell at that place in the grid."""
    return mat3().translate(*middle(index)).multiply(BOX)


# Each pen is built already placed on its cell, with the picture centred on its circle. Erase has no pen here
image_at = middle(3)
PENS = (("colour", color.rgb(255, 150, 60)),
        # Left to right across the middle of the square
        ("linear", brush.gradient(brush.LINEAR, 0.0, 0.5, 1.0, 0.5, SUNSET, placed(1))),
        # From up and left of the middle, so the circle reads as a lit sphere
        ("radial", brush.gradient(brush.RADIAL, 0.35, 0.35, 1.0, 1.0, ORB, placed(2))),
        ("image", brush.image(picture, mat3().translate(image_at[0] - picture.width * PAINT / 2,
                                                         image_at[1] - picture.height * PAINT / 2)
                              .scale(PAINT))),
        ("blur", brush.blur(BLUR)),
        ("erase", None))


def backdrop():
    """Cover the panel in calmed detail, for the blur to soften and the erase to reveal."""
    # The landscape art turned a quarter and flipped, which covers the portrait panel unstretched
    # and keeps its bright pulse behind the pens
    canvas.pen = brush.image(backdrop_art,
                             mat3().translate(canvas.width, canvas.height).scale(1, -1).rotate(90))
    canvas.rectangle(0, 0, canvas.width, canvas.height)

    # Taken down so the pens and their names read over it, the detail surviving underneath
    canvas.pen = OVERLAY.with_alpha(CALM)
    canvas.rectangle(0, 0, canvas.width, canvas.height)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    backdrop()

    for index, (name, pen) in enumerate(PENS):
        across, down = middle(index)

        if pen is None:
            # An opaque plate, then erase takes alpha away to cut the hole
            plate.pen = color.rgb(30, 34, 44)
            plate.clear()
            plate.pen = brush.erase()
            plate.shape(shape.circle(CELL[0] / 2, CELL[1] / 2, RADIUS))
            canvas.blit(plate, rect(0, 0, plate.width, plate.height),
                        rect(round(across - CELL[0] / 2), round(down - CELL[1] / 2),
                             plate.width, plate.height))
        else:
            canvas.pen = pen
            canvas.shape(shape.circle(across, down, RADIUS))

        # Centred under the circle, taking a letter of this face as six pixels wide
        canvas.pen = color.white
        canvas.text(name, across - len(name) * 3, down + CELL[1] * LABEL_DOWN)

    screen.update(canvas)
    print(f"six pens, {RADIUS:.0f}px across each cell of {CELL[0]:.0f}x{CELL[1]:.0f}")

    # Nothing moves, so the panel holds its frame and this only waits
    while not mighty.boot_pressed():
        time.sleep(0.05)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
