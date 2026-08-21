import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280, ScreenGroup
from picovector import color, font, image, rect, shape

"""
Draw a motorway lane control gantry, a signal to a lane, working through a lane closure.

A signal is a square RGB lamp matrix with a lamp in each corner, which makes the
40 a ring of discrete lamps rather than a drawn circle. The aspect is drawn at the
matrix's own resolution, scaled up a lamp to a block, and a baked mask laid over it; the
corner lamps are not part of the matrix, so they go on over the top and flash a side at a
time, for a closed lane only.

A panel on a screen hub is a lane, so the gantry is as wide as the hub is populated. The
lanes change together, which is what a group is for: an aspect is drawn once and streamed
to every lane showing it, so a four lane gantry is one or two writes, not four.

Press "Boot" to exit the program.
"""

# Constants for drawing
# A panel cannot be asked what size it is, only whether one answered, so the class has to be named. A
# gantry signal is square, which is the 1.54" panel's own shape; on a 2.8" it is centred and the rest of the
# panel is left as the housing around it
SCREEN = Screen280
ROTATION = 90                   # A signal is drawn landscape and turned a quarter onto its panel

# Panel pixels across one lamp of the matrix. An aperture reads as round from about six pixels up, so this
# is the finest matrix the panel holds, and it puts a real signal's resolution inside the face
LAMP = 6
APERTURE = 0.7                  # The lit hole, as a fraction of a lamp's width
SOFTEN = 1.0                    # Panel pixels the aperture's edge fades over
CORNER_AIR = 3                  # The face left showing around a corner lamp, which sets it in

HOUSING = color.black           # What the signals are set into
FACE = color.rgb(17, 17, 17)    # A signal's own face, so it reads as a panel even when it is blank
KEYLINE = color.rgb(51, 51, 51)  # Its edge, which finds it against the housing
UNLIT = color.rgb(34, 34, 34)   # A lamp that is not lit, a shade up from the face behind it
# A red aspect: the ring of a speed limit, the X of a closed lane, and a corner lamp lit
RED = color.rgb(255, 34, 34)
# The number inside a ring, the national speed limit's disc, and the arrow into the lane alongside
WHITE = color.rgb(238, 238, 238)
GREEN = color.rgb(0, 221, 170)   # An arrow straight down, green being the colour for a lane open
# A corner lamp between flashes, which stays visibly red, not dark. Lit, it is the same red as an
# aspect, the lamps on a real signal being the one colour
CORNER_OFF = color.rgb(51, 17, 17)

# Every aspect is set out in lamps, a signal being designed that way, and every stroke of an arrow or a cross
# lies at 45 degrees or square, which is how the reference signals draw them
RING_RADIUS = 14                # A speed limit's ring, which is the widest aspect and so sets the matrix
RING_LAMPS = 3                  # And how many lamps thick it is
STROKE = 5                      # Lamps across a stroke running square on, and
ACROSS = 7                      # along a row where it runs at 45 degrees, which is the same visual weight
BAND_ACROSS = 9                 # The unlit band across the national speed limit, along a row, being wider
CROSS_ARM = 10                  # How far each arm of the cross runs from the middle
NUMBER_FONT = "manticore"       # The number in a speed limit ring. dir(font) lists all 37
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

# What the gantry shows, a setting at a time and an aspect to a lane, as wide as a full hub so that however
# many answered are all driven. Two lanes close, one at a time and each pointing drivers into the lane beside
# it first, and the national speed limit goes up as the restriction is lifted, which is the order a real one
# works in. Two lanes carrying the same aspect is also what makes a write a subset and not a single panel
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
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_LINES)

# The hub hands out a port per chip select it reaches, whether or not a panel is on the end of it. A panel
# that is not there refuses to be created, so build them all and keep whichever answered: a lane to each
screens = []
for port in mighty.hub.ports:
    try:
        screens.append(SCREEN(port))
    except ValueError:
        pass

if not screens:
    # Give the connectors back before saying so. A hub drives its chip selects high, and one of those is the
    # backlight pin of whatever is plugged into that connector
    mighty.shutdown()
    raise RuntimeError("No panels answered! Check the hub is plugged into SP/CE A, with its panels on the hub rather than on the board")

# A group holds the lanes to one refresh, so a setting reaches all of them on one frame and any tear band
# crawls along the gantry. A group of one is still a gantry, so however many answered are driven the same way
gantry = ScreenGroup(*screens)

# The distinct aspects each setting calls for, over the lanes that answered, worked out once. This is what
# makes a setting cost a write per aspect, not per lane
ASPECTS_IN = []
for setting in GANTRY:
    distinct = []
    for aspect in setting[:len(screens)]:
        if aspect not in distinct:
            distinct.append(aspect)

    ASPECTS_IN.append(distinct)

# One canvas serves every lane, drawn again for each aspect a setting calls for. Landscape and turned a
# quarter onto the panels. On the heap, not in SRAM, a gantry redrawing only when it changes
WIDTH, HEIGHT = screens[0].height, screens[0].width
canvas = image(WIDTH, HEIGHT)

