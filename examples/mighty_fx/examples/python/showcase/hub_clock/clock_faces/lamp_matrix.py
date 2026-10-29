import micropython
from picovector import brush, color, image, mat3, rect, shape

"""
A matrix of tungsten lamps in deep reflector cups for the hub clock, five across and seven down, lit in
the shape of a digit. When it changes, the lamps it needs light at once and the rest cool through
orange to a dull red. A colon is a pair of smaller lamps beside the matrix. showcase/lamp_matrix.py is
the fuller version.

Every stage of each lamp's glow is drawn once at the start, and a frame copies in only the lamps that
differ from what it last held.
"""

CHANGE_STEPS = 4                    # Frames through a change, the lamps going out a stage cooler each frame
COLON_BLINKS = False                # The colon's lamps stay lit
WRITE_BUDGET = 16                   # Writes a change may take across the panels, so a carry's cooling ends within its second
CARRY_TOGETHER = True               # Every digit of a carry changes at once, the lamps being switched

COLUMNS = 5
ROWS = 7
PITCH = 40                          # Panel pixels from one lamp to the next
RADIUS = 19                         # A reflector cup's radius
EDGE = 6                            # Panel pixels from the matrix to the panel's left edge, the colon taking the right
COLON_RADIUS = 10                   # A colon lamp's cup
COLON_ROWS = (2, 4)                 # The rows a colon's lamps sit level with
EMITTER = 0.32                      # How far an outermost lamp's emitter shows off its cup's middle, of the radius
PANEL = color.black
RIM = color.rgb(34, 34, 34)         # The cup's rim, a hard edge drawn over its light
RIM_W = 2                           # Panel pixels across the rim
BULB_RING = color.rgb(34, 34, 34)   # An unlit emitter, a dark ring
BULB_GLASS = color.rgb(85, 85, 85)  # Round its dull glass
ANTIALIAS = image.X4

# A filament's colour falls with its heat
STAGES = 5                          # How many steps of its glow are drawn, from just lit to full
FILAMENT = ((0.0, (0, 0, 0)), (0.12, (136, 17, 0)), (0.35, (238, 68, 0)),
            (0.65, (255, 153, 34)), (1.0, (255, 238, 187)))  # Colour at each brightness, from cold to white hot
CORE_LIFT = 0.3                     # How much hotter an emitter's middle runs than the rest of its glow

# The light a cup fills with, a ring at a time from the rim in towards the emitter, each ring's alpha
# layering over the rings before it
RINGS = (90, 70, 62, 60, 60, 62, 66, 72, 82, 96)

# The digits, a row of five lamps to each string, top to bottom, in the dot matrix shapes LCD modules use
FONT = {
    " ": ("00000",) * 7,
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
}
LAMPS = COLUMNS * ROWS

# The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so a smooth fade shows as
# bands. Each drawing is set onto those levels a pixel at a time, rounding up or down by a fixed 4x4
# pattern, an ordered dither, which breaks the bands up and stays put as a lamp changes stage
BAYER = bytes((0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5))

# Made by prepare() for the panel's size, and kept
lit_in = {}                         # Each digit's lamps that are lit, as a tuple of whether, along each row in turn
stages = []                         # Each lamp's drawings, unlit first as None, then a stage at a time to full
colon_stages = []                   # And the same for the colon's two lamps
backgrounds = {}                    # The panel with every cup unlit, by whether it has the colon's cups
placed = {}                         # What each frame already holds, by the frame's id
places = []                         # Each lamp's patch on the panel, then the colon's
side = colon_side = 0
source = rect(0, 0, 0, 0)
target = rect(0, 0, 0, 0)


@micropython.viper
def dither(pixels: ptr8, width: int, height: int, stride: int, pattern: ptr8):
    """
    Set every pixel of an image onto the panel's levels, in place, by an ordered dither, and make it
    opaque, as an antialiased edge can leave one just short. Compiled by viper, as it runs for every
    pixel of every drawing.
    """
    for y in range(height):
        for x in range(width):
            threshold = pattern[(y & 3) * 4 + (x & 3)]
            at = y * stride + x * 4
            for channel in range(3):
                value = pixels[at + channel]
                level = value // 17
                # Whether the part, of 17, passes the threshold's middle, (threshold + 0.5) of 16
                if (value - level * 17) * 32 > threshold * 34 + 17:
                    level += 1
                pixels[at + channel] = level * 17
            pixels[at + 3] = 255


