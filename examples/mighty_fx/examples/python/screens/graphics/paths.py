import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, font, image, mat3, shape, vec2

"""
Show every setting that decides how a path is drawn, side by side.

The rows show where a stroke sits against its edge, how segments join at a corner, how an
open line ends, and which parts a fill counts as inside. The pentagram's middle is enclosed
twice, so even-odd leaves it empty and nonzero fills it.

A stroke is sized in the shape's own units, so a unit-sized shape takes a thickness like 0.1.
A stroke needs even-odd to stay hollow, so put a changed fill rule back.

Press "Boot" to exit the program.
"""

# Constants for drawing
BACKGROUND = color.rgb(10, 12, 16)      # The panel behind the paths
PATH_COLOUR = color.rgb(120, 200, 255)  # The paths themselves
LABEL = color.white                     # And their names
ACROSS = 3                              # Cells across the panel
DOWN = 4                                # A row per family of settings
REACH = 0.30                            # A drawing's radius, of the cell's narrower side
THICKNESS = 0.16                        # Stroke thickness, in the drawing's own units
BOLD = 0.5                              # And for the joins and caps, which only show at width
LABEL_DOWN = 0.36                       # Where a name sits below its drawing, of the cell's height
LABEL_FACE = font.match                 # A ROM pixel face, drawn at its own size

ALIGNS = (("inner", shape.ALIGN_INNER), ("centre", shape.ALIGN_CENTER),
          ("outer", shape.ALIGN_OUTER))
JOINS = (("miter", shape.JOIN_MITER), ("round", shape.JOIN_ROUND), ("bevel", shape.JOIN_BEVEL))
CAPS = (("butt", shape.CAP_BUTT), ("round", shape.CAP_ROUND), ("square", shape.CAP_SQUARE))
RULES = (("even-odd", image.EVEN_ODD), ("nonzero", image.NON_ZERO))

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
REACH_PX = min(CELL) * REACH

# A star and a pentagram at unit size around the origin. The star runs anticlockwise as a custom
# path's winding decides its inside, and reversing it swaps ALIGN_INNER and ALIGN_OUTER
STAR = ((-0.28, -0.36), (-0.95, -0.31), (-0.44, 0.13), (-0.59, 0.81), (0.0, 0.44),
        (0.59, 0.81), (0.44, 0.13), (0.95, -0.31), (0.28, -0.36), (0.0, -1.0))
PENTAGRAM = ((0.0, -1.0), (0.588, 0.809), (-0.951, -0.309), (0.951, -0.309), (-0.588, 0.809))
CHEVRON = ((-1.0, -0.7), (0.0, 0.7), (1.0, -0.7))
SEGMENT = ((-1.0, 0.0), (1.0, 0.0))


def points(outline):
    """Turn a run of unit coordinates into the vectors a custom shape wants."""
    return [vec2(x, y) for x, y in outline]


def place(index):
    """Find where the cell at that place in the grid centres."""
    return (index % ACROSS + 0.5) * CELL[0], (index // ACROSS + 0.5) * CELL[1]


def drawn(outline, index, name, flags=None, rule=image.EVEN_ODD, thick=THICKNESS):
    """Draw one cell with its outline placed and stroked where the flags say so, then named."""
    across, down = place(index)
    figure = shape.custom(points(outline))
    if flags is not None:
        figure.stroke(thick, flags)

    figure.transform = mat3().translate(across, down).scale(REACH_PX)

    canvas.fill_rule = rule
    canvas.pen = PATH_COLOUR
    canvas.shape(figure)

    canvas.fill_rule = image.EVEN_ODD
    # Centred under the drawing, taking a letter of this face as six pixels wide
    canvas.pen = LABEL
    canvas.text(name, across - len(name) * 3, down + CELL[1] * LABEL_DOWN)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    canvas.pen = BACKGROUND
    canvas.clear()

    for index, (name, align) in enumerate(ALIGNS):
        drawn(STAR, index, name, align)

    # Joins and caps only show at width, so these two rows are drawn bold
    for index, (name, join) in enumerate(JOINS):
        drawn(CHEVRON, ACROSS + index, name, shape.ALIGN_CENTER | shape.PATH_OPEN | join,
              thick=BOLD)

    for index, (name, cap) in enumerate(CAPS):
        drawn(SEGMENT, ACROSS * 2 + index, name, shape.ALIGN_CENTER | shape.PATH_OPEN | cap,
              thick=BOLD)

    for index, (name, rule) in enumerate(RULES):
        drawn(PENTAGRAM, ACROSS * 3 + index, name, rule=rule)

    screen.update(canvas)
    print(f"stroke alignment, joins, caps and fill rules, {REACH_PX:.0f}px a drawing")

    # Nothing moves, so the panel holds its frame and this only waits
    while not mighty.boot_pressed():
        time.sleep(0.05)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
