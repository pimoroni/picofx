import sys

from mighty_fx import MightyFX, SPCE
from picovector import color, shape, vec2
from screens import SCREEN_TYPES, Reserve, ScreenPair

"""
Lay a different drifting carpet on each panel of a pair, each tiled from a small scrap of pattern.

A pair takes every placement setting once per screen, so one call sends two images and an
offset each. The hexagons drift on the diagonal and the blocks sideways.

Each tile is about a ninth of the full-panel image it replaces, and the drift is only the offset.

Press "Boot" to exit the program.

Section: Across several screens
"""

# Constants
ROTATION = 0             # Panels upright, side by side
# The hexagon carpet, at half the size of the tile it was measured from
HEX_RINGS = ((41, 48), (28, 33), (14, 17))   # Half width and half height, outside in
HEX_ROW = 51             # How far below one row of hexagons the next one sits
HEX_W, HEX_H = 96, 136   # The tile of two rows, the second half a tile across

# The black channel between motifs, half a tile less the hexagon so its edges meet both flanks
HEX_NOTCH = HEX_W // 2 - HEX_RINGS[0][0]
BLOCK_H = 15             # Half the height of a block's top face
HEX_STEP = 1             # Pixels the hexagons drift each frame, on the diagonal
BLOCK_STEP = 1           # And the blocks, sideways

# The hexagons, every hotel corridor of a certain vintage
ORANGE = color.rgb(223, 95, 24)
BLACK = color.rgb(0, 0, 0)
HEART = color.rgb(152, 31, 36)
HEX_COLOURS = (ORANGE, BLACK, HEART)    # One per ring, outside in

# The blocks, a lit top face and two sides turned away by different amounts
TOP = color.rgb(206, 202, 194)
LEFT = color.rgb(0, 104, 106)
RIGHT = color.rgb(172, 140, 48)
SEAM = color.rgb(58, 54, 50)

# A face as wide as its height times root three makes the sides as deep as the top is tall
BLOCK_W = round(BLOCK_H * 1.7320508)
BLOCK_DEPTH = BLOCK_H * 2

# Which screens are on the ports, "2.8" or "1.54", or what the effects file passes in args.
# A pair wants two of the same size, each panel holding its own picture
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with both SP/CE ports set up for screens, and a panel on each
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A pair holds both panels to one refresh rate and keeps their scans together
pair = ScreenPair(ScreenType(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES, rotation=ROTATION),
                  ScreenType(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES, rotation=ROTATION))
first, second = pair.screens

hexagons = first.canvas(HEX_W, HEX_H)

# Two blocks, the second the half step that interlocks them
BLOCK_TILE_W, BLOCK_TILE_H = BLOCK_W * 2, BLOCK_H * 6
blocks = second.canvas(BLOCK_TILE_W, BLOCK_TILE_H)

print(f"a {HEX_W}x{HEX_H} carpet and a {BLOCK_TILE_W}x{BLOCK_TILE_H} one,"
      f" {(HEX_W * HEX_H + BLOCK_TILE_W * BLOCK_TILE_H) * 4 // 1024}KB for two panels")


def hexagon(cx, cy, rx, ry):
    """Build a hexagon with points top and bottom and flat sides, taller than it is wide."""
    return shape.custom([vec2(cx, cy - ry), vec2(cx + rx, cy - ry / 2),
                         vec2(cx + rx, cy + ry / 2), vec2(cx, cy + ry),
                         vec2(cx - rx, cy + ry / 2), vec2(cx - rx, cy - ry / 2)])


def motif(cx, cy, notch_up):
    """Draw one hexagon of rings with a black slot at one end, at the top where notch_up is set."""
    # The outer ring, its notch, then the inner rings over it so the middle stays whole
    outer_rx, outer_ry = HEX_RINGS[0]
    hexagons.pen = HEX_COLOURS[0]
    hexagons.shape(hexagon(cx, cy, outer_rx, outer_ry))

    tip = cy - outer_ry if notch_up else cy + outer_ry
    hexagons.pen = BLACK
    hexagons.shape(shape.custom([vec2(cx - HEX_NOTCH, tip), vec2(cx + HEX_NOTCH, tip),
                                 vec2(cx + HEX_NOTCH, cy), vec2(cx - HEX_NOTCH, cy)]))

    for (rx, ry), pen in zip(HEX_RINGS[1:], HEX_COLOURS[1:]):
        hexagons.pen = pen
        hexagons.shape(hexagon(cx, cy, rx, ry))


def face(points):
    """Draw one rhombus of a block, outlined so the pattern reads as woven rather than printed."""
    corners = [vec2(x, y) for x, y in points]
    blocks.shape(shape.custom(corners))
    blocks.pen = SEAM
    blocks.shape(shape.custom(corners).stroke(1))


def block(cx, cy):
    """Draw the three faces of one block, its top face centred on (cx, cy)."""
    blocks.pen = TOP
    face(((cx, cy - BLOCK_H), (cx + BLOCK_W, cy), (cx, cy + BLOCK_H), (cx - BLOCK_W, cy)))
    blocks.pen = LEFT
    face(((cx - BLOCK_W, cy), (cx, cy + BLOCK_H), (cx, cy + BLOCK_H + BLOCK_DEPTH),
          (cx - BLOCK_W, cy + BLOCK_DEPTH)))
    blocks.pen = RIGHT
    face(((cx + BLOCK_W, cy), (cx, cy + BLOCK_H), (cx, cy + BLOCK_H + BLOCK_DEPTH),
          (cx + BLOCK_W, cy + BLOCK_DEPTH)))


# Both patterns are drawn a step past every edge, so a motif crossing one is completed by its wrapped copy
hexagons.pen = BLACK
hexagons.clear()

# A whole row at a time, so where rows overlap the second covers both sides of every motif alike
for down in range(-1, 2):
    for across in range(-1, 3):
        motif(across * HEX_W, down * HEX_H, False)
for down in range(-1, 2):
    for across in range(-1, 3):
        motif(across * HEX_W + HEX_W / 2, down * HEX_H + HEX_ROW, True)

# The rasteriser can draw a diagonal's two slopes a pixel apart, so the left half is mirrored
# into the right. That also makes the wrap exact
raw, stride = hexagons.raw, hexagons.stride
for row in range(HEX_H):
    line = row * stride
    for column in range(HEX_W // 2):
        near = line + column * 4
        far = line + (HEX_W - 1 - column) * 4
        raw[far:far + 4] = raw[near:near + 4]

blocks.pen = SEAM
blocks.clear()
for column in range(-1, 2):
    for row in range(-1, 3):
        block(column * BLOCK_TILE_W, row * BLOCK_TILE_H)
        block(column * BLOCK_TILE_W + BLOCK_W, row * BLOCK_TILE_H + BLOCK_H * 3)

frames = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        hex_at = frames * HEX_STEP
        block_at = frames * BLOCK_STEP

        # Two images and an offset each, sharing one tile setting
        pair.update(hexagons, blocks, offset=((-hex_at, -hex_at), (-block_at, 0)), tile=True)
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
