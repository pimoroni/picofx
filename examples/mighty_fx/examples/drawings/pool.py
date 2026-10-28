import random
from picovector import color, image, rect

"""
Drawing: Pool
The floor of a small pool seen through rippling water, in modern or Roman tiles, with light gathering in lines.
Section: Animation
"""

# Entry: screenA rotation=90 pixel_double=true: graphics file=pool.py fps=9   (a 2.8" screen)

# Constants for drawing
STYLE = "modern"                                    # The floor, "modern" blue mosaic or "roman" cream stones round an octagon
STEPS = 2                                           # Ripple steps a frame, more for faster ripples
DROPS = 2                                           # Drops falling on the water each step
DROP_DEPTH = 30                                     # How deep a drop dents the water, its middle seventeen times this
SPLASH_DEPTH = DROP_DEPTH * 4
SPLASH_CHANCE = 0.04                                # The chance each step of a splash
CALMING = 7                                         # How slowly ripples die away, as a shift, more for longer lasting ripples
BENDING = 9                                         # How little the water's slope moves the floor, as a shift, more for less wobble
LIGHT = 4                                           # How little the water's curve brightens the floor, as a shift, more for fainter light
LIGHT_THRESHOLD = 4                                 # How far the curve must pass, after the LIGHT shift, before any light shows

# Sizes, in canvas pixels, each shown as two panel pixels by two
STONE = 6                                           # Across a tile or stone, its grout included
BORDER = 8                                          # Floor drawn beyond each edge of the panel, the furthest the bent light reaches being one less

# The floor's colours, a modern pool's blues in pale grout, and a Roman bath's cream, blue and terracotta
POOL_BLUES = ((102, 204, 238), (85, 187, 238), (68, 170, 238), (51, 153, 221), (34, 136, 221), (119, 221, 255), (68, 187, 221))
POOL_GROUT = (170, 221, 238)
CREAM = ((204, 204, 170), (213, 209, 179), (209, 200, 166), (217, 213, 183))
BLUE = ((34, 68, 102), (51, 85, 119), (34, 51, 85))
TERRACOTTA = ((170, 85, 51), (187, 102, 68), (153, 68, 51))
BATH_GROUT = (170, 170, 136)
BATH_WATER = (0.75, 0.875, 0.86)                    # How much of each channel a bath's green water lets through

# The canvas this drawing expects, a 2.8" screen at rotation=90 with pixel_double=true. The module
# body cannot see the canvas, and the water is sized from it, so it is stated and checked on the first call
WIDTH, HEIGHT = 160, 120

# The floor, with a border round the panel's view of it. A drawing cannot import screens to claim SRAM,
# so it is on the heap
FLOOR_W, FLOOR_H = WIDTH + 2 * BORDER, HEIGHT + 2 * BORDER
floor = image(FLOOR_W, FLOOR_H)