# The signal is square and as large as the panel allows, centred, so the housing is whatever is left
SIGNAL = min(WIDTH, HEIGHT)
SIGNAL_X = (WIDTH - SIGNAL) // 2
SIGNAL_Y = (HEIGHT - SIGNAL) // 2

# The matrix is exactly the ring, that being the widest aspect, and odd across so a middle lamp exists to
# centre the rest on. Sizing it to the aspects, not to the space left over is what leaves the corner
# lamps room: nothing is drawn in a border the ring does not reach
CELLS = RING_RADIUS * 2 + 1
MIDDLE = RING_RADIUS
SIDE = CELLS * LAMP
MATRIX_X = SIGNAL_X + (SIGNAL - SIDE) // 2
MATRIX_Y = SIGNAL_Y + (SIGNAL - SIDE) // 2

# A corner lamp is then as large as the face around the matrix allows. The clearance is taken along the
# diagonal because a lamp only ever threatens the matrix's corner, which leaves it larger than pulling it
# clear of the nearest side would
INSET = (SIGNAL - SIDE) // 2
CORNER_AT = int(INSET / (1 + 2 ** -0.5))
CORNER_R = CORNER_AT - CORNER_AIR

# The aspect is drawn here, one pixel to a lamp, and scaled up on the way to the panel
lamps = image(CELLS, CELLS)
number_font = getattr(font, NUMBER_FONT)
lamps.font = number_font

# Ink is measured on its own matrix, because measuring means clearing and drawing: sharing the one above
# would wipe a ring already laid down when a limit is placed for the first time
scratch = image(CELLS, CELLS)
scratch.font = number_font


def ink_box(text, scale):
    """Where a string's ink lands when drawn at the origin, as (left, top, right, bottom) in lamps.

    Neither figure a font offers is the ink. `measure_text` gives the advance, which carries the bearing
    past the last glyph, and the declared height is the box a glyph sits in. Centring on either leaves the
    number visibly off centre inside the ring, so it is measured instead.
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


# The digits' ink height at one step, over all ten so any limit sizes the same, which is what the scale is
# taken from
INK_TOP, INK_BOTTOM = CELLS, -1
for digit in "0123456789":
    _, digit_top, _, digit_bottom = ink_box(digit, 1)
    INK_TOP = min(INK_TOP, digit_top)
    INK_BOTTOM = max(INK_BOTTOM, digit_bottom)


def number_scale():
    """The largest whole step whose digits stay inside the ring, a pixel font scaling no other way.

    Width and height both have to fit, so the fit is taken at the corner of the ink box, that being the point
    which reaches furthest from the middle. Sizing on height alone lets a short faced font take a step it
    cannot fit across, and the number then runs out through the ring.
    """
    speeds = {aspect[1] for setting in GANTRY for aspect in setting
              if aspect is not None and aspect[0] == "speed"}
    if not speeds:
        return 1

    inner = RING_RADIUS - RING_LAMPS
    tall = INK_BOTTOM - INK_TOP + 1
    scale = 1
    while True:
        step = scale + 1
        wide = max(int(lamps.measure_text(f"{speed}", font_size=step)[0]) for speed in speeds)
        if ((wide / 2) ** 2 + (tall * step / 2) ** 2) ** 0.5 > inner:
            return scale

        scale = step


NUMBER_SCALE = number_scale()
NUMBER_AT = {}


def number_at(limit):
    """Where this limit's text goes so its ink lands in the middle of the ring, measured once and kept."""
    if limit not in NUMBER_AT:
        left, top, right, bottom = ink_box(f"{limit}", NUMBER_SCALE)
        NUMBER_AT[limit] = (round((CELLS - 1 - left - right) / 2), round((CELLS - 1 - top - bottom) / 2))

    return NUMBER_AT[limit]


# Each way an arrow points is its own drawing, a shape that reads straight down not reading turned. Each
# entry is the tip's direction, the two directions its barbs run back in, how far their corner sits from the
# middle, how far each barb runs, then where the shaft starts and stops. Directions step a lamp at a time;
# the rest are lamps along the direction given
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
      f" {NUMBER_FONT} inking {INK_BOTTOM - INK_TOP + 1} lamps at scale {NUMBER_SCALE},"
      f" {sum(len(aspects) for aspects in ASPECTS_IN)} writes over {len(GANTRY)} settings"
      f" where a lane at a time would be {len(GANTRY) * len(screens)}")


def fill_frame(face, outer, inner):
    """Fill the band between two rectangles, in four pieces, leaving the inner one untouched.

    Every opaque part of the mask goes on this way so that nothing is ever painted across the matrix.
    Drawing composites, so a transparent pen cannot take an opaque ground back to clear: an aperture
    covered once stays covered.
    """
    face.rectangle(rect(outer.x, outer.y, outer.w, inner.y - outer.y))
    face.rectangle(rect(outer.x, inner.y + inner.h, outer.w, outer.y + outer.h - inner.y - inner.h))
    face.rectangle(rect(outer.x, inner.y, inner.x - outer.x, inner.h))
    face.rectangle(rect(inner.x + inner.w, inner.y, outer.x + outer.w - inner.x - inner.w, inner.h))


