from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import Screen280, ScreenGroup
from picovector import color, font, image, rect, shape

"""
Draw a motorway lane control gantry, a signal to a lane, working through a lane closure.

A signal is a square RGB lamp matrix with a lamp in each corner. The aspect is drawn at
the matrix's resolution and scaled up so each pixel fills one lamp, under a baked mask. The
corner lamps flash over it for a closed lane.

A panel on the hub is a lane. A group streams an aspect once to every lane showing it, so
a four lane gantry is one or two writes.

Press "Boot" to exit the program.
"""

# Constants for drawing
SCREEN = Screen280                  # A panel cannot be asked its size, so the class is named.
                                    # A signal is square, centred in a housing on a 2.8"
ROTATION = 0                        # 0 or 180, portrait so both panel sizes sit edge to edge across a gantry

LAMP = 6                            # Panel pixels a lamp, the smallest that reads as round
APERTURE = 0.7                      # The lit hole, as a fraction of a lamp's width
SOFTEN = 1.0                        # Panel pixels the aperture's edge fades over
CORNER_AIR = 3                      # The face left showing around a corner lamp, which sets it in

HOUSING = color.black               # What the signals are set into
FACE = color.rgb(17, 17, 17)        # A signal's own face, so it reads as a panel even when it is blank
KEYLINE = color.rgb(51, 51, 51)     # Its edge, which finds it against the housing
UNLIT = color.rgb(34, 34, 34)       # A lamp that is not lit, a shade up from the face behind it
RED = color.rgb(255, 34, 34)        # A red aspect, the ring of a speed limit,
                                    # the X of a closed lane, and a corner lamp lit
WHITE = color.rgb(238, 238, 238)    # The number inside a ring, the national speed limit's disc,
                                    # and the arrow into the lane alongside
GREEN = color.rgb(0, 221, 170)      # An arrow straight down, green being the colour for a lane open

CORNER_OFF = color.rgb(51, 17, 17)  # A corner lamp between flashes, still visibly red.
                                    # Lit, it is the aspect's red

# Every aspect is set out in lamps, a signal being designed that way, and every stroke of an arrow or a cross
# lies at 45 degrees or square, which is how the reference signals draw them
RING_RADIUS = 14                # A speed limit's ring, which is the widest aspect and so sets the matrix
RING_LAMPS = 3                  # And how many lamps thick it is
STROKE = 5                      # Lamps across a stroke running square on, and
ACROSS = 7                      # along a row where it runs at 45 degrees, which is the same visual weight
BAND_ACROSS = 9                 # The unlit band across the national speed limit, along a row, being wider
CROSS_ARM = 10                  # How far each arm of the cross runs from the middle
NUMBER_FONT = font.manticore    # The number in a speed limit ring. dir(font) lists them all
HOLD = 5.0                      # How long the gantry holds a setting, in seconds
FLASH_MS = 500                  # How long each side's pair of corner lamps stays lit for

# The aspects a lane can show
BLANK = None
OPEN = ("arrow", 0)             # A lane open, which is the arrow straight down
KEEP_RIGHT = ("arrow", 1)       # Move to the lane on the right, and
KEEP_LEFT = ("arrow", -1)       # to the one on the left
SHUT = ("closed", 0)
NATIONAL = ("national", 0)
FORTY = ("speed", 40)
SIXTY = ("speed", 60)

# What the gantry shows, a setting at a time and an aspect a lane, six wide so any number answering are
# driven. Lanes close one at a time, and each points drivers across first
GANTRY = (
    (BLANK, BLANK, BLANK, BLANK, BLANK, BLANK),
    (OPEN, OPEN, OPEN, OPEN, OPEN, OPEN),
    (SIXTY, SIXTY, SIXTY, SIXTY, SIXTY, SIXTY),
    (FORTY, FORTY, FORTY, FORTY, FORTY, FORTY),
    (KEEP_RIGHT, KEEP_RIGHT, FORTY, FORTY, FORTY, FORTY),
    (SHUT, KEEP_RIGHT, FORTY, FORTY, FORTY, FORTY),
    (SHUT, SHUT, FORTY, FORTY, FORTY, FORTY),
    (SHUT, SHUT, FORTY, FORTY, SIXTY, SIXTY),
    (NATIONAL, NATIONAL, NATIONAL, NATIONAL, NATIONAL, NATIONAL),
    (BLANK, BLANK, BLANK, BLANK, BLANK, BLANK),
)

