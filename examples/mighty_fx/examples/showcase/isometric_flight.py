import math
import sys
import time

from mighty_fx import MightyFX, SPCE
from picovector import color, image, shape, vec2
from screens import SCREEN_TYPES, Reserve, ScreenPair

"""
Fly for ever over two isometric worlds, each drawn once into a tile the driver repeats.

Both come off one height field, a few sine terms whose cycles all complete across the tile, so
the ground meets itself at every edge and tile=True repeats it without a seam. The hills take
that height as it stands; the terraces snap it to a few levels, which turns every slope into a
fold. Nothing is drawn after startup, and the flight is the offset growing.

One panel carries a world and a second carries the other, so a pair is both at once. An example
that takes the button has to give a way back, so leaving it is a hold.

Press "Boot" to swap the worlds over, and hold it to exit the program.
"""

# Constants
ROTATION = 90               # Quarter turn, to suit how the screens are mounted
TILE_W, TILE_H = 320, 256   # The tile's repeat, a screenful of pixels
CELL_W, CELL_H = 32, 16     # One cell of ground, twice as wide as tall
QUIT_MS = 1500              # Held at least this long, the button ends the example
SPEED = 1.6                 # Pixels of ground a wandering view crosses each frame
TURN_WIDE = 700             # Frames the slow half of a wander takes to come round
TURN_TIGHT = 260            # And the quick half, which bends the course inside the slow one
STEP = 1                    # Pixels a descending view drops each frame, twice that across

# The lattice: a corner sits at (p * CELL_W / 2, q * CELL_H / 2), and a cell's centre at the
# same spacing on the other parity, which interlocks them. Both counts are the tile's own
# repeat, so a corner looked up past the edge is the one that wraps to it
P_PERIOD = TILE_W // (CELL_W // 2)
Q_PERIOD = TILE_H // (CELL_H // 2)
HALF_W, HALF_H = CELL_W // 2, CELL_H // 2


def field(p, q):
    """The height at lattice corner (p, q), 0 for the lowest ground and 1 for the highest.

    Every term completes a whole number of cycles across the tile, on both axes, so the field
    meets itself exactly at the edges and either world tiles without a crack.
    """
    across, down = p / P_PERIOD, q / Q_PERIOD
    total = (0.5 * math.sin(2 * math.pi * across)
             + 0.5 * math.sin(2 * math.pi * down)
             + 0.3 * math.sin(2 * math.pi * (across + down))
             + 0.3 * math.sin(2 * math.pi * (2 * across - down))
             + 0.2 * math.sin(2 * math.pi * (across - 2 * down)))
    return (total / 1.8 + 1) / 2


# One figure per corner, worked out once and shared by both worlds and by the four cells that
# meet there, so no two cells can disagree about where their common corner sits
FIELD = [[field(p, q) for q in range(Q_PERIOD)] for p in range(P_PERIOD)]


def raw(u, v):
    """The field at a lattice corner, wrapped to the tile."""
    return FIELD[u % P_PERIOD][v % Q_PERIOD]


def tinted(rgb, factor):
    """One colour at a fraction of its brightness."""
    return color.rgb(min(255, int(rgb[0] * factor)), min(255, int(rgb[1] * factor)),
                     min(255, int(rgb[2] * factor)))


def scattered(u, v, spacing):
    """One cell in spacing, spread about and not sitting on a grid."""
    scatter = ((u % P_PERIOD + 1) * 2654435761) ^ ((v % Q_PERIOD + 1) * 2246822519)
    return scatter % spacing == 0


def growing(u, v, line):
    """Whether this part of the map carries props, on its own broad scale.

    They gather into groups instead of standing one to a field, so where they grow is a slow
    field of its own and which cell holds one is the scatter above.
    """
    across, down = u / P_PERIOD, v / Q_PERIOD
    return (math.sin(2 * math.pi * (across + 0.25))
            + math.sin(2 * math.pi * (down - 0.1))) / 2 > line


def facet_of(cx, cy, north, east, south, west):
    """The four-cornered quad a cell of ground is drawn as, at the corner heights given."""
    return shape.custom([vec2(cx, cy - HALF_H - north), vec2(cx + HALF_W, cy - east),
                         vec2(cx, cy + HALF_H - south), vec2(cx - HALF_W, cy - west)])


def lit_by(tilt, shades, spread):
    """Which of a world's shades a facet takes, from how far the ground tilts across it.

    A facet tilts away from wherever the ground rises, so the light it takes follows the
    difference across it.
    """
    shade = int(len(shades) / 2 + tilt / spread)
    return shades[0 if shade < 0 else (len(shades) - 1 if shade >= len(shades) else shade)]


