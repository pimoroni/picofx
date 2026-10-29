import math
from picovector import color, font, image, mat3, rect, shape

"""
A flip-dot digit for the hub clock, a grid of discs yellow one side and dark the other. When the digit
changes, the discs that differ turn over, a column after the column before. A colon is a pair of discs
beside the grid. showcase/flip_dot_sign.py is the fuller version.
"""

DIGIT_FONT = "/rom/fonts/smart.ppf"  # A pixel face, a pixel to a disc
CHANGE_STEPS = 5                    # Frames through a change
COLON_BLINKS = False                # The colon's discs stay showing yellow
WRITE_BUDGET = None                 # Every frame of a turn shows, however long a wrap's cascade takes
CARRY_FROM_LEFT = True              # A carry sweeps the panels left to right as the discs sweep each panel, the seconds keeping their pace

COLUMNS = 8
ROWS = 11
CELL = 26                           # The disc pitch in panel pixels
EDGE = 2                            # Panel pixels from the grid to the panel's left edge, the colon taking the right
COLON_ROWS = (3, 7)                 # The rows the colon's discs sit level with
TURN = 0.5                          # How much of a change one disc takes to turn over, the columns sweeping through the rest
DOT_SIDES = 8                       # Octagonal discs, as one type has
DOT_TWIST = 22.5                    # Turns the octagon so its flats face up and along, as a real one sits
DOT_INSET = 2                       # How much of the frame shows between one disc and the next
FLIP_AXIS = 45                      # The angle of the diagonal a disc turns about, corner to corner
STOP_ANGLE = 135                    # The post the yellow face rests against, bottom left as seen
PIN_SHARE = 0.25                    # A post's size against the disc's
FLIP_STEPS = 6                      # How many faces a turn is drawn with
LIT = color.rgb(240, 230, 40)       # A disc showing its yellow face
UNLIT = color.rgb(48, 46, 44)       # And its dark one, which a real disc still shows plainly
STOP = color.rgb(90, 88, 84)        # The posts, lighter than either face so they read as parts
FRAME = color.black                 # What the discs are set into

DOT = CELL - DOT_INSET * 2
REACH = 1.0 / math.cos(math.pi / DOT_SIDES)
NUDGE = 0.5
PIN_PIXELS = max(2, round(DOT * PIN_SHARE))
PIN_AT = PIN_PIXELS // 2
PIN_REACH = 1.0 / math.cos(math.pi / 8)
DISCS = COLUMNS * ROWS

# Made by prepare() for the panel's size, and kept
yellow_in = {}                      # Each digit's discs showing yellow, along each row in turn
tiles = []                          # The yellow face at each step of its turn, then the dark one
backgrounds = {}                    # Every disc dark, by whether the panel has the colon's discs
placed = {}                         # What each frame already holds, by the frame's id
places = []                         # Where each disc's tile goes, then the colon's
cell = rect(0, 0, DOT, DOT)         # A disc's place, made once, a rect built per disc being an allocation


def post(tile, angle):
    """Draw one of a cell's two posts, where it is seen."""
    seen = math.radians(angle)
    x = PIN_AT if math.cos(seen) < 0 else DOT - PIN_AT - PIN_PIXELS
    y = PIN_AT if math.sin(seen) < 0 else DOT - PIN_AT - PIN_PIXELS
    standing = shape.regular_polygon(0, 0, PIN_PIXELS / 2 * PIN_REACH, 8)
    standing.transform = mat3().translate(x + PIN_PIXELS / 2 + NUDGE, y + PIN_PIXELS / 2).rotate(DOT_TWIST)
    tile.pen = STOP
    tile.shape(standing)


def faces(colour, stop_angle):
    """Draw a face at every step of its turn, from flat on to edge on, each tile carrying its frame."""
    middle = DOT / 2
    steps = []
    for step in range(FLIP_STEPS):
        squash = max(1.0 / DOT, math.cos(math.pi / 2 * step / (FLIP_STEPS - 1)))
        tile = image(DOT, DOT)
        tile.pen = FRAME
        tile.clear()
        if squash == 1.0:
            placing = mat3().translate(middle + NUDGE, middle).rotate(DOT_TWIST)
        else:
            placing = mat3().translate(middle + NUDGE, middle).rotate(FLIP_AXIS) \
                            .scale(1, squash).rotate(DOT_TWIST - FLIP_AXIS)
        post(tile, stop_angle + 180)
        dot = shape.regular_polygon(0, 0, middle * REACH, DOT_SIDES)
        dot.transform = placing
        tile.pen = colour
        tile.shape(dot)
        post(tile, stop_angle)
        steps.append(tile)
    return steps