# Create a MightyFX object with a screen hub across both SP/CE ports. One carries the screen bus and the other
# gives up its five lines as extra chip selects, which lets one port drive six panels instead of one
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_SELECTS)

# Build a screen on every hub port and keep those that answer, as a hub need not be full
screens = []
for port in mighty.hub.ports:
    try:
        screens.append(SCREEN(port))
    except ValueError:
        pass

if not screens:
    # Give the ports back before saying so. A hub drives its chip selects high, and one of those is the
    # backlight pin of whatever is plugged into that port
    mighty.shutdown()
    raise RuntimeError("No panels answered! Check the hub is plugged into SP/CE A, with its panels on the hub rather than on the board")

# A group holds however many lanes answered to one refresh, so a setting reaches all on one frame
gantry = ScreenGroup(*screens, rotation=ROTATION)

# The distinct aspects each setting needs over the lanes that answered, so a setting costs a write per aspect
ASPECTS_IN = []
for setting in GANTRY:
    distinct = []
    for aspect in setting[:len(screens)]:
        if aspect not in distinct:
            distinct.append(aspect)

    ASPECTS_IN.append(distinct)

# One canvas serves every lane and is drawn again for each aspect a setting calls for, portrait as the panels are
WIDTH, HEIGHT = screens[0].width, screens[0].height
canvas = image(WIDTH, HEIGHT)

# The signal is square and as large as the panel allows, centred, so the housing is whatever is left
SIGNAL = min(WIDTH, HEIGHT)
SIGNAL_X = (WIDTH - SIGNAL) // 2
SIGNAL_Y = (HEIGHT - SIGNAL) // 2

# The matrix is exactly the ring and odd across so it has a middle lamp, which leaves the corner lamps room
CELLS = RING_RADIUS * 2 + 1
MIDDLE = RING_RADIUS
SIDE = CELLS * LAMP
MATRIX_X = SIGNAL_X + (SIGNAL - SIDE) // 2
MATRIX_Y = SIGNAL_Y + (SIGNAL - SIDE) // 2

# A corner lamp as large as the face allows, its clearance taken along the diagonal
INSET = (SIGNAL - SIDE) // 2
CORNER_AT = int(INSET / (1 + 2 ** -0.5))
CORNER_R = CORNER_AT - CORNER_AIR

# The aspect is drawn here, one pixel to a lamp, and scaled up on the way to the panel
lamps = image(CELLS, CELLS)
lamps.font = NUMBER_FONT

# Lettering is measured on its own matrix, as measuring clears it
scratch = image(CELLS, CELLS)
scratch.font = NUMBER_FONT


def lettering_box(text, scale):
    """
    Measure where a string's lettering lands drawn at the origin, as (left, top, right, bottom) in lamps.

    Centring needs the drawn lettering, since a face's metrics are not where it lands.
    """
    scratch.pen = color.black
    scratch.clear()
    scratch.pen = color.white
    scratch.text(text, 0, 0, scale)

    raw, stride = scratch.raw, scratch.stride
    left, top, right, bottom = CELLS, CELLS, -1, -1
    for y in range(CELLS):
        for x in range(CELLS):
            if raw[y * stride + x * 4] > 127:
                left, right = min(left, x), max(right, x)
                top, bottom = min(top, y), max(bottom, y)

    return left, top, right, bottom


# The digits' drawn height at one step, over all ten so every limit sizes alike
LETTERING_TOP, LETTERING_BOTTOM = CELLS, -1
for digit in "0123456789":
    _, digit_top, _, digit_bottom = lettering_box(digit, 1)
    LETTERING_TOP = min(LETTERING_TOP, digit_top)
    LETTERING_BOTTOM = max(LETTERING_BOTTOM, digit_bottom)