def hill_cell(land, tile, u, v):
    """One sloping cell of grass. Returns where a tree grows on it, or None.

    Props are left to the caller: one stands taller than the cells in front of it, which are
    painted after this one and would bury it.
    """
    cx, cy = u * HALF_W, v * HALF_H
    relief = land["relief"]
    north, east = raw(u, v - 1) * relief, raw(u + 1, v) * relief
    south, west = raw(u, v + 1) * relief, raw(u - 1, v) * relief

    facet = facet_of(cx, cy, north, east, south, west)
    mean = (north + east + south + west) / 4
    hue = land["hues"][1] if mean > relief / 2 else land["hues"][0]

    # Every other cell is drawn darker, so the field reads as a checkerboard the way the
    # era's did
    tilt = (east - west) + 0.5 * (south - north)
    lit = lit_by(tilt, land["shades"], 3.2) * (1.0 if v % 2 else land["checker"])

    tile.pen = tinted(hue, lit)
    tile.shape(facet)
    tile.pen = tinted(hue, lit * land["seam"])
    tile.shape(facet.stroke(1))

    # A tree wants ground near enough to level to stand up straight on
    if (growing(u, v, land["line"]) and scattered(u, v, land["spacing"])
            and abs(east - west) < land["footing"] and abs(south - north) < land["footing"]):
        return (cx, cy - mean)
    return None


def terrace_cell(land, tile, u, v):
    """One flat or folded cell of terrace. Returns where a spire stands on it, or None.

    The snap to a level is what turns the field's slopes into steps: four corners on one
    level come out flat, and corners straddling two come out as a hard fold between them.
    """
    cx, cy = u * HALF_W, v * HALF_H
    levels, relief = land["levels"], land["relief"]
    lift = relief / (levels - 1)

    def level(du, dv):
        return min(levels - 1, int(raw(u + du, v + dv) * levels))

    north, east, south, west = level(0, -1), level(1, 0), level(0, 1), level(-1, 0)
    facet = facet_of(cx, cy, north * lift, east * lift, south * lift, west * lift)
    band = (north + east + south + west) // 4

    tilt = (east - west) + 0.5 * (south - north)
    tile.pen = tinted(land["grounds"][band], lit_by(tilt, land["shades"], 1.0))
    tile.shape(facet)
    tile.pen = color.rgb(*land["seams"][band])
    tile.shape(facet.stroke(1))

    # A spire wants a cell that came out flat, all four of its corners on one level
    if (growing(u, v, land["line"]) and scattered(u, v, land["spacing"])
            and max(north, east, south, west) - min(north, east, south, west) < land["footing"]):
        return (cx, cy - band * lift)
    return None