def filament(level):
    """Calculate a tungsten filament's colour at a brightness from 0 to 1, between the FILAMENT stops."""
    for (low, cold), (high, hot) in zip(FILAMENT, FILAMENT[1:]):
        if level <= high:
            part = (level - low) / (high - low)
            return tuple(round(a + (b - a) * part) for a, b in zip(cold, hot))
    return FILAMENT[-1][1]


def cup(drawing, x, y, emitter_x, emitter_y, radius):
    """Draw an unlit cup, paler deep in around the emitter, with its unlit bulb."""
    for ring in range(12):
        part = ring / 11
        grey = round(26 + 26 * part)
        drawing.pen = color.rgb(grey, grey, grey)
        drawing.shape(shape.circle(x + (emitter_x - x) * part, y + (emitter_y - y) * part, radius * (1 - 0.8 * part)))
    # A dark ring round dull glass
    drawing.pen = BULB_RING
    drawing.shape(shape.circle(emitter_x, emitter_y, radius * 5 / 19))
    drawing.pen = BULB_GLASS
    drawing.shape(shape.circle(emitter_x, emitter_y, radius * 3 / 19))


def rim(drawing, x, y, radius):
    """Draw a cup's rim, laid over its light so a lit cup still reads as a cup."""
    drawing.pen = RIM
    drawing.shape(shape.circle(x, y, radius - RIM_W / 2).stroke(RIM_W))


def lit(background, left, top, size, x, y, emitter_x, emitter_y, radius, stage):
    """
    Draw a lamp at a stage of its glow, on a patch of its own over its piece of the background.

    The cup fills with the filament's colour in rings from the rim in towards the emitter, the emitter
    itself a ring of that colour round a hotter middle.
    """
    patch = image(size, size)
    patch.antialias = ANTIALIAS
    source.x, source.y, source.w, source.h = left, top, size, size
    patch.blit(background, source, rect(0, 0, size, size))

    x, y, emitter_x, emitter_y = x - left, y - top, emitter_x - left, emitter_y - top
    # A stage's strength rises quicker than its colour, so a dim filament still shows
    strength = min(1, stage / STAGES * 1.4)
    tint = color.rgb(*filament(stage / STAGES))
    for ring, alpha in enumerate(RINGS):
        part = ring / (len(RINGS) - 1)
        patch.pen = tint.with_alpha(round(alpha * strength))
        patch.shape(shape.circle(x + (emitter_x - x) * part, y + (emitter_y - y) * part, radius * (1 - 0.7 * part)))
    patch.pen = tint.with_alpha(round(255 * strength))
    patch.shape(shape.circle(emitter_x, emitter_y, radius * 5 / 19))
    patch.pen = color.rgb(*filament(min(1, stage / STAGES + CORE_LIFT))).with_alpha(round(255 * strength))
    patch.shape(shape.circle(emitter_x, emitter_y, radius * 3 / 19))

    rim(patch, x, y, radius)
    dither(patch.raw, size, size, patch.stride, BAYER)
    return patch


def mirrored(patch, size, flip_across, flip_down):
    """
    Copy a lamp's drawing flipped across the panel, down it, or both, for the lamp opposite it.

    The image pen lands a flip down one row low, and a flip down alone one column out as well, so
    those are shifted back a pixel.
    """
    if flip_across and flip_down:
        flip = mat3().translate(size, size - 1).scale(-1, -1)
    elif flip_across:
        flip = mat3().translate(size, 0).scale(-1, 1)
    else:
        flip = mat3().translate(1, size - 1).scale(1, -1)
    flipped = image(size, size)
    flipped.pen = brush.image(patch, flip)
    flipped.shape(shape.rectangle(0, 0, size, size))
    return flipped