# Every speed limit the gantry shows
SPEEDS = {aspect[1] for setting in GANTRY for aspect in setting
          if aspect is not None and aspect[0] == "speed"}


def number_scale():
    """The largest whole step whose digits fit inside the ring, the fit taken at the lettering box's corner."""
    if not SPEEDS:
        return 1

    inner = RING_RADIUS - RING_LAMPS
    tall = LETTERING_BOTTOM - LETTERING_TOP + 1
    scale = 1
    while True:
        step = scale + 1
        wide = max(int(lamps.measure_text(f"{speed}", font_size=step)[0]) for speed in SPEEDS)
        if ((wide / 2) ** 2 + (tall * step / 2) ** 2) ** 0.5 > inner:
            return scale

        scale = step


def measure_number(limit):
    """Measure where this limit's text goes so its lettering lands in the middle of the ring."""
    left, top, right, bottom = lettering_box(f"{limit}", NUMBER_SCALE)
    return round((CELLS - 1 - left - right) / 2), round((CELLS - 1 - top - bottom) / 2)


NUMBER_SCALE = number_scale()
NUMBER_AT = {limit: measure_number(limit) for limit in SPEEDS}


# Each way an arrow points is its own drawing, a shape that reads straight down not reading turned. Each
# entry is the tip's direction, the two directions its barbs run back in, how far their corner sits from the
# middle, how far each barb runs, then where the shaft starts and stops. Directions step a lamp at a time.
# The rest are lamps along the direction given
ARROWS = {-1: ((-1, 1), ((0, -1), (1, 0)), 11, 16, 10, 2),
          0: ((0, 1), ((-1, -1), (1, -1)), 11, 10, 14, 1),
          1: ((1, 1), ((0, -1), (-1, 0)), 11, 16, 10, 2)}

# The four corner lamps, built once because they never move. A pair to a side, so they alternate left
# against right as the roadworks sign's beacons do, and the first two are the left pair
FAR = SIGNAL - CORNER_AT
CORNER_LAMPS = tuple(shape.circle(SIGNAL_X + x, SIGNAL_Y + y, CORNER_R)
                     for x, y in ((CORNER_AT, CORNER_AT), (CORNER_AT, FAR), (FAR, CORNER_AT), (FAR, FAR)))

SCALE_FROM = rect(0, 0, CELLS, CELLS)
SCALE_TO = rect(MATRIX_X, MATRIX_Y, SIDE, SIDE)

print(f"Gantry of {len(screens)} lane(s) of {len(mighty.hub.ports)}, {WIDTH}x{HEIGHT} a panel,"
      f" a {SIGNAL}px signal holding {CELLS}x{CELLS} lamps of {LAMP}px inside {CORNER_R * 2}px corners,"
      f" its numbers drawing {LETTERING_BOTTOM - LETTERING_TOP + 1} lamps at scale {NUMBER_SCALE},"
      f" {sum(len(aspects) for aspects in ASPECTS_IN)} writes over {len(GANTRY)} settings"
      f" where a lane at a time would be {len(GANTRY) * len(screens)}")


def fill_frame(face, outer, inner):
    """
    Fill the band between two rectangles in four pieces, leaving the inner one untouched.

    An opaque fill cannot be cleared again.
    """
    face.rectangle(rect(outer.x, outer.y, outer.w, inner.y - outer.y))
    face.rectangle(rect(outer.x, inner.y + inner.h, outer.w, outer.y + outer.h - inner.y - inner.h))
    face.rectangle(rect(outer.x, inner.y, inner.x - outer.x, inner.h))
    face.rectangle(rect(inner.x + inner.w, inner.y, outer.x + outer.w - inner.x - inner.w, inner.h))


