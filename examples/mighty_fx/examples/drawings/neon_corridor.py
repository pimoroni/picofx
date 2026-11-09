from math import exp, sqrt

"""
Walk without end down a corridor of neon, as rings of light come out of the haze
towards you and a bright light shines at the far end. SCHEME sets its colours to
neon, plaid, emerald, magenta or blueprint, SPEED sets a slow, normal, fast or
ludicrous pace, and OBLONG = True stretches the corridor to the panel's shape.

The drawing calculates the corridor once as it loads, and keeps a word for each pixel in one quarter
with its depth, its nearest line and the far light on it. Each frame then moves the rings along, looks
the quarter's colours up in a palette, and mirrors them into the other three quarters.

Drawing: Neon Corridor
Defaults: Rotation = 90, Pixel double = false
Styles: neon, plaid, emerald, magenta, blueprint
Styles: square, oblong
Styles: normal, slow, fast, ludicrous
Section: Animated scenes
"""

# Constants for drawing
SCHEME = "neon"                     # The colours, a name from SCHEMES, unless the entry's style names one
SCHEME_NAMES = ("neon", "plaid", "emerald", "magenta", "blueprint")    # Every scheme in SCHEMES in order, for the messages naming them
SPEED = "normal"                    # How fast the walk goes, a name from SPEEDS, unless the entry's style names one
SPEEDS = {"slow": 35, "normal": 70, "fast": 120, "ludicrous": 240}      # Depth steps a second at each pace

# The corridor's shape
OBLONG = False                      # Whether the corridor stretches to the panel's shape, unless the entry's style says square
ZOOM = 2                            # Where the panel's shorter edges meet the walls, in half-widths of the corridor down it. More narrows the view
UNIT = 128                          # Depth steps in a half-width of the corridor
RING = const(64)                    # Depth steps between rings, a quarter of the width for square cells. It must be a power of two up to 64, as the depth is kept in 6 bits
LONGEST_STEP = RING * 1000 * 3 // 8     # The furthest a frame moves the walk in thousandths of a depth step. Three eighths of a ring stays clear of the half where the rings seem to run backwards

# The light at the far end, each size a share of a half-width of the corridor
DOT = 0.039                         # How far its hot dot spreads
HALO = 0.219                        # How far its halo spreads
RAY = 0.344                         # How far the rays along the lines reach

# Each scheme is the wall's colour and the haze down the corridor, the glow and colour of the lines
# along it, the glow and colour of the rings, the hot core of every line, and the far end's colour
SCHEMES = {
    "neon": ((0, 12, 28), (0, 30, 60), (0, 70, 140), (0, 220, 255), (110, 0, 90), (255, 60, 200), (230, 250, 255), (0, 0, 0)),
    "plaid": ((8, 6, 34), (24, 10, 50), (190, 60, 0), (255, 150, 30), (110, 0, 10), (235, 40, 25), (255, 240, 200), (0, 0, 0)),
    "emerald": ((0, 14, 8), (0, 34, 20), (60, 120, 0), (170, 255, 40), (0, 80, 50), (0, 210, 120), (230, 255, 220), (0, 0, 0)),
    "magenta": ((0, 12, 28), (0, 30, 60), (110, 0, 90), (255, 60, 200), (0, 70, 140), (0, 220, 255), (255, 225, 250), (0, 0, 0)),
    "blueprint": ((14, 52, 130), (24, 70, 150), (70, 120, 210), (235, 245, 255), (50, 100, 190), (140, 200, 255), (255, 255, 255), (12, 44, 112)),
}

# The entry's style, its choices joined by dashes, such as plaid-oblong-fast. Each is a scheme, a shape or a speed
for choice in style.split("-") if style else ():
    if choice in SCHEMES:
        SCHEME = choice
    elif choice in ("square", "oblong"):
        OBLONG = choice == "oblong"
    elif choice in SPEEDS:
        SPEED = choice
    else:
        raise ValueError(f"'{choice}' is not one of the styles! Use {', '.join(SCHEME_NAMES)}, square or oblong, or slow, normal, fast or ludicrous")

# Is SCHEME one of them?
if SCHEME not in SCHEMES:
    raise ValueError(f"'{SCHEME}' is not one of the schemes! Set SCHEME to {', '.join(SCHEME_NAMES)}")

# Is SPEED one of them?
if SPEED not in SPEEDS:
    raise ValueError(f"'{SPEED}' is not one of the speeds! Set SPEED to slow, normal, fast or ludicrous")

# The palette starts with the lines' colours, 16 levels of fog by 64 strengths each
RING_COLOURS = const(1024)          # Where the rings' colours start, laid out as the lines' are
GLOW = const(2048)                  # Where a line's glow by its distance in quarter pixels starts
LIGHT = const(2112)                 # Where the 16 levels of the far light start
PALETTE_SIZE = 2128

