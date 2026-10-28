from picovector import color, font, image, mat3, shape, vec2

"""
Drawing: Paths
Every setting that decides how a path is drawn, side by side.
Section: Drawing from code
"""

# Entry: screenA: graphics file=paths.py interval=60

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

STAR = ((-0.28, -0.36), (-0.95, -0.31), (-0.44, 0.13), (-0.59, 0.81), (0.0, 0.44),
        (0.59, 0.81), (0.44, 0.13), (0.95, -0.31), (0.28, -0.36), (0.0, -1.0))
PENTAGRAM = ((0.0, -1.0), (0.588, 0.809), (-0.951, -0.309), (0.951, -0.309), (-0.588, 0.809))
CHEVRON = ((-1.0, -0.7), (0.0, 0.7), (1.0, -0.7))
SEGMENT = ((-1.0, 0.0), (1.0, 0.0))

# A cell's size and a drawing's radius, set on the first call from the canvas
CELL = None
REACH_PX = 0


def points(outline):
    """Turn a run of unit coordinates into the vectors a custom shape wants."""
    return [vec2(x, y) for x, y in outline]


def place(index):
    """Find where the cell at that place in the grid centres."""
    return (index % ACROSS + 0.5) * CELL[0], (index // ACROSS + 0.5) * CELL[1]


def drawn(canvas, outline, index, name, flags=None, rule=image.EVEN_ODD, thick=THICKNESS):
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
    canvas.pen = LABEL
    canvas.text(name, across - len(name) * 3, down + CELL[1] * LABEL_DOWN)


def draw(canvas, _elapsed):
    global CELL, REACH_PX
    # Nothing moves, so the cells are drawn once and the canvas keeps them
    if CELL is not None:
        return

    CELL = canvas.width / ACROSS, canvas.height / DOWN
    REACH_PX = min(CELL) * REACH
    canvas.antialias = image.X4
    canvas.font = LABEL_FACE

    canvas.pen = BACKGROUND
    canvas.clear()

    for index, (name, align) in enumerate(ALIGNS):
        drawn(canvas, STAR, index, name, align)

    for index, (name, join) in enumerate(JOINS):
        drawn(canvas, CHEVRON, ACROSS + index, name, shape.ALIGN_CENTER | shape.PATH_OPEN | join,
              thick=BOLD)

    for index, (name, cap) in enumerate(CAPS):
        drawn(canvas, SEGMENT, ACROSS * 2 + index, name, shape.ALIGN_CENTER | shape.PATH_OPEN | cap,
              thick=BOLD)

    for index, (name, rule) in enumerate(RULES):
        drawn(canvas, PENTAGRAM, ACROSS * 3 + index, name, rule=rule)
