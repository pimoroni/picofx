import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import brush, color, font, image, mat3, rect, shape

"""
Fill the same circle six ways, because a pen is not only a colour.

A colour, a linear gradient, a radial one, an image, a blur that takes what is already
under it, and an erase that takes the pixels away. The last two only make sense over
something, so the panel starts covered in a pattern for them to work on.

A gradient's axis lives in a 0 to 1 square and a transform maps that square onto whatever
it is filling. Building one costs a 256 entry table, which depends only on the colour
stops, so an axis that moves is repositioned with geometry() rather than rebuilt.

Erase needs an opaque surface to punch through, so that one is drawn in a small image of
its own and blitted over the panel: erasing on the panel would only take the backdrop out.

Press "Boot" to exit the program.
"""

# Constants for drawing
GROUND = color.rgb(8, 10, 14)           # Laid over the backdrop to calm it
CALM = 150                              # How far down, of 255, so the pens read over it
ACROSS = 2                              # Cells across the panel
DOWN = 3                                # And down it
REACH = 0.30                            # A circle's radius, as a fraction of the cell's narrower side
BLUR = 4                                # How far the blur pen reaches, in pixels
PAINT = 0.35                            # What the image pen scales its picture by
LABEL_DOWN = 0.34                       # Where a label sits below its circle, of the cell's height
BACKDROP = "/examples/assets/traces/traces3.png"
PICTURE = "/examples/assets/gold_macaw_card.png"  # What the image pen paints with
LABEL_FACE = "match"                    # A ROM pixel face, drawn at its own size

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
canvas.font = getattr(font, LABEL_FACE)

CELL = canvas.width / ACROSS, canvas.height / DOWN
RADIUS = min(CELL) * REACH
BOX = mat3().translate(-RADIUS, -RADIUS).scale(RADIUS * 2, RADIUS * 2)

backdrop_art = image.load(BACKDROP)
picture = image.load(PICTURE)

# Every pen built once. A gradient's stops decide its table, so only the axis moves later
plain = color.rgb(255, 150, 60)
linear = brush.gradient(brush.LINEAR, 0.0, 0.5, 1.0, 0.5, SUNSET, BOX)
radial = brush.gradient(brush.RADIAL, 0.35, 0.35, 1.0, 1.0, ORB, BOX)
blurred = brush.blur(BLUR)

# An image pen carries a transform and no table, so it costs nothing to build where it is
# wanted, which is what "pictured" stands for in the list below
pictured = "image"

# The erase cell is a plate with a hole in it, so it needs somewhere of its own to be opaque
plate = image(round(CELL[0]), round(CELL[1]))

PENS = (("colour", plain), ("linear", linear), ("radial", radial),
        ("image", pictured), ("blur", blurred), ("erase", None))


def middle(index):
    """Where the cell at that place in the grid centres."""
    return (index % ACROSS + 0.5) * CELL[0], (index // ACROSS + 0.5) * CELL[1]


def backdrop():
    """The panel covered in detail, then calmed, so every pen has something under it.

    The blur wants detail to soften and the erase wants something to reveal, and a flat
    colour gives neither of them anything to show.
    """
    canvas.blit(backdrop_art, rect(0, 0, backdrop_art.width, backdrop_art.height),
                rect(0, 0, canvas.width, canvas.height))

    # Taken down so the pens and their names read over it, the detail surviving underneath
    canvas.pen = GROUND.with_alpha(CALM)
    canvas.rectangle(0, 0, canvas.width, canvas.height)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    backdrop()

    for index, (name, pen) in enumerate(PENS):
        across, down = middle(index)

        if pen is None:
            # An opaque plate, then the hole: erase takes alpha away where it draws
            plate.pen = color.rgb(30, 34, 44)
            plate.clear()
            plate.pen = brush.erase()
            plate.shape(shape.circle(CELL[0] / 2, CELL[1] / 2, RADIUS))
            canvas.blit(plate, rect(0, 0, plate.width, plate.height),
                        rect(round(across - CELL[0] / 2), round(down - CELL[1] / 2),
                             plate.width, plate.height))
        else:
            # A gradient and an image pen are described around the origin, so each is
            # moved to the cell it fills rather than being built there
            if pen is linear:
                pen.geometry(0.0, 0.5, 1.0, 0.5, mat3().translate(across, down).multiply(BOX))
            elif pen is radial:
                pen.geometry(0.35, 0.35, 1.0, 1.0, mat3().translate(across, down).multiply(BOX))
            elif pen is pictured:
                # Centred on the circle, so what shows through is the middle of the picture
                # rather than whatever happens to be in its top corner
                pen = brush.image(picture, mat3()
                                  .translate(across - picture.width * PAINT / 2,
                                             down - picture.height * PAINT / 2)
                                  .scale(PAINT))

            canvas.pen = pen
            canvas.shape(shape.circle(across, down, RADIUS))

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
