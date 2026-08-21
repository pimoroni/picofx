import sys
import time

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, font, image, mat3, shape, vec2

"""
Every setting that decides how a path is drawn, four rows of three.

Where the stroke sits against the edge it traces, inside it, centred on it or outside it.
How two segments meet at a corner, mitred to a point, rounded off, or cut across. How a
line that goes nowhere else ends, cut square at the point, rounded past it, or squared past
it. And which parts of a path a fill counts as inside, which only shows itself where a path
crosses itself: the pentagram's middle is enclosed twice, so even-odd leaves it empty and
nonzero fills it.

Two things worth carrying away. A stroke is described in the shape's own units, so a shape
built at unit size takes a thickness like 0.1 rather than 2. And a stroke is drawn as a
ribbon with a hollow middle, which needs the even-odd rule to stay hollow, so a fill rule
set for something else has to be put back.

Press "Boot" to exit the program.
"""

# Constants for drawing
GROUND = color.rgb(10, 12, 16)          # The panel behind the paths
INK = color.rgb(120, 200, 255)          # The paths themselves
LABEL = color.white                     # And their names
ACROSS = 3                              # Cells across the panel
DOWN = 4                                # A row per family of settings
REACH = 0.30                            # A drawing's radius, of the cell's narrower side
THICK = 0.16                            # Stroke thickness, in the drawing's own units
BOLD = 0.5                              # And for the joins and caps, which only show at width
LABEL_DOWN = 0.36                       # Where a name sits below its drawing, of the cell's height
LABEL_FACE = "match"                    # A ROM pixel face, drawn at its own size

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
canvas.font = getattr(font, LABEL_FACE)

CELL = canvas.width / ACROSS, canvas.height / DOWN
REACH_PX = min(CELL) * REACH

# A star and a pentagram, both at unit size around the origin. The pentagram's edges each
# skip a point, so the path crosses itself and the middle is enclosed twice.
#
# The star is wound anticlockwise, and that is not decoration: which side of a custom path
# counts as its inside is decided by the direction the points run, so winding it the other way
# swaps what ALIGN_INNER and ALIGN_OUTER do. Measured on this board, the same star reversed
# strokes 86px wide where this one strokes 56px
STAR = ((-0.28, -0.36), (-0.95, -0.31), (-0.44, 0.13), (-0.59, 0.81), (0.0, 0.44),
        (0.59, 0.81), (0.44, 0.13), (0.95, -0.31), (0.28, -0.36), (0.0, -1.0))
PENTAGRAM = ((0.0, -1.0), (0.588, 0.809), (-0.951, -0.309), (0.951, -0.309), (-0.588, 0.809))
CHEVRON = ((-1.0, -0.7), (0.0, 0.7), (1.0, -0.7))
SEGMENT = ((-1.0, 0.0), (1.0, 0.0))


def points(outline):
    """A run of unit coordinates as the vectors a custom shape wants."""
    return [vec2(x, y) for x, y in outline]


def place(index):
    """Where the cell at that place in the grid centres."""
    return (index % ACROSS + 0.5) * CELL[0], (index // ACROSS + 0.5) * CELL[1]


def drawn(outline, index, name, flags=None, rule=image.EVEN_ODD, thick=THICK):
    """One cell: the outline placed and drawn, stroked where flags say so, then named."""
    across, down = place(index)
    figure = shape.custom(points(outline))
    if flags is not None:
        figure.stroke(thick, flags)

    figure.transform = mat3().translate(across, down).scale(REACH_PX)

    canvas.fill_rule = rule
    canvas.pen = INK
    canvas.shape(figure)

    canvas.fill_rule = image.EVEN_ODD
    canvas.pen = LABEL
    canvas.text(name, across - len(name) * 3, down + CELL[1] * LABEL_DOWN)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    canvas.pen = GROUND
    canvas.clear()

    for index, (name, align) in enumerate(ALIGNS):
        drawn(STAR, index, name, align)

    # A join and a cap are features of the stroke's own width, so these two rows are drawn
    # bold: at a hairline all three of each look the same
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
