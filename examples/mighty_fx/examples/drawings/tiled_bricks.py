from picovector import color, shape

"""
Drawing: Tiled bricks
A brick wall drawn from a tile of 32 by 32 pixels, sliding to show it has no seam.
Section: Placing pictures
"""

# Entry: screenA rotation=90 tile=repeat: graphics file=tiled_bricks.py width=32 height=32

# Constants
BRICK_W = 32             # A brick and its mortar, which is the tile's width
BRICK_H = 16             # A course, two of which is the tile's height
MORTAR = 3               # How wide the gaps between bricks are
STEP = 1                 # Pixels the wall slides each frame
FACE = color.rgb(168, 68, 52)
FACE_TOP = color.rgb(196, 96, 76)     # The weathered top edge of a brick
FACE_FOOT = color.rgb(132, 48, 38)    # And its shaded foot
GROUT = color.rgb(196, 188, 172)

frames = 0


def brick(canvas, x, y):
    """Draw one brick at (x, y), its face laid over the mortar with a lit top and dark foot."""
    width, height = BRICK_W - MORTAR, BRICK_H - MORTAR
    canvas.pen = FACE_TOP
    canvas.shape(shape.rectangle(x, y, width, height))
    canvas.pen = FACE
    canvas.shape(shape.rectangle(x, y + 1, width, height - 2))
    canvas.pen = FACE_FOOT
    canvas.shape(shape.rectangle(x, y + height - 1, width, 1))


def draw(canvas, _elapsed):
    global frames

    # The entry's offset is fixed, so the slide happens inside the tile, the pattern drawn
    # at its shifted origin and once more a tile up and left to cover the wrap
    shift_x = frames * STEP % BRICK_W
    shift_y = frames * STEP % (BRICK_H * 2)
    frames += 1

    canvas.pen = GROUT
    canvas.clear()
    for origin_x in (shift_x - BRICK_W, shift_x):
        for origin_y in (shift_y - BRICK_H * 2, shift_y):
            brick(canvas, origin_x, origin_y)
            brick(canvas, origin_x + BRICK_W // 2, origin_y + BRICK_H)
            brick(canvas, origin_x + BRICK_W // 2 - BRICK_W, origin_y + BRICK_H)
