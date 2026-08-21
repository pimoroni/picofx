import math
import sys

from mighty_fx import MightyFX, SPCE
from picovector import color, image, shape, vec2
from screens import SCREEN_TYPES, Tile

"""
Fly for ever over a neon isometric landscape that is drawn once, into a single tile.
tile=True has the driver repeat that tile in both directions, so every frame after startup
costs nothing but a larger offset: no drawing, and nothing to reset when the view passes
the tile's edge.

Where isometric_slopes.py lets the ground take any height it likes, this one snaps every
corner of the lattice to one of a few levels. A cell whose four corners land on the same
level comes out flat, and one whose corners straddle two levels comes out as a hard fold
between them, so the landscape reads as terraces cut into steps rather than as hills. It
is the same height field underneath, and the only difference is the snap.

Across the panel the tile is mirrored rather than repeated, tile taking a value per axis and
Tile.MIRROR reversing every other copy. Each sideways seam is therefore a reflection, which
costs nothing and buys two things: the terraces meet themselves exactly, so there is no join
to spot, and the pattern only comes back round after two tiles instead of one, which puts
the sideways repeat outside anything the panel can show at once. Down the panel it repeats
plainly, so both forms of the setting sit in one call.

What a reflection costs instead is a symmetry, and once a viewer has seen it they see it
every time: the spires shade the other way in a mirrored copy, since the whole picture is
handed back to front. MIRROR_ACROSS turns it off, which trades that for a plain join.

Every seam glows in a colour taken from the height it sits at, over facets kept dark, which
is what makes the grid the thing you see rather than the ground.

Press "Boot" to exit the program.
"""

# Constants
ROTATION = 90               # Quarter turn, to suit how the screen is mounted
TILE_W, TILE_H = 320, 256   # The tile, one screenful, mirrored across so it never repeats
CELL_W, CELL_H = 32, 16     # One cell of ground, twice as wide as tall
RELIEF = 48                 # Pixels between the lowest ground and the highest
LEVELS = 5                  # Heights the ground is allowed to sit at
STEP = 1                    # Pixels the view descends each frame, twice that across
SPIRE_H = 24                # How tall a spire stands above its ground
SPIRE_W = 7                 # Half the width of a spire at its base
SPIRE_SPACING = 3           # One cell in this many carries a spire, inside a cluster
CLUSTER_LINE = 0.25         # How much of the map grows spires, -1 for none and 1 for all
SPIRE_GROUND = 1            # How level a cell must be to carry one, in pixels
MIRROR_ACROSS = True        # Whether the tile is mirrored sideways or plainly repeated

# Dark ground, one shade per level, against a seam that glows brighter as it climbs. The
# facets stay dim so the seams carry the picture
GROUNDS = ((20, 10, 44), (30, 12, 60), (40, 14, 78), (52, 16, 96), (64, 20, 116))
SEAMS = ((0, 236, 208), (0, 200, 248), (110, 130, 255), (208, 84, 255), (255, 64, 190))
SHADES = (0.7, 0.85, 1.0, 1.2, 1.45)   # Light a facet takes, by which way it tilts
SPIRE = color.rgb(126, 16, 150)
SPIRE_LIT = color.rgb(255, 96, 226)
SPIRE_FOOT = color.rgb(38, 8, 60)

# The lattice: a corner sits at (p * CELL_W / 2, q * CELL_H / 2), and a cell's centre at
# the same spacing on the other parity, which interlocks them. Both counts are
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
    """One of the palette colours at a fraction of its brightness."""
    return color.rgb(min(255, int(rgb[0] * factor)), min(255, int(rgb[1] * factor)),
                     min(255, int(rgb[2] * factor)))


def corner_level(p, q):
    """Which level the ground sits at, at lattice corner (p, q).

    Every term completes a whole number of cycles across the tile, on both axes, so
    the field meets itself exactly at the edges; the snap to a level is what turns its
    slopes into steps.
    """
    across, down = p / P_PERIOD, q / Q_PERIOD
    total = (0.5 * math.sin(2 * math.pi * across)
             + 0.5 * math.sin(2 * math.pi * down)
             + 0.3 * math.sin(2 * math.pi * (across + down))
             + 0.3 * math.sin(2 * math.pi * (2 * across - down))
             + 0.2 * math.sin(2 * math.pi * (across - 2 * down)))
    level = int((total / 1.8 + 1) / 2 * LEVELS)
    return 0 if level < 0 else (LEVELS - 1 if level > LEVELS - 1 else level)


