from picovector import color, font, image, rect, shape

"""
Drawing: Split-flap clock
A split-flap clock, its digits climbing through the drum a flap at a time like a real board.
Section: Mechanical and glowing displays
"""

# Entry: screenA rotation=90: graphics file=split_flap_clock.py fps=50   (a 2.8" screen)

# Constants for drawing
FLAP_FONT = "/rom/fonts/AdventPro-Medium.af"  # A vector face, so it sizes to the card
DRUM = " 0123456789"                    # What is on a card, in the order it comes round
CLOCK_START = (11, 32, 45)              # The time it counts on from, Mighty FX having no clock to read
FLAP_MS = 260                           # How long one card takes to fall

CARD = color.rgb(34, 34, 38)
SHADOW = color.rgb(17, 17, 19)
HOUSING = color.rgb(17, 17, 19)
KEYLINE = color.rgb(51, 51, 56)
HIGHLIGHT = color.rgb(85, 85, 92)
TEXT_COLOUR = color.rgb(238, 238, 232)
SPLIT = color.rgb(8, 8, 9)
BOARD = color.black
GAP = 4
SPLIT_H = 2
EDGE = 3
CORNER = 6
SHADOW_H = 3
BEZEL = 8
MARGIN = 6
SEPARATOR = 14
ANTIALIAS = image.X2
CELL_H = 96

# The canvas this drawing expects, a 2.8" screen at rotation=90. The module body cannot see
# the canvas, and the layout below is built from it, so it is stated and checked on the first call
WIDTH, HEIGHT = 320, 240

FLAPS = 6
CELL_W = (WIDTH - MARGIN * 2 - SEPARATOR * 2 - GAP * (FLAPS + 1)) // FLAPS
TOP = (HEIGHT - CELL_H) // 2
HALF = CELL_H // 2

flap_font = font.load(FLAP_FONT)


def lettering_extent(size):
    """Measure which rows a digit fills at this size, font_size being the em height."""
    tall = round(size) * 2
    probe = image(CELL_W * 2, tall)
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = flap_font
    probe.antialias = ANTIALIAS
    probe.text("8", rect(0, 0, CELL_W * 2, tall), font_size=size)

    raw, stride = probe.raw, probe.stride
    drawn = [y for y in range(tall)
             if any(raw[y * stride + x * 4] > 60 for x in range(CELL_W * 2))]
    return (drawn[0], drawn[-1]) if drawn else None


def card_size():
    """Find the largest lettering a card can carry, sized on what it draws."""
    ruler = image(8, 8)
    ruler.font = flap_font
    probe = 48
    per_pixel = max(ruler.measure_text(letter, font_size=probe)[0] for letter in DRUM) / probe
    extent = lettering_extent(probe)
    if extent is None:
        return probe
    lettering_per_pixel = (extent[1] - extent[0] + 1) / probe
    return min((CELL_H - SPLIT_H * 2) / lettering_per_pixel, (CELL_W - GAP * 2) / per_pixel)


def lettering_top(size):
    """Find where to draw the lettering so it centres on a card, not its em box."""
    extent = lettering_extent(size)
    if extent is None:
        return round((CELL_H - size) / 2)
    return (CELL_H - (extent[1] - extent[0] + 1)) // 2 - extent[0]


SIZE = card_size()
LETTERING_TOP = lettering_top(SIZE)
EM_BOX = round(SIZE) + 2

# Every character of the drum drawn once to a card of its own, so a flap is a blit
drum = image(CELL_W * len(DRUM), CELL_H)
drum.pen = SPLIT
drum.clear()
drum.font = flap_font
drum.antialias = ANTIALIAS