def prepare(width, height):
    """Draw the backgrounds and every stage of every lamp, sized for a panel this size."""
    global side, colon_side
    side, colon_side = PITCH, COLON_RADIUS * 2 + 4
    first_x = EDGE + PITCH / 2
    first_y = (height - ROWS * PITCH) / 2 + PITCH / 2
    middle_x = first_x + (COLUMNS - 1) * PITCH / 2
    middle_y = first_y + (ROWS - 1) * PITCH / 2

    def middle(x, y, radius):
        """
        Find where a cup's emitter shows, the panel seen from in front of the matrix's middle, so an
        emitter at the back of a deep cup shows shifted towards it, by more the further out the cup is.
        """
        across = (x - middle_x) / (middle_x - first_x)
        down = (y - middle_y) / (middle_y - first_y)
        return x - radius * EMITTER * across, y - radius * EMITTER * down

    cups = [(first_x + column * PITCH, first_y + row * PITCH) for row in range(ROWS) for column in range(COLUMNS)]
    colon_x = (first_x + (COLUMNS - 0.5) * PITCH + width) / 2
    colon_cups = [(colon_x, first_y + row * PITCH) for row in COLON_ROWS]

    for digit, rows in FONT.items():
        lit_in[digit] = tuple(lamp == "1" for row in rows for lamp in row)

    background = image(width, height)
    background.antialias = ANTIALIAS
    background.pen = PANEL
    background.clear()
    for x, y in cups:
        cup(background, x, y, *middle(x, y, RADIUS), RADIUS)
        rim(background, x, y, RADIUS)
    dither(background.raw, width, height, background.stride, BAYER)
    backgrounds[False] = background

    with_colon = image(width, height)
    with_colon.antialias = ANTIALIAS
    with_colon.blit(background, 0, 0)
    for x, y in colon_cups:
        cup(with_colon, x, y, *middle(x, y, COLON_RADIUS), COLON_RADIUS)
        rim(with_colon, x, y, COLON_RADIUS)
    dither(with_colon.raw, width, height, with_colon.stride, BAYER)
    backgrounds[True] = with_colon

    # Each lamp past the matrix's middle row or column is the mirror image of the one opposite it
    for index, (x, y) in enumerate(cups):
        column, row = index % COLUMNS, index // COLUMNS
        left, top = round(x - side / 2), round(y - side / 2)
        places.append((left, top))
        opposite_column, opposite_row = min(column, COLUMNS - 1 - column), min(row, ROWS - 1 - row)
        if (opposite_column, opposite_row) != (column, row):
            opposite = stages[opposite_row * COLUMNS + opposite_column]
            stages.append([None] + [mirrored(patch, side, column != opposite_column, row != opposite_row)
                                    for patch in opposite[1:]])
        else:
            stages.append([None] + [lit(background, left, top, side, x, y, *middle(x, y, RADIUS), RADIUS, stage)
                                    for stage in range(1, STAGES + 1)])

    for x, y in colon_cups:
        left, top = round(x - colon_side / 2), round(y - colon_side / 2)
        places.append((left, top))
        colon_stages.append([None, lit(with_colon, left, top, colon_side, x, y, *middle(x, y, COLON_RADIUS),
                                       COLON_RADIUS, STAGES)])


def draw(frame, digit, colon_lit, previous=None, progress=1.0):
    """
    Draw a whole panel into the frame, the lamps of the digit lit.

    colon_lit is None on a panel without a colon. On the way from a previous digit, by progress from 0 to
    1, the lamps the digit needs are lit already and those it does not are cooling.
    """
    with_colon = colon_lit is not None
    held = placed.get(id(frame))
    if held is None:
        frame.raw[:] = backgrounds[with_colon].raw
        held = [with_colon, [0] * (LAMPS + 2)]
        placed[id(frame)] = held
    elif held[0] != with_colon:
        # Last drawn for a panel with the colon or without it, so only the colon's cups change
        for lamp in range(2):
            put(frame, backgrounds[with_colon], places[LAMPS + lamp], colon_side, None)
            held[1][LAMPS + lamp] = 0
        held[0] = with_colon
    showing = held[1]

    wanted = lit_in[digit]
    cooling = 0
    if previous is not None and progress < 1:
        before = lit_in[previous]
        cooling = round(STAGES * (1 - progress))
    else:
        before = wanted

    background = backgrounds[with_colon]
    for index in range(LAMPS):
        stage = STAGES if wanted[index] else (cooling if before[index] else 0)
        if stage != showing[index]:
            put(frame, background, places[index], side, stages[index][stage])
            showing[index] = stage

    if with_colon:
        stage = 1 if colon_lit else 0
        for lamp in range(2):
            if stage != showing[LAMPS + lamp]:
                put(frame, background, places[LAMPS + lamp], colon_side, colon_stages[lamp][stage])
                showing[LAMPS + lamp] = stage


def put(frame, background, place, size, patch):
    """Copy a lamp's drawing into place in the frame, or its piece of the background where it is out."""
    target.x, target.y, target.w, target.h = place[0], place[1], size, size
    if patch is None:
        source.x, source.y, source.w, source.h = target.x, target.y, size, size
        frame.blit(background, source, target)
    else:
        frame.blit(patch, target.x, target.y)