def prepare(width, height):
    """Draw every face of a disc's turn and the dark grid, sized for a panel this size."""
    top = (height - ROWS * CELL) // 2
    for index in range(DISCS):
        places.append((EDGE + index % COLUMNS * CELL + DOT_INSET, top + index // COLUMNS * CELL + DOT_INSET))
    colon_left = (EDGE + COLUMNS * CELL + width) // 2 - CELL // 2
    for row in COLON_ROWS:
        places.append((colon_left + DOT_INSET, top + row * CELL + DOT_INSET))

    # Each digit drawn a pixel to a disc, its lettering's rows found and set one row down from the top
    face = font.load(DIGIT_FONT)
    pattern = image(COLUMNS + 2, face.height + 4)
    pattern.font = face
    for digit in "0123456789":
        pattern.pen = color.black
        pattern.clear()
        pattern.pen = color.white
        pattern.text(digit, 1, 0)
        raw, stride = pattern.raw, pattern.stride
        rows = [y for y in range(pattern.height) if any(raw[y * stride + x * 4] for x in range(COLUMNS))]
        first = rows[0] - 1
        yellow_in[digit] = tuple(
            0 <= first + row < pattern.height and raw[(first + row) * stride + column * 4] != 0
            for row in range(ROWS) for column in range(COLUMNS))
    yellow_in[" "] = (False,) * DISCS

    tiles.extend(faces(LIT, STOP_ANGLE) + faces(UNLIT, STOP_ANGLE + 180))
    for with_colon in (False, True):
        background = image(width, height)
        background.pen = FRAME
        background.clear()
        for x, y in places[:DISCS + (2 if with_colon else 0)]:
            background.blit(tiles[FLIP_STEPS], x, y)
        backgrounds[with_colon] = background


def draw(frame, digit, colon_lit, previous=None, progress=1.0):
    """
    Draw a whole panel into the frame, the discs of the digit showing yellow.

    colon_lit is None on a panel without a colon. On the way from a previous digit, by progress from 0 to
    1, the discs that differ turn over, the leftmost column first.
    """
    with_colon = colon_lit is not None
    held = placed.get(id(frame))
    if held is None:
        frame.raw[:] = backgrounds[with_colon].raw
        held = [with_colon, [FLIP_STEPS] * (DISCS + 2)]
        placed[id(frame)] = held
    elif held[0] != with_colon:
        # Last drawn for a panel with the colon or without it, so only the colon's discs change
        for disc in (DISCS, DISCS + 1):
            cell.x, cell.y = places[disc]
            frame.blit(backgrounds[with_colon], cell, cell)
            held[1][disc] = FLIP_STEPS
        held[0] = with_colon
    showing = held[1]

    wanted = yellow_in[digit]
    before = yellow_in[previous] if previous is not None and progress < 1 else wanted
    sweep = (1 - TURN) / (COLUMNS - 1)
    for index in range(DISCS):
        if before[index] == wanted[index]:
            tile = 0 if wanted[index] else FLIP_STEPS
        else:
            # Half a turn to edge on showing the old face, then half back showing the new
            phase = min(1, max(0, (progress - index % COLUMNS * sweep) / TURN))
            if phase < 0.5:
                tile = round(phase * 2 * (FLIP_STEPS - 1)) + (0 if before[index] else FLIP_STEPS)
            else:
                tile = round((1 - phase) * 2 * (FLIP_STEPS - 1)) + (0 if wanted[index] else FLIP_STEPS)
        if tile != showing[index]:
            frame.blit(tiles[tile], *places[index])
            showing[index] = tile

    if with_colon:
        tile = 0 if colon_lit else FLIP_STEPS
        for disc in (DISCS, DISCS + 1):
            if tile != showing[disc]:
                frame.blit(tiles[tile], *places[disc])
                showing[disc] = tile