def bake_mask():
    """
    Bake the signal's face, an aperture over every lamp and the rest opaque, a row of lamps at a time.

    Shared by every lane, since every signal is the same shape.
    """
    tile = image(LAMP, LAMP)
    tile.pen = color.transparent
    tile.clear()
    middle = (LAMP - 1) / 2
    radius = LAMP * APERTURE / 2 - 0.5
    for y in range(LAMP):
        for x in range(LAMP):
            over = ((x - middle) ** 2 + (y - middle) ** 2) ** 0.5 - radius
            if over > 0:
                tile.pen = FACE.with_alpha(min(255, round(over / SOFTEN * 255)))
                tile.rectangle(rect(x, y, 1, 1))

    face = image(WIDTH, HEIGHT)
    face.pen = color.transparent
    face.clear()

    # The housing, then the signal's edge and its own face, each stopping short of the one inside it
    signal_at = rect(SIGNAL_X, SIGNAL_Y, SIGNAL, SIGNAL)
    inside_at = rect(SIGNAL_X + 1, SIGNAL_Y + 1, SIGNAL - 2, SIGNAL - 2)
    matrix_at = rect(MATRIX_X, MATRIX_Y, SIDE, SIDE)

    face.pen = HOUSING
    fill_frame(face, rect(0, 0, WIDTH, HEIGHT), signal_at)
    face.pen = KEYLINE
    fill_frame(face, signal_at, inside_at)
    face.pen = FACE
    fill_frame(face, inside_at, matrix_at)

    row = image(SIDE, LAMP)
    row.pen = color.transparent
    row.clear()
    for cell in range(CELLS):
        row.blit(tile, cell * LAMP, 0)

    for cell in range(CELLS):
        face.blit(row, MATRIX_X, MATRIX_Y + cell * LAMP)

    return face


mask = bake_mask()


def draw_speed(limit):
    """Draw a speed limit, a ring of two filled circles with the inner one unlit around the number."""
    middle = CELLS / 2
    lamps.pen = RED
    lamps.circle(middle, middle, RING_RADIUS)
    lamps.pen = UNLIT
    lamps.circle(middle, middle, RING_RADIUS - RING_LAMPS)

    lamps.pen = WHITE
    across, down = NUMBER_AT[limit]
    lamps.text(f"{limit}", across, down, NUMBER_SCALE)