# The stones are laid from just off the floor's top left corner so that one sits in the middle of the panel,
# and enough of them to cover the floor
FIRST_X = (FLOOR_W // 2 - STONE // 2) % STONE - STONE
FIRST_Y = (FLOOR_H // 2 - STONE // 2) % STONE - STONE
COLUMNS, ROWS = FLOOR_W // STONE + 2, FLOOR_H // STONE + 2
MIDDLE_COLUMN = (FLOOR_W // 2 - STONE // 2 - FIRST_X) // STONE
MIDDLE_ROW = (FLOOR_H // 2 - STONE // 2 - FIRST_Y) // STONE
EDGE = 6                                            # How far from the panel's edge a drop falls, its dent reaching four cells

# The water's heights now and a step before, a word a cell, on the heap as the floor is
CELLS = WIDTH * HEIGHT
water = [bytearray(CELLS * 4), bytearray(CELLS * 4)]


def build_floor():
    """Draw the floor once, a stone at a time, in the chosen STYLE."""
    if STYLE == "roman":
        floor.pen = color.rgb(*BATH_GROUT)
        floor.clear()
        for row in range(ROWS):
            for column in range(COLUMNS):
                across, down = abs(column - MIDDLE_COLUMN), abs(row - MIDDLE_ROW)
                # How many stones out from the middle, in an octagon with its corners cut at 45 degrees
                ring = round(max(across, down, (across + down) * 0.7071))
                palette = BLUE if ring in (0, 1, 5) else TERRACOTTA if ring == 3 else CREAM
                base = random.choice(palette)
                floor.pen = color.rgb(*(round(channel * part) for channel, part in zip(base, BATH_WATER)))
                floor.rectangle(rect(FIRST_X + column * STONE, FIRST_Y + row * STONE, STONE - 1, STONE - 1))
    else:
        floor.pen = color.rgb(*POOL_GROUT)
        floor.clear()
        for row in range(ROWS):
            for column in range(COLUMNS):
                floor.pen = color.rgb(*random.choice(POOL_BLUES))
                floor.rectangle(rect(FIRST_X + column * STONE, FIRST_Y + row * STONE, STONE - 1, STONE - 1))


@micropython.viper
def ripple(now: ptr32, before: ptr32, width: int, rows: int, calming: int):
    """
    Step the water on, writing each cell's next height over its height a step before.

    The cells round the edge stay level, so the ripples reflect from them as from a pool's walls.
    """
    for y in range(1, rows - 1):
        row = y * width
        for x in range(1, width - 1):
            cell = row + x
            next_height = ((now[cell - 1] + now[cell + 1] + now[cell - width] + now[cell + width]) >> 1) - before[cell]
            before[cell] = next_height - (next_height >> calming)


@micropython.viper
def drop(now: ptr32, width: int, x: int, y: int, depth: int):
    """Dent the water round a cell, deepest in the middle and rounded off four cells out."""
    for down in range(-4, 5):
        for across in range(-4, 5):
            weight = 17 - down * down - across * across
            if weight > 0:
                now[(y + down) * width + x + across] -= depth * weight


@micropython.viper
def draw_water(heights: ptr32, out: ptr32, floor_pixels: ptr32, width: int, rows: int, floor_w: int, border: int,
               bending: int, light: int, threshold: int):
    """
    Draw the floor through the water, each pixel taken from a little to one side by the water's slope
    there, and brightened where the water curves to gather the light.

    The slope and curve are read two cells apart, which smooths them. Each pixel is read and written as
    one word, the light added a channel at a time only where it shows.
    """
    limit = border - 1                                  # The furthest a pixel is taken from, kept inside the floor's border
    for y in range(2, rows - 2):
        row = y * width
        for x in range(2, width - 2):
            cell = row + x
            left = heights[cell - 2]
            right = heights[cell + 2]
            up = heights[cell - 2 * width]
            down = heights[cell + 2 * width]
            shift_x = (left - right) >> bending
            shift_y = (up - down) >> bending
            if shift_x > limit:
                shift_x = limit
            elif shift_x < -limit:
                shift_x = -limit
            if shift_y > limit:
                shift_y = limit
            elif shift_y < -limit:
                shift_y = -limit
            colour = floor_pixels[(y + border + shift_y) * floor_w + x + border + shift_x]
            glint = ((left + right + up + down - 4 * heights[cell]) >> light) - threshold
            if glint > 0:
                # Doubled past the threshold, so the light that shows is bright
                glint = glint << 1
                if glint > 255:
                    glint = 255
                red = (colour & 0xFF) + glint
                green = (colour >> 8 & 0xFF) + glint
                blue = (colour >> 16 & 0xFF) + glint
                if red > 255:
                    red = 255
                if green > 255:
                    green = 255
                if blue > 255:
                    blue = 255
                colour = (colour >> 24 << 24) | blue << 16 | green << 8 | red
            out[cell] = colour


@micropython.viper
def show_floor(out: ptr32, floor_pixels: ptr32, width: int, rows: int, floor_w: int, border: int):
    """Copy the floor as it lies under still water, filling the edge the water drawing leaves alone."""
    for y in range(rows):
        for x in range(width):
            out[y * width + x] = floor_pixels[(y + border) * floor_w + x + border]


# The floor is drawn once
build_floor()
floor_pixels = floor.raw
shown = False


def draw(canvas, _elapsed):
    global shown
    if not shown:
        if (canvas.width, canvas.height) != (WIDTH, HEIGHT):
            raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                             f"rotation=90 with pixel_double=true, and was given {canvas.width}x{canvas.height}")
        # The panel's edge shown as under still water
        show_floor(canvas.raw, floor_pixels, WIDTH, HEIGHT, FLOOR_W, BORDER)
        shown = True

    # The water rippled on by STEPS steps with drops and splashes, and the floor drawn through it
    for _ in range(STEPS):
        now, before = water
        for _ in range(DROPS):
            drop(now, WIDTH, random.randint(EDGE, WIDTH - 1 - EDGE), random.randint(EDGE, HEIGHT - 1 - EDGE), DROP_DEPTH)
        if random.random() < SPLASH_CHANCE:
            drop(now, WIDTH, random.randint(EDGE, WIDTH - 1 - EDGE), random.randint(EDGE, HEIGHT - 1 - EDGE), SPLASH_DEPTH)
        ripple(now, before, WIDTH, HEIGHT, CALMING)
        water.reverse()
    draw_water(water[0], canvas.raw, floor_pixels, WIDTH, HEIGHT, FLOOR_W, BORDER, BENDING, LIGHT, LIGHT_THRESHOLD)