# One level per corner, so a corner shared by four cells is worked out once and they all
# agree on it, which leaves the terraces without a crack
CORNERS = [[corner_level(p, q) for q in range(Q_PERIOD)] for p in range(P_PERIOD)]


def level_at(p, q):
    return CORNERS[p % P_PERIOD][q % Q_PERIOD]


def clustered(u, v):
    """Whether this part of the map grows spires, on its own broad scale."""
    across, down = u / P_PERIOD, v / Q_PERIOD
    return (math.sin(2 * math.pi * (across + 0.25))
            + math.sin(2 * math.pi * (down - 0.1))) / 2 > CLUSTER_LINE


def scattered(u, v):
    """One cell in SPIRE_SPACING, spread about rather than sitting on a grid."""
    scatter = ((u % P_PERIOD + 1) * 2654435761) ^ ((v % Q_PERIOD + 1) * 2246822519)
    return scatter % SPIRE_SPACING == 0


def draw_cell(u, v):
    """One terrace cell. Returns where a spire stands on it, or None.

    The spires are left to the caller: one stands taller than the cells in front of it,
    which are painted after this one and would bury it.
    """
    cx, cy = u * HALF_W, v * HALF_H
    lift = RELIEF / (LEVELS - 1)
    north, east = level_at(u, v - 1), level_at(u + 1, v)
    south, west = level_at(u, v + 1), level_at(u - 1, v)

    facet = shape.custom([vec2(cx, cy - HALF_H - north * lift),
                          vec2(cx + HALF_W, cy - east * lift),
                          vec2(cx, cy + HALF_H - south * lift),
                          vec2(cx - HALF_W, cy - west * lift)])

    band = (north + east + south + west) // 4

    # A facet tilts away from wherever the ground rises, so the light it takes follows
    # the difference across it
    tilt = (east - west) + 0.5 * (south - north)
    shade = int(len(SHADES) / 2 + tilt)
    shade = 0 if shade < 0 else (len(SHADES) - 1 if shade >= len(SHADES) else shade)

    terrain.pen = tinted(GROUNDS[band], SHADES[shade])
    terrain.shape(facet)
    terrain.pen = color.rgb(*SEAMS[band])
    terrain.shape(facet.stroke(1))

    # A spire wants a cell that came out flat, all four of its corners on one level
    if (clustered(u, v) and scattered(u, v)
            and max(north, east, south, west) - min(north, east, south, west) < SPIRE_GROUND):
        return (cx, cy - band * lift)
    return None


def draw_spire(cx, ground_y):
    """A lit spire on the ground at (cx, ground_y), on a dark foot."""
    terrain.pen = SPIRE_FOOT
    terrain.shape(shape.ellipse(cx, ground_y + 1, SPIRE_W, SPIRE_W // 2))
    terrain.pen = SPIRE
    terrain.shape(shape.custom([vec2(cx, ground_y - SPIRE_H),
                                vec2(cx + SPIRE_W, ground_y),
                                vec2(cx - SPIRE_W, ground_y)]))
    terrain.pen = SPIRE_LIT
    terrain.shape(shape.custom([vec2(cx - 1, ground_y - SPIRE_H + 2),
                                vec2(cx + SPIRE_W - 4, ground_y - 2),
                                vec2(cx - SPIRE_W + 2, ground_y - 2)]))


# Draw the tile once, back to front, so a terrace covers the ground standing behind it.
# The loops run past every edge, so anything crossing one is completed by its wrapped
# neighbour and the repeat has no seam to find
print("> Drawing the grid ...")
spires = []
for v in range(-8, Q_PERIOD + 10):
    for u in range(-3, P_PERIOD + 4):
        if (u + v) % 2 == 0:
            standing = draw_cell(u, v)
            if standing is not None:
                spires.append(standing)

# The spires go on afterwards, in the order their cells were drawn, so each is covered by
# the spires in front of it and by none of the ground
for spire_x, spire_y in spires:
    draw_spire(spire_x, spire_y)

# Mirroring costs nothing and hides the sideways join, at the price of a symmetry a
# viewer can learn to see, the spires shading the other way in a reflected copy
ACROSS = Tile.MIRROR if MIRROR_ACROSS else True

frames = 0

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        down = frames * STEP

        # Two across for one down keeps the flight along the lattice's own slope, and
        # sideways the tile is mirrored rather than repeated
        screen.update(terrain, rotation=ROTATION, tile=(ACROSS, True),
                      offset=(-down * 2, -down))
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
