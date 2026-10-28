import math
from picovector import color, image, rect, shape, vec2

"""
Drawing: Isometric flight
Fly for ever over two isometric worlds, each drawn once into a tile, taking turns on a timer.
Section: Animation
"""

# Entry: screenA rotation=90: graphics file=isometric_flight.py

# Constants
TILE_W, TILE_H = 320, 256   # The tile's repeat, a screenful of pixels
CELL_W, CELL_H = 32, 16     # One cell of ground, twice as wide as tall
SPEED = 1.6                 # Pixels of ground a wandering view crosses each frame
TURN_WIDE = 700             # Frames the slow half of a wander takes to come round
TURN_TIGHT = 260            # And the quick half, which bends the course inside the slow one
STEP = 1                    # Pixels a descending view drops each frame, twice that across
SWAP_MS = 20000             # How long a world flies before the other takes over, as a drawing has no button

P_PERIOD = TILE_W // (CELL_W // 2)
Q_PERIOD = TILE_H // (CELL_H // 2)
HALF_W, HALF_H = CELL_W // 2, CELL_H // 2


def field(p, q):
    """The height at lattice corner (p, q), 0 for the lowest ground and 1 for the highest."""
    across, down = p / P_PERIOD, q / Q_PERIOD
    total = (0.5 * math.sin(2 * math.pi * across)
             + 0.5 * math.sin(2 * math.pi * down)
             + 0.3 * math.sin(2 * math.pi * (across + down))
             + 0.3 * math.sin(2 * math.pi * (2 * across - down))
             + 0.2 * math.sin(2 * math.pi * (across - 2 * down)))
    return (total / 1.8 + 1) / 2


FIELD = [[field(p, q) for q in range(Q_PERIOD)] for p in range(P_PERIOD)]


def raw(u, v):
    """The field at a lattice corner, wrapped to the tile."""
    return FIELD[u % P_PERIOD][v % Q_PERIOD]


def tinted(rgb, factor):
    """One colour at a fraction of its brightness."""
    return color.rgb(min(255, int(rgb[0] * factor)), min(255, int(rgb[1] * factor)),
                     min(255, int(rgb[2] * factor)))


def scattered(u, v, spacing):
    """Whether this cell is one in spacing, spread about and not sitting on a grid."""
    scatter = ((u % P_PERIOD + 1) * 2654435761) ^ ((v % Q_PERIOD + 1) * 2246822519)
    return scatter % spacing == 0


def growing(u, v, line):
    """Whether this part of the map carries props."""
    across, down = u / P_PERIOD, v / Q_PERIOD
    return (math.sin(2 * math.pi * (across + 0.25))
            + math.sin(2 * math.pi * (down - 0.1))) / 2 > line


def facet_of(cx, cy, north, east, south, west):
    """The four-cornered quad a cell of ground is drawn as, at the corner heights given."""
    return shape.custom([vec2(cx, cy - HALF_H - north), vec2(cx + HALF_W, cy - east),
                         vec2(cx, cy + HALF_H - south), vec2(cx - HALF_W, cy - west)])


def lit_by(tilt, shades, spread):
    """Which of a world's shades a facet takes, from how far the ground tilts across it."""
    shade = int(len(shades) / 2 + tilt / spread)
    return shades[0 if shade < 0 else (len(shades) - 1 if shade >= len(shades) else shade)]


def hill_cell(land, tile, u, v):
    """Draw one sloping cell of grass, and return where a tree grows on it or None."""
    cx, cy = u * HALF_W, v * HALF_H
    relief = land["relief"]
    north, east = raw(u, v - 1) * relief, raw(u + 1, v) * relief
    south, west = raw(u, v + 1) * relief, raw(u - 1, v) * relief

    facet = facet_of(cx, cy, north, east, south, west)
    mean = (north + east + south + west) / 4
    hue = land["hues"][1] if mean > relief / 2 else land["hues"][0]

    tilt = (east - west) + 0.5 * (south - north)
    lit = lit_by(tilt, land["shades"], 3.2) * (1.0 if v % 2 else land["checker"])

    tile.pen = tinted(hue, lit)
    tile.shape(facet)
    tile.pen = tinted(hue, lit * land["seam"])
    tile.shape(facet.stroke(1))

    if (growing(u, v, land["line"]) and scattered(u, v, land["spacing"])
            and abs(east - west) < land["footing"] and abs(south - north) < land["footing"]):
        return (cx, cy - mean)
    return None


def terrace_cell(land, tile, u, v):
    """Draw one flat or folded cell of terrace, and return where a spire stands on it or None."""
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

    if (growing(u, v, land["line"]) and scattered(u, v, land["spacing"])
            and max(north, east, south, west) - min(north, east, south, west) < land["footing"]):
        return (cx, cy - band * lift)
    return None


def draw_tree(land, tile, cx, ground_y):
    """Draw a fir, shadow, trunk, then two tiers of needles."""
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
    """Draw a lit spire on the ground, standing on a dark foot."""
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
    """Draw one world's tile back to front, then its props in the same order."""
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
    """Move a world's view on a frame, and return where in its tile the panel's corner reads from."""
    place["frames"] += 1
    if land["motion"] == "descend":
        place["across"] = place["frames"] * STEP * 2
        place["down"] = place["frames"] * STEP
    else:
        heading = (math.pi * math.sin(2 * math.pi * place["frames"] / TURN_WIDE)
                   + 0.7 * math.sin(2 * math.pi * place["frames"] / TURN_TIGHT))
        place["across"] += SPEED * math.cos(heading)
        place["down"] += SPEED * math.sin(heading) / 2

    return int(place["across"]) % TILE_W, int(place["down"]) % TILE_H


tiles = [build(land) for land in WORLDS]
places = [{"across": 0.0, "down": 0.0, "frames": 0} for _ in WORLDS]

# Moved and never made, so a frame allocates nothing
source = rect(0, 0, 0, 0)
target = rect(0, 0, 0, 0)


def tiled(canvas, tile, from_x, from_y):
    """
    Fill the canvas from the tile read from (from_x, from_y), wrapping at its edges.

    The entry's offset is fixed, so the tiling the driver would do is up to four blits here.
    """
    y, read_y = 0, from_y
    while y < canvas.height:
        tall = min(TILE_H - read_y, canvas.height - y)
        x, read_x = 0, from_x
        while x < canvas.width:
            wide = min(TILE_W - read_x, canvas.width - x)
            source.x, source.y, source.w, source.h = read_x, read_y, wide, tall
            target.x, target.y, target.w, target.h = x, y, wide, tall
            canvas.blit(tile, source, target)
            x += wide
            read_x = 0
        y += tall
        read_y = 0


def draw(canvas, elapsed):
    leading = int(elapsed * 1000 // SWAP_MS) % len(WORLDS)
    tiled(canvas, tiles[leading], *flown(WORLDS[leading], places[leading]))
