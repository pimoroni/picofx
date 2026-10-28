from picovector import color, font, image, rect, shape

"""
Drawing: Gantry ASPECT_NAME
One lane control signal showing ASPECT_NAME, for an effects file whose scenes set each lane.
Section: Transport signs
"""

# Entry: screenA: graphics file=gantry_ASPECT_FILE.py width=240 height=240 fps=20   (a 2.8" screen)

ASPECT = None                       # The sign shown, set per file

# Constants for drawing
LAMP = 6
APERTURE = 0.7
SOFTEN = 1.0
CORNER_AIR = 3

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
FLASH_MS = 500

# Every speed limit any sign of the set shows, so the numbers size alike on every lane
SPEEDS = (40, 60)

# The signal, square, the panel's housing round it coming from the entry's background
SIGNAL = 240

CELLS = RING_RADIUS * 2 + 1
MIDDLE = RING_RADIUS
SIDE = CELLS * LAMP
MATRIX_AT = (SIGNAL - SIDE) // 2

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


def number_scale():
    """The largest whole step whose digits fit inside the ring."""
    inner = RING_RADIUS - RING_LAMPS
    tall = LETTERING_BOTTOM - LETTERING_TOP + 1
    scale = 1
    while True:
        step = scale + 1
        wide = max(int(lamps.measure_text(f"{speed}", font_size=step)[0]) for speed in SPEEDS)
        if ((wide / 2) ** 2 + (tall * step / 2) ** 2) ** 0.5 > inner:
            return scale
        scale = step


NUMBER_SCALE = number_scale()
if ASPECT is not None and ASPECT[0] == "speed":
    left, top, right, bottom = lettering_box(f"{ASPECT[1]}", NUMBER_SCALE)
    NUMBER_AT = (round((CELLS - 1 - left - right) / 2), round((CELLS - 1 - top - bottom) / 2))

ARROWS = {-1: ((-1, 1), ((0, -1), (1, 0)), 11, 16, 10, 2),
          0: ((0, 1), ((-1, -1), (1, -1)), 11, 10, 14, 1),
          1: ((1, 1), ((0, -1), (-1, 0)), 11, 16, 10, 2)}

FAR = SIGNAL - CORNER_AT
CORNER_LAMPS = tuple(shape.circle(x, y, CORNER_R)
                     for x, y in ((CORNER_AT, CORNER_AT), (CORNER_AT, FAR), (FAR, CORNER_AT), (FAR, FAR)))

SCALE_FROM = rect(0, 0, CELLS, CELLS)
SCALE_TO = rect(MATRIX_AT, MATRIX_AT, SIDE, SIDE)


def bake_mask():
    """Bake the matrix's face, an aperture over every lamp and the rest opaque, a row of lamps at a time."""
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

    face = image(SIDE, SIDE)
    face.pen = color.transparent
    face.clear()
    row = image(SIDE, LAMP)
    row.pen = color.transparent
    row.clear()
    for cell in range(CELLS):
        row.blit(tile, cell * LAMP, 0)
    for cell in range(CELLS):
        face.blit(row, 0, cell * LAMP)
    return face


mask = bake_mask()


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


def light_aspect():
    """Light the aspect on the matrix, one pixel to a lamp."""
    lamps.pen = UNLIT
    lamps.clear()
    if ASPECT is None:
        return

    kind, value = ASPECT
    if kind == "speed":
        lamps.pen = RED
        lamps.circle(CELLS / 2, CELLS / 2, RING_RADIUS)
        lamps.pen = UNLIT
        lamps.circle(CELLS / 2, CELLS / 2, RING_RADIUS - RING_LAMPS)
        lamps.pen = WHITE
        lamps.text(f"{value}", NUMBER_AT[0], NUMBER_AT[1], NUMBER_SCALE)
    elif kind == "national":
        lamps.pen = WHITE
        lamps.circle(CELLS / 2, CELLS / 2, RING_RADIUS)
        lamps.pen = UNLIT
        over = RING_RADIUS + 1
        lamp_stroke(MIDDLE - over, MIDDLE + over, MIDDLE + over, MIDDLE - over,
                    round(BAND_ACROSS / 2 ** 0.5) | 1, BAND_ACROSS)
    elif kind == "closed":
        lamps.pen = RED
        for corner_x, corner_y in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            lamp_stroke(MIDDLE + corner_x * CROSS_ARM, MIDDLE + corner_y * CROSS_ARM, MIDDLE, MIDDLE,
                        STROKE, ACROSS, (-1, 0))
    else:
        lamps.pen = GREEN if value == 0 else WHITE
        point, barbs, at, back, from_here, to_there = ARROWS[value]
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


FLASHES = ASPECT is not None and ASPECT[0] == "closed"
shown = None


def corners(canvas, on_the_left):
    """Draw the corner lamps, a closed lane's pairs flashing in turn."""
    for index, lamp in enumerate(CORNER_LAMPS):
        canvas.pen = RED if FLASHES and (index < 2) == on_the_left else CORNER_OFF
        canvas.shape(lamp)


def draw(canvas, elapsed):
    global shown
    if shown is None:
        if (canvas.width, canvas.height) != (SIGNAL, SIGNAL):
            raise ValueError(f"this drawing needs width={SIGNAL} height={SIGNAL} on its entry, "
                             f"and was given {canvas.width}x{canvas.height}")
        # The face, its keyline and the lit matrix, which never change
        canvas.pen = KEYLINE
        canvas.clear()
        canvas.pen = FACE
        canvas.rectangle(rect(1, 1, SIGNAL - 2, SIGNAL - 2))
        light_aspect()
        canvas.blit(lamps, SCALE_FROM, SCALE_TO, image.NEAREST)
        canvas.blit(mask, MATRIX_AT, MATRIX_AT)
        corners(canvas, False)
        shown = False

    # Only a closed lane changes once drawn, its corner pairs taking turns
    if FLASHES:
        on_the_left = bool(int(elapsed * 1000) // FLASH_MS % 2)
        if on_the_left != shown:
            corners(canvas, on_the_left)
            shown = on_the_left
