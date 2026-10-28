from picovector import color, font, image, rect, shape

"""
Drawing: Lane control signal
One lane of a motorway lane control gantry, working through a lane closure.
Section: Transport signs
"""

# Entry: screenA: graphics file=lane_control_gantry.py fps=50   (a 2.8" screen)

# Constants for drawing
LANE = 0                            # Which lane of the gantry this signal is, 0 being the left and the busiest

LAMP = 6
APERTURE = 0.7
SOFTEN = 1.0
CORNER_AIR = 3

HOUSING = color.black
FACE = color.rgb(17, 17, 17)
KEYLINE = color.rgb(51, 51, 51)
UNLIT = color.rgb(34, 34, 34)
RED = color.rgb(255, 34, 34)
WHITE = color.rgb(238, 238, 238)
GREEN = color.rgb(0, 221, 170)
CORNER_OFF = color.rgb(51, 17, 17)

RING_RADIUS = 14
RING_LAMPS = 3
STROKE = 5
ACROSS = 7
BAND_ACROSS = 9
CROSS_ARM = 10
NUMBER_FONT = font.manticore
HOLD_MS = 5000
FLASH_MS = 500

BLANK = None
OPEN = ("arrow", 0)
KEEP_RIGHT = ("arrow", 1)
KEEP_LEFT = ("arrow", -1)
SHUT = ("closed", 0)
NATIONAL = ("national", 0)
FORTY = ("speed", 40)
SIXTY = ("speed", 60)

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

# The canvas this drawing expects, a 2.8" screen at rotation 0, stated as the mask is baked
# before the first call
WIDTH, HEIGHT = 240, 320

SIGNAL = min(WIDTH, HEIGHT)
SIGNAL_X = (WIDTH - SIGNAL) // 2
SIGNAL_Y = (HEIGHT - SIGNAL) // 2

CELLS = RING_RADIUS * 2 + 1
MIDDLE = RING_RADIUS
SIDE = CELLS * LAMP
MATRIX_X = SIGNAL_X + (SIGNAL - SIDE) // 2
MATRIX_Y = SIGNAL_Y + (SIGNAL - SIDE) // 2

INSET = (SIGNAL - SIDE) // 2
CORNER_AT = int(INSET / (1 + 2 ** -0.5))
CORNER_R = CORNER_AT - CORNER_AIR

lamps = image(CELLS, CELLS)
lamps.font = NUMBER_FONT

scratch = image(CELLS, CELLS)
scratch.font = NUMBER_FONT


def lettering_box(text, scale):
    """Measure where a string's lettering lands drawn at the origin, as (left, top, right, bottom) in lamps."""
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


LETTERING_TOP, LETTERING_BOTTOM = CELLS, -1
for digit in "0123456789":
    _, digit_top, _, digit_bottom = lettering_box(digit, 1)
    LETTERING_TOP = min(LETTERING_TOP, digit_top)
    LETTERING_BOTTOM = max(LETTERING_BOTTOM, digit_bottom)

# Every speed limit the whole gantry shows, so this lane's numbers size as they would beside the rest
SPEEDS = {aspect[1] for setting in GANTRY for aspect in setting
          if aspect is not None and aspect[0] == "speed"}


def number_scale():
    """The largest whole step whose digits fit inside the ring."""
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

ARROWS = {-1: ((-1, 1), ((0, -1), (1, 0)), 11, 16, 10, 2),
          0: ((0, 1), ((-1, -1), (1, -1)), 11, 10, 14, 1),
          1: ((1, 1), ((0, -1), (-1, 0)), 11, 16, 10, 2)}

FAR = SIGNAL - CORNER_AT
CORNER_LAMPS = tuple(shape.circle(SIGNAL_X + x, SIGNAL_Y + y, CORNER_R)
                     for x, y in ((CORNER_AT, CORNER_AT), (CORNER_AT, FAR), (FAR, CORNER_AT), (FAR, FAR)))