for index, letter in enumerate(DRUM):
    left = index * CELL_W
    drum.pen = CARD
    drum.shape(shape.rounded_rectangle(rect(left, 0, CELL_W, HALF - SPLIT_H // 2),
                                       CORNER, CORNER, 0, 0))
    drum.shape(shape.rounded_rectangle(rect(left, HALF + SPLIT_H - SPLIT_H // 2,
                                            CELL_W, HALF - SPLIT_H), 0, 0, CORNER, CORNER))
    drum.pen = SHADOW
    drum.rectangle(rect(left, 0, CELL_W, SHADOW_H))
    drum.rectangle(rect(left, HALF + SPLIT_H - SPLIT_H // 2, CELL_W, SHADOW_H))

    wide = drum.measure_text(letter, font_size=SIZE)[0]
    drum.pen = TEXT_COLOUR
    drum.text(letter, rect(left + round((CELL_W - wide) / 2), LETTERING_TOP, CELL_W, EM_BOX),
              font_size=SIZE)

places = []
at = MARGIN + GAP
for position in range(FLAPS):
    places.append(at)
    at += CELL_W + GAP
    if position % 2 == 1 and position < FLAPS - 1:
        at += SEPARATOR

source = rect(0, 0, CELL_W, HALF)
target = rect(0, 0, CELL_W, HALF)


def half_of(index, lower):
    """The upper or lower half of one drum card, as a source rect."""
    source.x = index * CELL_W
    source.y = HALF if lower else 0
    return source


def settled(canvas, flap, index):
    """A card at rest, both halves showing the same character."""
    target.x, target.w = places[flap], CELL_W
    for lower in (False, True):
        target.y, target.h = TOP + (HALF if lower else 0), HALF
        canvas.blit(drum, half_of(index, lower), target)


def falling(canvas, flap, from_index, to_index, part):
    """Draw a card part way down."""
    target.x, target.w = places[flap], CELL_W
    target.y, target.h = TOP, HALF
    canvas.blit(drum, half_of(to_index, False), target)

    if part < 0.5:
        showing, above, index = round(HALF * (1 - part * 2)), True, from_index
    else:
        showing, above, index = round(HALF * (part - 0.5) * 2), False, to_index

    if showing <= 0:
        return

    target.y = TOP + HALF - showing if above else TOP + HALF
    target.h = showing

    if showing <= EDGE:
        canvas.pen = SPLIT
        canvas.rectangle(target)
    else:
        canvas.blit(drum, half_of(index, not above), target)


def clock_now(elapsed_ms):
    """The time the board is showing, counted on from CLOCK_START."""
    hours, minutes, seconds = CLOCK_START
    total = (hours * 3600 + minutes * 60 + seconds + int(elapsed_ms // 1000)) % 86400
    return f"{total // 3600:02d}{total // 60 % 60:02d}{total % 60:02d}"


def board(canvas):
    """Draw the case, blank cards and colons, which a falling card never writes over."""
    if (canvas.width, canvas.height) != (WIDTH, HEIGHT):
        raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                         f"rotation=90, and was given {canvas.width}x{canvas.height}")

    canvas.pen = BOARD
    canvas.clear()

    case = rect(places[0] - BEZEL, TOP - BEZEL,
                places[-1] + CELL_W + BEZEL - (places[0] - BEZEL), CELL_H + BEZEL * 2)
    canvas.pen = KEYLINE
    canvas.shape(shape.rounded_rectangle(case, CORNER, CORNER, CORNER, CORNER))
    canvas.pen = HOUSING
    canvas.shape(shape.rounded_rectangle(rect(case.x + 1, case.y + 1, case.w - 2, case.h - 2),
                                         CORNER, CORNER, CORNER, CORNER))
    canvas.pen = HIGHLIGHT
    canvas.rectangle(rect(case.x + CORNER, case.y, case.w - CORNER * 2, 1))
    canvas.pen = BOARD
    canvas.rectangle(rect(case.x + CORNER, case.y + case.h - 1, case.w - CORNER * 2, 1))

    for flap in range(FLAPS):
        settled(canvas, flap, 0)

    canvas.pen = TEXT_COLOUR
    for position in (1, 3):
        middle = places[position] + CELL_W + GAP + SEPARATOR // 2
        for y in (TOP + HALF // 2, TOP + HALF + HALF // 2):
            canvas.rectangle(rect(middle - 2, y - 2, 4, 4))


showing = [0] * FLAPS               # Where each card is in the drum, blank to begin with
wanted = [0] * FLAPS
turning = [None] * FLAPS            # When the card at this place started falling, in elapsed ms
started = False


def draw(canvas, elapsed):
    global started
    if not started:
        board(canvas)
        started = True

    now = elapsed * 1000
    reading = clock_now(now)

    for flap in range(FLAPS):
        wanted[flap] = DRUM.index(reading[flap])

    for flap in range(FLAPS):
        if turning[flap] is None:
            if showing[flap] != wanted[flap]:
                turning[flap] = now
            continue

        part = min(1.0, (now - turning[flap]) / FLAP_MS)
        step = (showing[flap] + 1) % len(DRUM)
        falling(canvas, flap, showing[flap], step, part)

        if part >= 1.0:
            showing[flap] = step
            settled(canvas, flap, step)
            turning[flap] = now if showing[flap] != wanted[flap] else None
