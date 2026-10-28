from picovector import color, image, mat3, shape

"""
Drawing: Shapes
Every shape picovector offers, each one filled and then stroked beside it, all turning.
Section: Drawing from code
"""

# Entry: screenA: graphics file=shapes.py

# Constants for drawing
BACKGROUND = color.rgb(10, 12, 16)      # The panel behind the shapes
ACROSS = 4                              # Cells across the panel, so two shapes to a pair
DOWN = 4                                # And down it
REACH = 0.34                            # How much of a cell's narrower side a shape takes
STROKE = 0.14                           # Stroke width, in the shape's own units
TURN_MS = 7000                          # How long a shape takes to come round
LIGHTNESS = 190                         # Every hue at one lightness, which is oklch's point
CHROMA = 110

# Each shape at unit size around the origin, filled and then stroked
SHAPES = (shape.rectangle(-1, -1, 2, 2), shape.rectangle(-1, -1, 2, 2).stroke(STROKE),
          shape.circle(0, 0, 1), shape.circle(0, 0, 1).stroke(STROKE),
          shape.ellipse(0, 0, 1, 0.6), shape.ellipse(0, 0, 1, 0.6).stroke(STROKE),
          shape.star(0, 0, 5, 0.5, 1), shape.star(0, 0, 5, 0.5, 1).stroke(STROKE),
          shape.squircle(0, 0, 1), shape.squircle(0, 0, 1).stroke(STROKE),
          shape.pie(0, 0, 1, 30, 300), shape.pie(0, 0, 1, 30, 300).stroke(STROKE),
          shape.arc(0, 0, 0.6, 1, 30, 300), shape.arc(0, 0, 0.6, 1, 30, 300).stroke(STROKE),
          shape.regular_polygon(0, 0, 1, 3), shape.regular_polygon(0, 0, 1, 3).stroke(STROKE))

# A cell's width and height, and how large a shape is drawn in it, set on the first call
cell = None
size = None


def draw(canvas, elapsed):
    global cell, size
    if cell is None:
        canvas.antialias = image.X4
        cell = canvas.width / ACROSS, canvas.height / DOWN
        size = min(cell) * REACH

    canvas.pen = BACKGROUND
    canvas.clear()

    turned = elapsed * 1000 / TURN_MS * 360
    for index, drawing in enumerate(SHAPES):
        canvas.pen = color.oklch(LIGHTNESS, CHROMA, index * 360 / len(SHAPES))

        across = (index % ACROSS + 0.5) * cell[0]
        down = (index // ACROSS + 0.5) * cell[1]
        drawing.transform = mat3().translate(across, down).rotate(turned).scale(size)
        canvas.shape(drawing)