# The canvas is the size of the screen, as the effects file turns it. pixel_double=true halves its width and height
WIDTH, HEIGHT = canvas.width, canvas.height
pixels = canvas.raw

# The corridor is measured in pixels of half the panel's shorter side. When oblong it reaches further
# across the longer side by the panel's shape
HALF = min(WIDTH, HEIGHT) // 2
REACH_X, REACH_Y = (WIDTH / 2 / HALF, HEIGHT / 2 / HALF) if OBLONG else (1, 1)

# The fog is full where the rings bunch to under 1.5 pixels apart, and begins a third of the way there
FOG_FAR = sqrt(HALF * ZOOM * RING / UNIT / 1.5)
FOG_NEAR = FOG_FAR * 1.5 / 4.6

# A line's strength out of 63 by distance in quarter pixels. Its core is a pixel wide with a soft glow either side
LINE_GLOW = [int(63 * min(1, max(0, 1.25 - quarters / 4) + 0.45 * exp(-quarters / 6.4)) + 0.5) for quarters in range(64)]


@micropython.viper
def put(words: ptr32, index: int, word: int):
    """Write a word into a buffer of words."""
    words[index] = word


def mix(a, b, part):
    """Mix two colours, part of the way from the first to the second."""
    return (a[0] + (b[0] - a[0]) * part, a[1] + (b[1] - a[1]) * part, a[2] + (b[2] - a[2]) * part)


def build_palette(palette, scheme):
    """Calculate the palette's colours for a scheme into the palette."""
    wall_rgb, haze, glow_along, line_along, glow_ring, line_ring, core, far = SCHEMES[scheme]
    for block, (glow, line) in enumerate(((glow_along, line_along), (glow_ring, line_ring))):
        for fog in range(16):
            # The wall fades to the far end's colour with the fog, lit by the haze part way down
            near = 1 - fog / 15
            wall = mix(far, wall_rgb, near ** 1.6)
            wall = mix(wall, haze, 2 * near * (1 - near) * near)
            wall = (int(wall[0] + 0.5), int(wall[1] + 0.5), int(wall[2] + 0.5))
            for strength in range(64):
                # From the wall to the glow, the line's colour and its hot core, out of 3780
                progress = 4 * strength * (15 - fog)
                if progress < 1890:
                    low, high, part, span = wall, glow, progress, 1890
                elif progress < 3213:
                    low, high, part, span = glow, line, progress - 1890, 1323
                else:
                    low, high, part, span = line, core, progress - 3213, 567
                red = low[0] + (high[0] - low[0]) * part // span
                green = low[1] + (high[1] - low[1]) * part // span
                blue = low[2] + (high[2] - low[2]) * part // span
                put(palette, block * RING_COLOURS + (fog << 6) + strength, 0xFF000000 | (blue << 16) | (green << 8) | red)

    for quarters, strength in enumerate(LINE_GLOW):
        put(palette, GLOW + quarters, strength)

    # The far light is added over the corridor, the lines' colour where faint and the hot core where strongest
    for level in range(16):
        rgb = mix(line_along, core, level / 15)
        put(palette, LIGHT + level, (int(rgb[2] * level / 15) << 16) | (int(rgb[1] * level / 15) << 8) | int(rgb[0] * level / 15))


def depth_word(distance, stretch):
    """
    Calculate the depth, spread and fog of a pixel on a wall this far from the middle, in pixels of the
    shorter side. stretch= is the panel pixels in each of those, on the axis from the middle to the wall.
    """
    depth = HALF * ZOOM / distance
    spread = min(4095, int(2 * distance * distance * stretch / (HALF * ZOOM) + 0.5))
    fog = max(0, min(15, int(15 * (depth - FOG_NEAR) / (FOG_FAR - FOG_NEAR) + 0.5)))
    return (int(depth * UNIT + 0.5) & (RING - 1)) | (spread << 6) | (fog << 24)


