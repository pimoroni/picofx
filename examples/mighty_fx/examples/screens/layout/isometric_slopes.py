import math
import sys

from mighty_fx import MightyFX, SPCE
from picovector import color, image, shape, vec2
from screens import SCREEN_TYPES

"""
Fly for ever over a rolling isometric landscape that is drawn once, into a single tile.
tile=True has the driver repeat that tile in both directions, so every frame after startup
costs nothing but a larger offset: no drawing, and nothing to reset when the view passes
the tile's edge.

The ground slopes because its height is held at the corners of the lattice and not at the
middle of each cell. A cell whose four corners sit at different heights is drawn as a
sloping quad, and neighbouring cells share those corners, so the surface comes out
continuous rather than as steps. Which way a cell tilts also decides how much light it
takes, which is what makes the hills read as hills.

It tiles cleanly because the height at every corner is looked up by wrapped coordinates and
the loops run past the tile's edges, so a hill straddling one finishes itself on the
opposite one.

The view wanders instead of running in a line, on a heading that keeps bending, which is
what an offset being any integer at all is worth: the course never has to be brought back
inside the tile, so a path can be whatever suits the picture. isometric_neon.py holds a
straight line instead, and mirrors its tile sideways rather than repeating it.

The view moves a fixed step per frame rather than by the clock. Each frame waits for the
panel's tearing signal, which paces them evenly, so counting frames gives smoother motion
than reading the clock: a step taken from elapsed time varies with however long the frame
before it took.

Press "Boot" to exit the program.
"""

# Constants
ROTATION = 90               # Quarter turn, to suit how the screen is mounted
TILE_W, TILE_H = 320, 256   # The tile's repeat, a screenful of pixels
CELL_W, CELL_H = 32, 16     # One cell of ground, twice as wide as tall
RELIEF = 44                 # Pixels between the lowest ground and the highest
SPEED = 1.6                 # Pixels of ground the view crosses each frame
TURN_WIDE = 700             # Frames the slow half of the wander takes to come round
TURN_TIGHT = 260            # And the quick half, which bends the course inside the slow one
TREE_H = 21                 # How tall a tree stands above its ground
TREE_W = 8                  # Half the width of the lowest branches
TRUNK_H = 5                 # How much of the trunk shows below the needles
TREE_SPACING = 3            # One cell in this many carries a tree, inside a wood
WOOD_LINE = 0.15            # How much of the map is wooded, -1 for none and 1 for all
TREE_GROUND = 5             # How level a cell must be to grow one, in pixels

# Two greens for the ground, the higher one paler, each cell alternating light and dark
# against its neighbours so the field reads as a checkerboard the way the era's did
HUES = ((36, 172, 108), (196, 216, 96))
CHECKER = 0.74              # How much darker every other cell is drawn
SHADES = (0.62, 0.74, 0.86, 0.96, 1.04, 1.12, 1.2)   # Light a facet takes, by its tilt
SEAM = 0.55                 # The fold between two cells, against the cell's own colour
CANOPY = color.rgb(16, 92, 52)
CANOPY_LIT = color.rgb(52, 148, 76)
TRUNK = color.rgb(84, 52, 28)
SHADOW = color.rgb(20, 108, 72)

# The lattice: a corner sits at (p * CELL_W / 2, q * CELL_H / 2), and a cell's centre at
# the same spacing on the other parity, which is what interlocks them. Both counts are
# the tile's own repeat, so a corner looked up past the edge is the one that wraps to it
P_PERIOD = TILE_W // (CELL_W // 2)
Q_PERIOD = TILE_H // (CELL_H // 2)
HALF_W, HALF_H = CELL_W // 2, CELL_H // 2

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a)

# The tile is drawn once and never touched again, so it lives in the heap rather than in
# the fast SRAM a canvas would claim: converting a heap source still finishes inside the
# time the frame spends on the wire
terrain = image(TILE_W, TILE_H)


def tinted(rgb, factor):
    """One of the ground's greens at a fraction of its brightness."""
    return color.rgb(min(255, int(rgb[0] * factor)), min(255, int(rgb[1] * factor)),
                     min(255, int(rgb[2] * factor)))


def corner_height(p, q):
    """The ground's height in pixels at lattice corner (p, q).

    Every term completes a whole number of cycles across the tile, on both axes, so
    the field meets itself exactly at the edges.
    """
    across, down = p / P_PERIOD, q / Q_PERIOD
    total = (0.5 * math.sin(2 * math.pi * across)
             + 0.5 * math.sin(2 * math.pi * down)
             + 0.3 * math.sin(2 * math.pi * (across + down))
             + 0.3 * math.sin(2 * math.pi * (2 * across - down))
             + 0.2 * math.sin(2 * math.pi * (across - 2 * down)))
    return (total / 1.8 + 1) / 2 * RELIEF


# One height per corner, so a corner shared by four cells is worked out once and they
# all agree on it, which is what leaves the surface without a crack
CORNERS = [[corner_height(p, q) for q in range(Q_PERIOD)] for p in range(P_PERIOD)]


