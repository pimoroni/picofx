from picovector import color, image, shape, vec2

"""
Drawing: Tiled arrows
A panel filled from a tile whose edges do not meet, plain and then mirrored across in turn.
Section: Placing pictures
"""

# Entry: screenA rotation=90 tile=repeat: graphics file=tiled_arrows.py width=80 height=40 fps=10

# Constants
TILE = 40                        # The wedge is square, and this is its side
HOLD_MS = 3000                   # How long each mode is held for
INSET = 8                        # How far the arrow sits inside the tile
DARK = color.rgb(16, 16, 40)     # The wedge's shaded side
LIGHT = color.rgb(214, 84, 60)   # And its lit one
MARK = color.rgb(255, 240, 130)  # The arrow, which points the way the wedge brightens
ANTIALIAS = image.X4


def wedge(flipped):
    """Draw one wedge, or its reflection left to right as Tile.MIRROR shows every other copy."""
    tile = image(TILE, TILE)
    tile.antialias = ANTIALIAS
    for x in range(TILE):
        across = TILE - 1 - x if flipped else x
        tile.pen = color.mix(DARK, LIGHT, round(across * 255 / (TILE - 1)))
        tile.shape(shape.rectangle(x, 0, 1, TILE))

    near, far = (TILE - INSET, INSET) if flipped else (INSET, TILE - INSET)
    tile.pen = MARK
    tile.shape(shape.custom([vec2(near, INSET), vec2(near, TILE - INSET), vec2(far, TILE // 2)]))
    return tile


# The entry's tile mode is fixed, so the canvas is two wedges side by side repeated: the same
# wedge twice for a plain repeat, a wedge and its reflection for a mirrored one
PLAIN = wedge(False)
MIRRORED = wedge(True)

shown = None


def draw(canvas, elapsed):
    global shown
    mirrored = int(elapsed * 1000) // HOLD_MS % 2 == 1
    if mirrored == shown:
        return
    shown = mirrored

    canvas.blit(PLAIN, 0, 0)
    canvas.blit(MIRRORED if mirrored else PLAIN, TILE, 0)