def build_table(table):
    """
    Calculate the word of every pixel in the panel's bottom right quarter into the table, row by row.
    The other three quarters are its mirror images, so they need no words of their own.

    A word holds the pixel's depth down the corridor in its lowest 6 bits, kept within one ring as only
    that is read. Its spread comes next in 12 bits, the 256ths of a pixel a depth step moves across the
    panel there. The top 14 bits hold the glow of its nearest line in 6, its fog in 4 and the far light in 4.
    """
    # The far light's dot and halo by distance in quarter pixels, then its rays. Both are in quarter levels, with 60 as full
    quarters = 4 * HALF                 # A half-width of the corridor, in quarter pixels
    ray_reach = 1.2 * HALF / 120        # How far a ray reaches either side of its line, 1.2 pixels of a 2.8 inch panel
    glare_length = int(2 * sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)) + 1
    glare = [int(60 * (exp(-step / (DOT * quarters)) + 0.55 * exp(-step / (HALO * quarters)))) for step in range(glare_length)]
    rays = [48 * exp(-step / (RAY * quarters)) for step in range(glare_length)]
    corner_length = sqrt(REACH_X * REACH_X + REACH_Y * REACH_Y)
    dither = (0, 2, 3, 1)               # Quarter levels added to round the light up, in a 2x2 pattern

    # On a side wall the pixel's depth, spread and fog depend only on how far across it is, and on
    # the floor or ceiling only on how far down. Each distance is to a pixel's middle
    side_distances = [(across + 0.5) / REACH_X for across in range(WIDTH // 2)]
    side_words = [depth_word(distance, REACH_X) for distance in side_distances]
    floor_words = [depth_word((down + 0.5) / REACH_Y, REACH_Y) for down in range(HEIGHT // 2)]

    for down in range(HEIGHT // 2):
        y = down + 0.5
        floor_distance = y / REACH_Y
        for across in range(WIDTH // 2):
            x = across + 0.5

            # Is the pixel on a side wall, or on the floor or ceiling? Each wall is measured from its middle to its corners
            if side_distances[across] > floor_distance:
                word = side_words[across]
                on_wall, wall_edge = y, REACH_Y * side_distances[across]
            else:
                word = floor_words[down]
                on_wall, wall_edge = x, REACH_X * floor_distance

            # Quarter pixels to the nearest line, along the middle of the wall, half way out or in a corner
            to_line = min(int(4 * min(on_wall, abs(on_wall - wall_edge / 2), wall_edge - on_wall)), 63)
            word |= LINE_GLOW[to_line] << 18

            # The far light's hot dot and halo, and its rays along the middles of the walls and into the corners
            from_middle = int(4 * sqrt(x * x + y * y))
            level = glare[from_middle]
            to_corner = abs(x * REACH_Y - y * REACH_X) / corner_length
            strength = max(0, 1 - min(x, y) / ray_reach) + max(0, 1 - to_corner / ray_reach)
            if strength:
                level += int(rays[from_middle] * strength)
            light = (min(level, 60) + dither[((down & 1) << 1) | (across & 1)]) >> 2
            put(table, down * (WIDTH // 2) + across, word | (light << 28))


@micropython.viper
def draw_corridor(table: ptr32, out: ptr32, palette: ptr32, width: int, height: int, travelled: int):
    """
    Draw the corridor with its rings moved along by the depth steps travelled. Each pixel of the bottom
    right quarter is coloured from its word in the table, then written to its mirror images as well.
    An odd width or height leaves the last column or row unwritten.
    """
    half_width = width >> 1
    half_height = height >> 1
    i = 0
    for down in range(half_height):
        # Where this row of the quarter starts at the panel's middle, and where its mirror image above starts
        below = (half_height + down) * width + half_width
        above = (half_height - 1 - down) * width + half_width
        for across in range(half_width):
            packed = table[i]
            i += 1

            # How far the pixel is from the nearest ring, first in depth steps and then in quarter pixels
            to_ring = (packed + travelled) & (RING - 1)
            if to_ring > RING >> 1:
                to_ring = RING - to_ring
            ring_quarters = (to_ring * ((packed >> 6) & 4095)) >> 6
            if ring_quarters > 63:
                ring_quarters = 63
            ring_glow = palette[GLOW + ring_quarters]

            # The ring and the line add their glows, coloured as whichever is stronger
            line_glow = (packed >> 18) & 63
            strength = line_glow + ring_glow
            if strength > 63:
                strength = 63
            if ring_glow > line_glow:
                strength += RING_COLOURS
            colour = palette[((packed >> 18) & 0x3C0) + strength]        # The fog's 4 bits moved down to bit 6 pick its level's 64 strengths

            light_level = (packed >> 28) & 15
            if light_level:
                light = palette[LIGHT + light_level]
                red = (colour & 0xFF) + (light & 0xFF)
                if red > 255:
                    red = 255
                green = ((colour >> 8) & 0xFF) + ((light >> 8) & 0xFF)
                if green > 255:
                    green = 255
                blue = ((colour >> 16) & 0xFF) + ((light >> 16) & 0xFF)
                if blue > 255:
                    blue = 255
                colour = (colour >> 24 << 24) | (blue << 16) | (green << 8) | red

            out[below + across] = colour
            out[below - 1 - across] = colour
            out[above + across] = colour
            out[above - 1 - across] = colour


# The palette and the words of one quarter's pixels, calculated once
palette = bytearray(PALETTE_SIZE * 4)
build_palette(palette, SCHEME)
table = bytearray((WIDTH // 2) * (HEIGHT // 2) * 4)
build_table(table)

travelled = 0                       # Thousandths of a depth step travelled, wrapping at one ring


def draw():
    """Draw one frame, the walk carried on by the ms since the last."""
    global travelled
    step = min(ticks_delta * SPEEDS[SPEED], LONGEST_STEP)
    travelled = (travelled + step) % (RING * 1000)
    draw_corridor(table, pixels, palette, WIDTH, HEIGHT, travelled // 1000)
