import sys

from mighty_fx import MightyFX, SPCE
from picovector import color, shape, vec2
from screens import SCREEN_TYPES, Reserve, ScreenPair

"""
Lay a different carpet on each panel of a pair, each tiled from a scrap of a pattern and
each drifting its own way.

Every placement setting a screen takes, a pair takes one of per screen, and this sends two
images and an offset each in a single call. One panel carries interlocking hexagons,
drifting on the diagonal; the other carries tumbling blocks, drifting sideways. Nothing
about the two has to agree.

Both tiles are tiny, because a pattern is only ever the smallest piece that repeats. The
hexagons need two rows, the second half a tile across, and the blocks two of themselves,
every other one sitting half a step across and down. Between them that is 69KB for two
panels of carpet, where two panel-sized images would be over 600KB.

The hexagons are the interesting one to draw. Each motif is three hexagons inside one
another, taller than they are wide, with a slot of ground cut out of the outer one at one
end. That slot is the whole pattern: it stops the ring reading as a closed loop and lets
the ground run in and on to the next motif, and the two rows take their slot at opposite
ends, so the openings face each other and the ground threads between them.

Neither pattern is mirrored, which is worth saying since Tile.MIRROR hides a join for
nothing elsewhere. The blocks are lit from one side, so a reflected copy is lit from the
other and the seam becomes the loudest thing on the panel; worse, the cubes meet their own
reflection and the faces stop lining up. Mirroring is for art with no direction to lose,
which is what kaleidoscope.py trades on.

Neither is drawn after startup. The drift is the offset, and it costs nothing.

Press "Boot" to exit the program.
"""

# Constants
ROTATION = 0             # Panels upright, side by side
# The hexagon carpet, at half the size of the tile it was measured from
HEX_RINGS = ((41, 48), (28, 33), (14, 17))   # Half width and half height, outside in
HEX_ROW = 51             # How far below one row of hexagons the next one sits
HEX_W, HEX_H = 96, 136   # The tile: two rows, the second half a tile across

# The slot is the black channel between two motifs, carried on through the ring, so it is
# half a tile less the hexagon and its edges line up with the flanks either side of it. A
# pixel narrower and the row above spills into the channel, thinning it by two where the
# rows meet, which reads as the tiles being out of step
HEX_NOTCH = HEX_W // 2 - HEX_RINGS[0][0]
BLOCK_H = 15             # Half the height of a block's top face
HEX_STEP = 1             # Pixels the hexagons drift each frame, on the diagonal
BLOCK_STEP = 1           # And the blocks, sideways

# The hexagons: every hotel corridor of a certain vintage
GROUND = color.rgb(223, 95, 24)
INK = color.rgb(0, 0, 0)
HEART = color.rgb(152, 31, 36)
HEX_INKS = (GROUND, INK, HEART)   # One per ring, outside in

# The blocks: a top face the light falls on, and two sides turned away from it by different
# amounts, which is the whole trick to three rhombi reading as a cube
TOP = color.rgb(206, 202, 194)
LEFT = color.rgb(0, 104, 106)
RIGHT = color.rgb(172, 140, 48)
SEAM = color.rgb(58, 54, 50)

# All three rhombi of a block are the same rhombus turned three ways, which is what makes
# the cube read as a cube. That holds when a face is as wide as its height times the root
# of three, so the sides come out as deep as the top face is tall
BLOCK_W = round(BLOCK_H * 1.7320508)
BLOCK_DEPTH = BLOCK_H * 2

# Which screens are on the ports, "2.8" or "1.54", or what the effects file passes in args.
# A pair wants two of the same size, each panel holding its own picture
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with both SP/CE ports set up for screens, and a panel on each
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A pair holds both panels to one refresh rate and keeps their scans together
pair = ScreenPair(ScreenType(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES),
                  ScreenType(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES))
first, second = pair.screens

hexagons = first.canvas(HEX_W, HEX_H)

# Two blocks, the second the half step that interlocks them
BLOCK_TILE_W, BLOCK_TILE_H = BLOCK_W * 2, BLOCK_H * 6
blocks = second.canvas(BLOCK_TILE_W, BLOCK_TILE_H)

print(f"a {HEX_W}x{HEX_H} carpet and a {BLOCK_TILE_W}x{BLOCK_TILE_H} one,"
      f" {(HEX_W * HEX_H + BLOCK_TILE_W * BLOCK_TILE_H) * 4 // 1024}KB for two panels")