def draw_tree(land, tile, cx, ground_y):
    """A fir on the ground: shadow, trunk, then two tiers of needles.

    The lit tier is drawn narrower and up to the left over the shaded one, so the tree has a
    side the light comes from.
    """
    tall, wide, trunk = land["prop_h"], land["prop_w"], land["trunk_h"]
    tile.pen = land["foot"]
    tile.shape(shape.ellipse(cx, ground_y + 1, wide, wide // 2))
    tile.pen = land["trunk"]
    tile.shape(shape.rectangle(cx - 1, ground_y - trunk, 3, trunk))

    tile.pen = land["body"]
    tile.shape(shape.custom([vec2(cx, ground_y - tall), vec2(cx + wide, ground_y - trunk),
                             vec2(cx - wide, ground_y - trunk)]))
    tile.pen = land["body_lit"]
    tile.shape(shape.custom([vec2(cx - 2, ground_y - tall + 3),
                             vec2(cx + wide - 4, ground_y - trunk - 2),
                             vec2(cx - wide + 1, ground_y - trunk - 2)]))


def draw_spire(land, tile, cx, ground_y):
    """A lit spire on the ground, standing on a dark foot."""
    tall, wide = land["prop_h"], land["prop_w"]
    tile.pen = land["foot"]
    tile.shape(shape.ellipse(cx, ground_y + 1, wide, wide // 2))
    tile.pen = land["body"]
    tile.shape(shape.custom([vec2(cx, ground_y - tall), vec2(cx + wide, ground_y),
                             vec2(cx - wide, ground_y)]))
    tile.pen = land["body_lit"]
    tile.shape(shape.custom([vec2(cx - 1, ground_y - tall + 2),
                             vec2(cx + wide - 4, ground_y - 2),
                             vec2(cx - wide + 2, ground_y - 2)]))


# The two worlds. Each carries its relief and palette, the cell and prop it is painted with,
# and how the view crosses it: "wander" keeps bending its heading, "descend" holds a line.
#
# Antialiasing is a world's own choice, and it is affordable either way since both tiles are drawn
# before the loop. Smooth ground gains from it; the terraces lose, their seams being one pixel of
# bright over dark ground, which softening spreads and dims
HILLS = {"name": "rolling hills", "cell": hill_cell, "prop": draw_tree, "motion": "wander",
         "antialias": image.X4,
         "relief": 44, "hues": ((36, 172, 108), (196, 216, 96)), "checker": 0.74, "seam": 0.55,
         "shades": (0.62, 0.74, 0.86, 0.96, 1.04, 1.12, 1.2),
         "line": 0.15, "spacing": 3, "footing": 5,
         "prop_h": 21, "prop_w": 8, "trunk_h": 5,
         "body": color.rgb(16, 92, 52), "body_lit": color.rgb(52, 148, 76),
         "trunk": color.rgb(84, 52, 28), "foot": color.rgb(20, 108, 72)}

TERRACES = {"name": "neon terraces", "cell": terrace_cell, "prop": draw_spire,
            "motion": "descend", "antialias": image.OFF, "relief": 48, "levels": 5,
            "grounds": ((20, 10, 44), (30, 12, 60), (40, 14, 78), (52, 16, 96), (64, 20, 116)),
            "seams": ((0, 236, 208), (0, 200, 248), (110, 130, 255), (208, 84, 255),
                      (255, 64, 190)),
            "shades": (0.7, 0.85, 1.0, 1.2, 1.45),
            "line": 0.25, "spacing": 3, "footing": 1,
            "prop_h": 24, "prop_w": 7,
            "body": color.rgb(126, 16, 150), "body_lit": color.rgb(255, 96, 226),
            "foot": color.rgb(38, 8, 60)}

WORLDS = (HILLS, TERRACES)


def build(land):
    """Draw one world's whole tile, back to front, and return it.

    The loops run past every edge, so ground crossing one is completed by its wrapped
    neighbour and the repeat has no seam to find. Props go on afterwards, in the order their
    cells were drawn, so each is covered by the props in front of it and by none of the ground.
    """
    print(f"> Drawing the {land['name']} ...")
    tile = image(TILE_W, TILE_H)
    tile.antialias = land["antialias"]
    standing = []
    for v in range(-8, Q_PERIOD + 10):
        for u in range(-3, P_PERIOD + 4):
            if (u + v) % 2 == 0:
                where = land["cell"](land, tile, u, v)
                if where is not None:
                    standing.append(where)

    for cx, ground_y in standing:
        land["prop"](land, tile, cx, ground_y)
    return tile


def flown(land, place):
    """Move a world's view on by one frame, and answer the offset to read its tile at.

    Any offset is valid with tiling on, so a course never has to be brought back inside the
    tile and can be whatever suits the world.
    """
    place["frames"] += 1
    if land["motion"] == "descend":
        # Two across for one down keeps the flight along the lattice's own slope
        place["across"] = place["frames"] * STEP * 2
        place["down"] = place["frames"] * STEP
    else:
        # Two slow turns of different lengths add up to a heading that keeps bending, and the
        # course follows it at a steady speed, half as far down as across for the shortening
        heading = (math.pi * math.sin(2 * math.pi * place["frames"] / TURN_WIDE)
                   + 0.7 * math.sin(2 * math.pi * place["frames"] / TURN_TIGHT))
        place["across"] += SPEED * math.cos(heading)
        place["down"] += SPEED * math.sin(heading) / 2

    return -int(place["across"]), -int(place["down"])


# Which screen is on the ports, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with both SP/CE ports set up for screens
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A screen refuses to be created where no panel answered on its port, so one panel flies a
# world on its own and a second brings the other alongside. The reserve is what a pair needs
# to convert two sources on one frame; a lone screen simply does not draw on it
screens = []
for port in (mighty.spce_a, mighty.spce_b):
    try:
        screens.append(ScreenType(port, reserve=Reserve.FULL_SIZE_IMAGES))
    except ValueError as e:
        print(e)

if not screens:
    mighty.shutdown()
    raise RuntimeError("No panels answered! Plug a screen into SP/CE A, and a second into"
                       " SP/CE B to fly both worlds at once")

# Two panels are two worlds shown together, so they are held to one refresh rate and written
# on the same frame. Working out how takes a few seconds when the pair is created
pair = ScreenPair(*screens) if len(screens) == 2 else None

tiles = [build(land) for land in WORLDS]
places = [{"across": 0.0, "down": 0.0, "frames": 0} for _ in WORLDS]

# Which world is on the first panel. The other follows it, so one number says where both are
leading = 0
print(f"{len(screens)} panel(s): press for the next world, hold {QUIT_MS}ms to finish")

pressed_since = None
leaving = False

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not leaving:
        if pair is not None:
            first, second = leading, (leading + 1) % len(WORLDS)
            pair.update(tiles[first], tiles[second], rotation=ROTATION, tile=True,
                        offset=(flown(WORLDS[first], places[first]),
                                flown(WORLDS[second], places[second])))
        else:
            screens[0].update(tiles[leading], rotation=ROTATION, tile=True,
                              offset=flown(WORLDS[leading], places[leading]))

        # Judged on release, a press being impossible to tell from a hold until it ends
        if mighty.boot_pressed():
            if pressed_since is None:
                pressed_since = time.ticks_ms()

        elif pressed_since is not None:
            held = time.ticks_diff(time.ticks_ms(), pressed_since)
            pressed_since = None
            if held >= QUIT_MS:
                leaving = True
            else:
                leading = (leading + 1) % len(WORLDS)
                print(f"> {WORLDS[leading]['name']} leading")

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