def lamp_stroke(from_x, from_y, to_x, to_y, weight, across, carry=(0, 0)):
    """
    Light a stroke of whole lamps between two lamps, square on or at 45 degrees, a row at a time.

    A 45 degree vector stroke lights an even count of lamps, which cannot centre on a middle lamp.
    weight is the count across a square stroke, across the count along a row at 45 degrees, and
    carry moves each end outwards where positive.
    """
    starts, ends = carry
    if from_x == to_x:
        low, high = (starts, ends) if from_y < to_y else (ends, starts)
        top, bottom = min(from_y, to_y) - low, max(from_y, to_y) + high
        lamps.rectangle(rect(from_x - weight // 2, top, weight, bottom - top + 1))
        return

    if from_y == to_y:
        low, high = (starts, ends) if from_x < to_x else (ends, starts)
        left, right = min(from_x, to_x) - low, max(from_x, to_x) + high
        lamps.rectangle(rect(left, from_y - weight // 2, right - left + 1, weight))
        return

    # Down a diagonal stroke's middle one figure holds while the other runs, so its ends are a limit on the
    # second, and a row's lit run is the middle's reach clipped by both of them
    fall = 1 if (to_x - from_x) * (to_y - from_y) > 0 else -1
    reach = across // 2
    middle = from_x - fall * from_y
    at_from, at_to = from_x + fall * from_y, to_x + fall * to_y
    first, last = ((at_from - starts, at_to + ends) if at_from < at_to
                   else (at_to - ends, at_from + starts))

    edge = reach + max(starts, ends, 0)
    for y in range(min(from_y, to_y) - edge, max(from_y, to_y) + edge + 1):
        left = max(middle + fall * y - reach, first - fall * y)
        right = min(middle + fall * y + reach, last - fall * y)
        if left <= right:
            lamps.rectangle(rect(left, y, right - left + 1, 1))


def draw_national():
    """Draw the national speed limit, a white disc crossed by an unlit band from low left to high right."""
    lamps.pen = WHITE
    lamps.circle(CELLS / 2, CELLS / 2, RING_RADIUS)

    # Past the disc at both ends, so the band cuts clean to its edge and does not stop inside it
    lamps.pen = UNLIT
    over = RING_RADIUS + 1
    lamp_stroke(MIDDLE - over, MIDDLE + over, MIDDLE + over, MIDDLE - over,
                round(BAND_ACROSS / 2 ** 0.5) | 1, BAND_ACROSS)


def draw_closed():
    """Draw a closed lane's red cross, four strokes run in from their tips so each tip is a single lamp."""
    lamps.pen = RED
    for corner_x, corner_y in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        lamp_stroke(MIDDLE + corner_x * CROSS_ARM, MIDDLE + corner_y * CROSS_ARM, MIDDLE, MIDDLE,
                    STROKE, ACROSS, (-1, 0))


def draw_arrow(towards):
    """
    Draw the arrow, green straight down for a lane open and white turned across for a lane change.

    A towards of 0 points down, 1 to the lane on the right and -1 to the one on the left.
    """
    lamps.pen = GREEN if towards == 0 else WHITE
    point, barbs, at, back, from_here, to_there = ARROWS[towards]

    corner_x = MIDDLE + point[0] * at
    corner_y = MIDDLE + point[1] * at
    for barb in barbs:
        # A square barb's middle sits in from the corner by half its weight. A diagonal one is carried past
        # the corner instead, so the pair comes to a point and does not stop where their middles cross
        square = barb[0] == 0 or barb[1] == 0
        slip_x = -point[0] * (STROKE // 2) if barb[0] == 0 else 0
        slip_y = -point[1] * (STROKE // 2) if barb[1] == 0 else 0
        lamp_stroke(corner_x + slip_x, corner_y + slip_y,
                    corner_x + slip_x + barb[0] * back, corner_y + slip_y + barb[1] * back,
                    STROKE, ACROSS, (0, 0) if square else (ACROSS // 2, -1))

    # The shaft in two, each half running in to the middle from its own end, for the same reason the cross is
    # in four, as only the start of a stroke can be pulled in to a tip of one lamp
    trim = (-1, 0) if point[0] and point[1] else (0, 0)
    for reach, way in ((from_here, -1), (to_there, 1)):
        lamp_stroke(MIDDLE + way * point[0] * reach, MIDDLE + way * point[1] * reach,
                    MIDDLE, MIDDLE, STROKE, ACROSS, trim)


def draw_signal(aspect, on_the_left):
    """Draw one signal on the canvas, its aspect on the matrix, the mask over it, then the corner lamps."""
    lamps.pen = UNLIT
    lamps.clear()
    if aspect is not None:
        kind, value = aspect
        if kind == "speed":
            draw_speed(value)
        elif kind == "national":
            draw_national()
        elif kind == "closed":
            draw_closed()
        else:
            draw_arrow(value)

    canvas.blit(lamps, SCALE_FROM, SCALE_TO, image.NEAREST)
    canvas.blit(mask, 0, 0)

    # Corner lamps are bolted to the face over the mask, and flash only for a closed lane.
    # The first two are the left pair, lit when on_the_left is true
    flashing = aspect is not None and aspect[0] == "closed"
    for index, lamp in enumerate(CORNER_LAMPS):
        canvas.pen = RED if flashing and (index < 2) == on_the_left else CORNER_OFF
        canvas.shape(lamp)


def send(setting, on_the_left):
    """Send one setting to the gantry an aspect at a time, to every lane showing it."""
    for aspect in ASPECTS_IN[setting]:
        draw_signal(aspect, on_the_left)
        gantry.update(canvas, to=tuple(screen for screen, showing in zip(screens, GANTRY[setting])
                                       if showing == aspect))


pacer = Pacer(0.02)                 # The gantry's clock, looking for a change every 20ms
shown = None

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = pacer.elapsed
        frame = (int(elapsed / (HOLD * 1000)) % len(GANTRY), bool(elapsed // FLASH_MS % 2))

        # Sent again at every flash even where no lamp flashes, which keeps the group's panels in phase
        if frame != shown:
            send(*frame)
            shown = frame

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
