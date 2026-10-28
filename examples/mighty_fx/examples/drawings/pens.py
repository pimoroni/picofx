from picovector import brush, color, font, image, mat3, rect, shape

"""
Drawing: Pens
The same circle filled with six different pens, from a plain colour to a picture.
Section: Drawing from code
"""

# Entry: screenA: graphics file=pens.py interval=60

# Constants for drawing
OVERLAY = color.rgb(8, 10, 14)
CALM = 150
ACROSS = 2
DOWN = 3
REACH = 0.30
BLUR = 4
PAINT = 0.35
LABEL_DOWN = 0.34
BACKDROP = "/examples/assets/traces/traces3.png"
PICTURE = "/examples/assets/gold_macaw_card.png"
LABEL_FACE = font.match

SUNSET = ((0.0, color.rgb(255, 94, 91)), (0.5, color.rgb(255, 209, 102)),
          (1.0, color.rgb(67, 138, 255)))
ORB = ((0.0, color.white), (0.35, color.rgb(120, 210, 255)), (1.0, color.rgb(18, 28, 84)))

try:
    backdrop_art = image.load(BACKDROP)
    picture = image.load(PICTURE)
except (ValueError, OSError):
    raise RuntimeError(f"'{BACKDROP}' or '{PICTURE}' is missing or corrupt! Check both are on the drive") from None

# The cell and circle sizes, set on the first call from the canvas
cell = None
radius = 0
drawn = False


def middle(index):
    """Find where the cell at that place in the grid centres."""
    return (index % ACROSS + 0.5) * cell[0], (index // ACROSS + 0.5) * cell[1]


def placed(index, box):
    """Map a gradient's 0 to 1 square onto the circle in the cell at that place in the grid."""
    return mat3().translate(*middle(index)).multiply(box)


def backdrop(canvas):
    """Cover the panel in calmed detail, for the blur to soften and the erase to reveal."""
    canvas.pen = brush.image(backdrop_art,
                             mat3().translate(canvas.width, canvas.height).scale(1, -1).rotate(90))
    canvas.rectangle(0, 0, canvas.width, canvas.height)

    canvas.pen = OVERLAY.with_alpha(CALM)
    canvas.rectangle(0, 0, canvas.width, canvas.height)


def draw(canvas, _elapsed):
    global cell, radius, drawn
    # Nothing moves, so the pens are drawn once and the canvas keeps them
    if drawn:
        return
    drawn = True

    canvas.antialias = image.X4
    canvas.font = LABEL_FACE

    cell = canvas.width / ACROSS, canvas.height / DOWN
    radius = min(cell) * REACH
    box = mat3().translate(-radius, -radius).scale(radius * 2, radius * 2)
    plate = image(round(cell[0]), round(cell[1]))

    image_at = middle(3)
    pens = (("colour", color.rgb(255, 150, 60)),
            ("linear", brush.gradient(brush.LINEAR, 0.0, 0.5, 1.0, 0.5, SUNSET, placed(1, box))),
            ("radial", brush.gradient(brush.RADIAL, 0.35, 0.35, 1.0, 1.0, ORB, placed(2, box))),
            ("image", brush.image(picture, mat3().translate(image_at[0] - picture.width * PAINT / 2,
                                                             image_at[1] - picture.height * PAINT / 2)
                                  .scale(PAINT))),
            ("blur", brush.blur(BLUR)),
            ("erase", None))

    backdrop(canvas)

    for index, (name, pen) in enumerate(pens):
        across, down = middle(index)

        if pen is None:
            # An opaque plate, then erase takes alpha away to cut the hole
            plate.pen = color.rgb(30, 34, 44)
            plate.clear()
            plate.pen = brush.erase()
            plate.shape(shape.circle(cell[0] / 2, cell[1] / 2, radius))
            canvas.blit(plate, rect(0, 0, plate.width, plate.height),
                        rect(round(across - cell[0] / 2), round(down - cell[1] / 2),
                             plate.width, plate.height))
        else:
            canvas.pen = pen
            canvas.shape(shape.circle(across, down, radius))

        canvas.pen = color.white
        canvas.text(name, across - len(name) * 3, down + cell[1] * LABEL_DOWN)