def height(p, q):
    return CORNERS[p % P_PERIOD][q % Q_PERIOD]


def wooded(u, v):
    """Whether this part of the map carries woodland, on its own broad scale.

    Trees gather into woods rather than standing one to a field, so where they grow is
    a slow field of its own and which cell holds one is the scatter below.
    """
    across, down = u / P_PERIOD, v / Q_PERIOD
    return (math.sin(2 * math.pi * (across + 0.25))
            + math.sin(2 * math.pi * (down - 0.1))) / 2 > WOOD_LINE


def scattered(u, v):
    """One cell in TREE_SPACING, spread about rather than sitting on a grid."""
    scatter = ((u % P_PERIOD + 1) * 2654435761) ^ ((v % Q_PERIOD + 1) * 2246822519)
    return scatter % TREE_SPACING == 0


def draw_cell(u, v):
    """One sloping cell of ground. Returns where a tree grows on it, or None.

    The trees are left to the caller: one stands taller than the cells in front of it,
    which are painted after this one and would bury it.
    """
    cx, cy = u * HALF_W, v * HALF_H
    north, east = height(u, v - 1), height(u + 1, v)
    south, west = height(u, v + 1), height(u - 1, v)

    facet = shape.custom([vec2(cx, cy - HALF_H - north), vec2(cx + HALF_W, cy - east),
                          vec2(cx, cy + HALF_H - south), vec2(cx - HALF_W, cy - west)])

    mean = (north + east + south + west) / 4
    hue = HUES[1] if mean > RELIEF / 2 else HUES[0]

    # A facet tilts away from wherever the ground rises, so the light it takes follows
    # the difference across it
    tilt = (east - west) + 0.5 * (south - north)
    shade = int(len(SHADES) / 2 + tilt / 3.2)
    shade = 0 if shade < 0 else (len(SHADES) - 1 if shade >= len(SHADES) else shade)
    lit = SHADES[shade] * (1.0 if v % 2 else CHECKER)

    terrain.pen = tinted(hue, lit)
    terrain.shape(facet)
    terrain.pen = tinted(hue, lit * SEAM)
    terrain.shape(facet.stroke(1))

    # A tree wants ground near enough to level to stand up straight on
    if (wooded(u, v) and scattered(u, v)
            and abs(east - west) < TREE_GROUND and abs(south - north) < TREE_GROUND):
        return (cx, cy - mean)
    return None


def draw_tree(cx, ground_y):
    """A fir on the ground at (cx, ground_y): shadow, trunk, then two tiers of needles.

    The lit tier is drawn narrower and up to the left over the shaded one, so the tree
    has a side the light comes from.
    """
    terrain.pen = SHADOW
    terrain.shape(shape.ellipse(cx, ground_y + 1, TREE_W, TREE_W // 2))
    terrain.pen = TRUNK
    terrain.shape(shape.rectangle(cx - 1, ground_y - TRUNK_H, 3, TRUNK_H))

    terrain.pen = CANOPY
    terrain.shape(shape.custom([vec2(cx, ground_y - TREE_H),
                                vec2(cx + TREE_W, ground_y - TRUNK_H),
                                vec2(cx - TREE_W, ground_y - TRUNK_H)]))
    terrain.pen = CANOPY_LIT
    terrain.shape(shape.custom([vec2(cx - 2, ground_y - TREE_H + 3),
                                vec2(cx + TREE_W - 4, ground_y - TRUNK_H - 2),
                                vec2(cx - TREE_W + 1, ground_y - TRUNK_H - 2)]))


# Draw the tile once, back to front, so a hill covers the ground standing behind it. The
# loops run past every edge, so anything crossing one is completed by its wrapped
# neighbour and the repeat has no seam to find
print("> Drawing the landscape ...")
trees = []
for v in range(-8, Q_PERIOD + 10):
    for u in range(-3, P_PERIOD + 4):
        if (u + v) % 2 == 0:
            standing = draw_cell(u, v)
            if standing is not None:
                trees.append(standing)

# The trees go on afterwards, in the order their cells were drawn, so each is covered by
# the trees in front of it and by none of the ground
for tree_x, tree_y in trees:
    draw_tree(tree_x, tree_y)

frames = 0
across, down = 0.0, 0.0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The view wanders rather than running in a line: two slow turns of different
        # lengths add up to a heading that keeps bending, and the course follows it at a
        # steady speed. Any offset is valid with tiling on, so the path can be whatever
        # it likes and never needs bringing back inside the tile
        heading = (math.pi * math.sin(2 * math.pi * frames / TURN_WIDE)
                   + 0.7 * math.sin(2 * math.pi * frames / TURN_TIGHT))
        across += SPEED * math.cos(heading)

        # Half as far down as across, which is the ground the isometric view foreshortens
        down += SPEED * math.sin(heading) / 2

        screen.update(terrain, rotation=ROTATION, tile=True,
                      offset=(-int(across), -int(down)))
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