SCALE_FROM = rect(0, 0, CELLS, CELLS)
SCALE_TO = rect(MATRIX_X, MATRIX_Y, SIDE, SIDE)


def fill_frame(face, outer, inner):
    """Fill the band between two rectangles in four pieces, leaving the inner one untouched."""
    face.rectangle(rect(outer.x, outer.y, outer.w, inner.y - outer.y))
    face.rectangle(rect(outer.x, inner.y + inner.h, outer.w, outer.y + outer.h - inner.y - inner.h))
    face.rectangle(rect(outer.x, inner.y, inner.x - outer.x, inner.h))
    face.rectangle(rect(inner.x + inner.w, inner.y, outer.x + outer.w - inner.x - inner.w, inner.h))


def bake_mask():
    """Bake the signal's face, an aperture over every lamp and the rest opaque, a row of lamps at a time."""
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
    """Light a stroke of whole lamps between two lamps, square on or at 45 degrees, a row at a time."""
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
    """Draw the national speed limit, a white disc crossed by an unlit band."""
    lamps.pen = WHITE
    lamps.circle(CELLS / 2, CELLS / 2, RING_RADIUS)

    lamps.pen = UNLIT
    over = RING_RADIUS + 1
    lamp_stroke(MIDDLE - over, MIDDLE + over, MIDDLE + over, MIDDLE - over,
                round(BAND_ACROSS / 2 ** 0.5) | 1, BAND_ACROSS)


def draw_closed():
    """Draw a closed lane's red cross, four strokes run in from their tips."""
    lamps.pen = RED
    for corner_x, corner_y in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        lamp_stroke(MIDDLE + corner_x * CROSS_ARM, MIDDLE + corner_y * CROSS_ARM, MIDDLE, MIDDLE,
                    STROKE, ACROSS, (-1, 0))


def draw_arrow(towards):
    """Draw the arrow, green straight down for a lane open and white turned across for a lane change."""
    lamps.pen = GREEN if towards == 0 else WHITE
    point, barbs, at, back, from_here, to_there = ARROWS[towards]

    corner_x = MIDDLE + point[0] * at
    corner_y = MIDDLE + point[1] * at
    for barb in barbs:
        square = barb[0] == 0 or barb[1] == 0
        slip_x = -point[0] * (STROKE // 2) if barb[0] == 0 else 0
        slip_y = -point[1] * (STROKE // 2) if barb[1] == 0 else 0
        lamp_stroke(corner_x + slip_x, corner_y + slip_y,
                    corner_x + slip_x + barb[0] * back, corner_y + slip_y + barb[1] * back,
                    STROKE, ACROSS, (0, 0) if square else (ACROSS // 2, -1))

    trim = (-1, 0) if point[0] and point[1] else (0, 0)
    for reach, way in ((from_here, -1), (to_there, 1)):
        lamp_stroke(MIDDLE + way * point[0] * reach, MIDDLE + way * point[1] * reach,
                    MIDDLE, MIDDLE, STROKE, ACROSS, trim)


def signal(canvas, aspect, on_the_left):
    """Draw the signal on the canvas, its aspect on the matrix, the mask over it, then the corner lamps."""
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

    flashing = aspect is not None and aspect[0] == "closed"
    for index, lamp in enumerate(CORNER_LAMPS):
        canvas.pen = RED if flashing and (index < 2) == on_the_left else CORNER_OFF
        canvas.shape(lamp)


shown = None


def draw(canvas, elapsed):
    global shown
    if shown is None and (canvas.width, canvas.height) != (WIDTH, HEIGHT):
        raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                         f"rotation 0, and was given {canvas.width}x{canvas.height}")

    now = int(elapsed * 1000)
    aspect = GANTRY[now // HOLD_MS % len(GANTRY)][LANE]
    frame = (aspect, bool(now // FLASH_MS % 2))

    # The canvas keeps the signal, so it is only drawn again where the aspect or the flash changed
    if frame != shown:
        signal(canvas, *frame)
        shown = frame