def hexagon(cx, cy, rx, ry):
    """A hexagon with points top and bottom and flat sides, taller than it is wide."""
    return shape.custom([vec2(cx, cy - ry), vec2(cx + rx, cy - ry / 2),
                         vec2(cx + rx, cy + ry / 2), vec2(cx, cy + ry),
                         vec2(cx - rx, cy + ry / 2), vec2(cx - rx, cy - ry / 2)])


def motif(cx, cy, notch_up):
    """One hexagon of rings, with the slot of ground that opens one end of it.

    notch_up puts the slot at the top, which is what the second row of every tile takes;
    the first row takes it at the bottom, so the two rows open towards each other.
    """
    # The outer ring first, then the notch taken out of it, and the rings inside it over
    # the top: the notch belongs to the outer ring alone and leaves the middle whole
    outer_rx, outer_ry = HEX_RINGS[0]
    hexagons.pen = HEX_INKS[0]
    hexagons.shape(hexagon(cx, cy, outer_rx, outer_ry))

    tip = cy - outer_ry if notch_up else cy + outer_ry
    hexagons.pen = INK
    hexagons.shape(shape.custom([vec2(cx - HEX_NOTCH, tip), vec2(cx + HEX_NOTCH, tip),
                                 vec2(cx + HEX_NOTCH, cy), vec2(cx - HEX_NOTCH, cy)]))

    for (rx, ry), pen in zip(HEX_RINGS[1:], HEX_INKS[1:]):
        hexagons.pen = pen
        hexagons.shape(hexagon(cx, cy, rx, ry))


def face(points):
    """One rhombus of a block, outlined so the pattern reads as woven rather than printed."""
    corners = [vec2(x, y) for x, y in points]
    blocks.shape(shape.custom(corners))
    blocks.pen = SEAM
    blocks.shape(shape.custom(corners).stroke(1))


def block(cx, cy):
    """The three faces of one block, its top face centred on (cx, cy)."""
    blocks.pen = TOP
    face(((cx, cy - BLOCK_H), (cx + BLOCK_W, cy), (cx, cy + BLOCK_H), (cx - BLOCK_W, cy)))
    blocks.pen = LEFT
    face(((cx - BLOCK_W, cy), (cx, cy + BLOCK_H), (cx, cy + BLOCK_H + BLOCK_DEPTH),
          (cx - BLOCK_W, cy + BLOCK_DEPTH)))
    blocks.pen = RIGHT
    face(((cx + BLOCK_W, cy), (cx, cy + BLOCK_H), (cx, cy + BLOCK_H + BLOCK_DEPTH),
          (cx + BLOCK_W, cy + BLOCK_DEPTH)))


# Both patterns are drawn a step past every edge, so a motif crossing one is completed by
# the copy of it that wraps to the far side. The ground is the ink here, with the hexagons
# laid over it: two rows to a tile, the second half a tile across and slotted the other way
hexagons.pen = INK
hexagons.clear()

# A whole row at a time, and the rows in a fixed order. The two rows overlap, so whichever
# is painted second takes a few pixels off the other where they cross: doing one row and
# then the other spends those pixels the same way on both sides of every motif. Painting
# each motif with its neighbour instead leaves a step, one side eaten and the other not
for down in range(-1, 2):
    for across in range(-1, 3):
        motif(across * HEX_W, down * HEX_H, False)
for down in range(-1, 2):
    for across in range(-1, 3):
        motif(across * HEX_W + HEX_W / 2, down * HEX_H + HEX_ROW, True)

# The rasteriser does not treat the two slopes of a diagonal alike, so the halves of a
# motif can come out a pixel different. This pattern is symmetric, so the left half is
# mirrored into the right rather than trusted to match: a stray pixel at the edge of a
# tile reads as the tiles not meeting, which is the one fault a tiled source cannot hide.
# It also makes the wrap exact, the last column being the mirror of the first
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

        # Two images and an offset each, in one call: the hexagons drift on the diagonal
        # and the blocks sideways, from one tile setting they happen to share
        pair.update(hexagons, blocks, rotation=ROTATION, tile=True,
                    offset=((-hex_at, -hex_at), (-block_at, 0)))
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