def bake_mask():
    """The signal's face, with an aperture over every lamp of the matrix and everything else opaque.

    Baked once, and shared by both lanes since every signal is the same shape. A lamp tile is blitted across
    a row and the row down the matrix, which is a few dozen blits, not one per lamp.
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
    """A mandatory speed limit: a ring of lamps with the number inside it.

    The ring is two filled circles, the inner one unlit, which is the cheapest annulus there is and needs
    nothing of how a stroke aligns.
    """
    middle = CELLS / 2
    lamps.pen = RED
    lamps.circle(middle, middle, RING_RADIUS)
    lamps.pen = UNLIT
    lamps.circle(middle, middle, RING_RADIUS - RING_LAMPS)

    lamps.pen = WHITE
    across, down = number_at(limit)
    lamps.text(f"{limit}", across, down, NUMBER_SCALE)


def lamp_stroke(from_x, from_y, to_x, to_y, weight, across, carry=(0, 0)):
    """Light a stroke of whole lamps between two lamps, square on or at 45 degrees, a row at a time.

    A 45 degree vector stroke lights an even count of lamps along a row whatever its thickness, and an
    even count cannot sit symmetrically on a matrix whose middle is a lamp, so the rasteriser cannot
    place these.

    `weight` is the count across a stroke running square on and `across` the count along a row at 45
    degrees, the same visual weight. `carry` moves each end along the stroke, out being positive, which
    is how two barbs come to a point of their own.
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
    """The national speed limit: a white disc with a band across it, low on the left to high on the right.

    The band is unlit lamps, a sign's black stripe on a lamp matrix being where the lamps are off.
    The line runs past the disc on both sides, so it cuts clean to the edge at either end.
    """
    lamps.pen = WHITE
    lamps.circle(CELLS / 2, CELLS / 2, RING_RADIUS)

    # Past the disc at both ends, so the band cuts clean to its edge and does not stop inside it
    lamps.pen = UNLIT
    over = RING_RADIUS + 1
    lamp_stroke(MIDDLE - over, MIDDLE + over, MIDDLE + over, MIDDLE - over,
                round(BAND_ACROSS / 2 ** 0.5) | 1, BAND_ACROSS)


def draw_closed():
    """A closed lane: a red cross of four strokes, each running in to the middle from its own tip.

    An arm to a corner rather than two strokes through the middle, so every tip is the start of a stroke and
    can be pulled in to a single lamp. The four square cut inner ends overlap and fill the middle.
    """
    lamps.pen = RED
    for corner_x, corner_y in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        lamp_stroke(MIDDLE + corner_x * CROSS_ARM, MIDDLE + corner_y * CROSS_ARM, MIDDLE, MIDDLE,
                    STROKE, ACROSS, (-1, 0))


def draw_arrow(towards):
    """The arrow: straight down for a lane open, and turned to point into the lane to either side of it.

    `towards` is -1, 0 or 1. A lane open is green straight down and a lane change is white turned across,
    as a real gantry pairs them. The shaft stops short of the barbs, which meet in a point of their own.
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
    # in four: only the start of a stroke can be pulled in to a tip of one lamp
    trim = (-1, 0) if point[0] and point[1] else (0, 0)
    for reach, way in ((from_here, -1), (to_there, 1)):
        lamp_stroke(MIDDLE + way * point[0] * reach, MIDDLE + way * point[1] * reach,
                    MIDDLE, MIDDLE, STROKE, ACROSS, trim)


def draw_signal(aspect, on_the_left):
    """One signal on the canvas: its aspect on the matrix, the mask over it, then the corner lamps."""
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

    # Over the mask, not through it: a corner lamp is bolted to the face and is no part of the matrix. They
    # flash for a closed lane and nothing else, and sit unlit under a speed limit or an arrow. The first two
    # are the left pair, so the index says which side one is on
    flashing = aspect is not None and aspect[0] == "closed"
    for index, lamp in enumerate(CORNER_LAMPS):
        canvas.pen = RED if flashing and (index < 2) == on_the_left else CORNER_OFF
        canvas.shape(lamp)


def send(setting, on_the_left):
    """One setting to the gantry, an aspect at a time, each streamed to every lane showing it.

    That is what a group is for: `to` names the lanes a frame reaches, so the ones sharing an aspect are
    written together on one frame, and a setting costs a write per distinct aspect, not per lane. A
    gantry showing one limit across four lanes is a single write.
    """
    for aspect in ASPECTS_IN[setting]:
        draw_signal(aspect, on_the_left)
        gantry.update(canvas, rotation=ROTATION,
                      to=tuple(screen for screen, showing in zip(screens, GANTRY[setting])
                               if showing == aspect))


started = time.ticks_ms()
shown = None

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = time.ticks_diff(time.ticks_ms(), started)
        frame = (int(elapsed / (HOLD * 1000)) % len(GANTRY), bool(elapsed // FLASH_MS % 2))

        # Nothing moves on a gantry, so it is only drawn again when the setting or the lamps change
        if frame != shown:
            send(*frame)
            shown = frame

        time.sleep_ms(20)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
