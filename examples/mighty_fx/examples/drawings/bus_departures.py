from picovector import color, font, image, rect, shape

"""
Drawing: Bus departures
A bus departure board on a television used for signage, antialiased vector type on a panel.
Section: Transport signs
"""

# Entry: screenA: graphics file=bus_departures.py fps=50   (a 2.8" screen)

# Constants for drawing
BOARD_FONT = "/rom/fonts/Oswald.af"
ANTIALIAS = image.X4
TITLE = "Departures from here"
CLOCK_START = (8, 9)
CLOCK_RATE = 5
PAGE_HOLD_MS = 6000
RELATIVE_UNDER = 30
LOOKAHEAD = 90

HEADER = color.rgb(136, 17, 51)
BODY = color.rgb(102, 0, 34)
BAND = color.rgb(68, 0, 17)
STRIP = color.rgb(255, 204, 102)
STRIP_TEXT = color.rgb(68, 0, 17)
TEXT_COLOUR = color.white
NOTE_TEXT = color.rgb(238, 187, 170)
BADGE = color.rgb(255, 255, 238)

LETTER_H = 11
TITLE_H = 14
STATUS_H = 10
STRIP_H = 9
NOTE_H = 9

MARGIN = 4
PAD = 2
ROW_PAD = 2
ROW_DROP = 4
GAP = 4
CORNER = 2
MARK_AIR = 1
TITLE_GAP = 2
LIST_GAP = 6
NOTE_SPACING = 1.15
REFERENCE = 64

OPERATORS = (("peak", color.rgb(0, 119, 187)),
             ("ring", color.rgb(204, 51, 34)),
             ("bars", color.rgb(0, 136, 68)))

SERVICES = (
    ("23", "Hillsborough", "A", 1, 10, 4, True),
    ("19", "Ecclesall", "B", 1, 12, 7, True),
    ("27", "Meadowhall", "C", 2, 15, 2, True),
    ("36", "Crookes", "D", 1, 20, 11, True),
    ("58", "Chesterfield", "E", 2, 20, 9, False),
    ("311", "Hathersage", "F", 0, 60, 35, False),
    ("314", "Castleton", "G", 0, 60, 50, False),
    ("316", "Bakewell", "H", 0, 60, 10, False),
    ("318", "Matlock", "J", 0, 60, 25, False),
    ("321", "Buxton", "K", 0, 90, 40, False),
    ("324", "Chatsworth", "L", 2, 60, 15, False),
)

NOTES = (("Stands A to E are on the near side of the road, past the taxi rank."
          " Please have your fare ready."),
         ("A time counting down is a tracked vehicle."
          " A time in full is as timetabled and may run early or late."))

# The canvas this drawing expects, a portrait 2.8" screen at rotation 0. The layout is measured
# before the first call, so it is stated and checked then
WIDTH, HEIGHT = 240, 320

board_font = font.load(BOARD_FONT)

# The layout is measured here, before any canvas exists, so a small image carries the face
ruler = image(8, 8)
ruler.font = board_font
ruler.antialias = ANTIALIAS


def lettering_rows(size, letters):
    """Measure which rows these letters fill from y zero."""
    tall = round(size) * 3
    probe = image(round(size) * 2, tall)
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = board_font
    probe.antialias = ANTIALIAS
    for letter in letters:
        probe.text(letter, rect(0, 0, probe.width, tall), font_size=size)

    raw, stride = probe.raw, probe.stride
    drawn = [y for y in range(tall)
             if any(raw[y * stride + x * 4] > 60 for x in range(probe.width))]
    return drawn[0], drawn[-1]


REACH = lettering_rows(REFERENCE, "HW8O")
LETTERING_PER_PX = (REACH[1] - REACH[0] + 1) / REFERENCE


def sized(letter_h):
    """A font size whose lettering reaches this height, and the lift that puts a capital's top on the mark."""
    size = letter_h / LETTERING_PER_PX
    return size, -lettering_rows(size, "HW8O")[0]


ROW_SIZE, ROW_LIFT = sized(LETTER_H)
TITLE_SIZE, TITLE_LIFT = sized(TITLE_H)
STATUS_SIZE, STATUS_LIFT = sized(STATUS_H)
STRIP_SIZE, STRIP_LIFT = sized(STRIP_H)
NOTE_SIZE = NOTE_H / LETTERING_PER_PX

ROW_BOX = round(ROW_SIZE) + 2
STATUS_BOX = round(STATUS_SIZE) + 2

BUS_H = TITLE_H
BUS_W = round(TITLE_H * 1.4)
HEADER_H = PAD + TITLE_H + TITLE_GAP + STATUS_H + PAD
STRIP_BAND = PAD + STRIP_H + PAD
NOTE_BOX = round(max(ruler.measure_text(note, rect(0, 0, WIDTH - MARGIN * 2, HEIGHT),
                                        font_size=NOTE_SIZE, line_height=NOTE_SPACING)[1]
                     for note in NOTES)) + 2
LIST_Y = HEADER_H + STRIP_BAND
LIST_END = HEIGHT - NOTE_BOX - LIST_GAP - MARGIN

# One panel, so one band of rows
ROW_MIN = LETTER_H + ROW_PAD + ROW_DROP
PER_BAND = (LIST_END - LIST_Y) // ROW_MIN
ROW_H = (LIST_END - LIST_Y) // PER_BAND
ROW_TOPS = [LIST_Y + index * ROW_H for index in range(PER_BAND)]
ROWS = len(ROW_TOPS)

FILLED = LIST_Y + PER_BAND * ROW_H
NOTE_Y = FILLED + LIST_GAP + (LIST_END - FILLED) // 2


def widest(strings, size):
    """How much width the longest of these needs at this size."""
    return max(ruler.measure_text(text, font_size=size)[0] for text in strings)


def column(strings, heading):
    """A column's width, measured from the widest thing in it or its heading."""
    return round(max(widest(strings, ROW_SIZE), widest((heading,), STRIP_SIZE)))


ROUTE_W = column([service[0] for service in SERVICES], "Service")
TIME_W = column(("00:00", f"{RELATIVE_UNDER} min"), "Time")
STAND_W = column([service[2] for service in SERVICES], "Stand")

PILL_H = ROW_H - 2
MARK_CY = 1 + PILL_H / 2
MARK_R = PILL_H / 2 - MARK_AIR - 0.5
MARK_W = round(MARK_R * 2)

FIXED = MARGIN * 2 + ROUTE_W + TIME_W + STAND_W + GAP * 4
PILL_W = MARK_W + PAD * 2
BADGE_W = max(PILL_W, round(widest(("Operator",), STRIP_SIZE)))

DEST_W = WIDTH - FIXED - BADGE_W
ROUTE_X = MARGIN
DEST_X = ROUTE_X + ROUTE_W + GAP
TIME_X = DEST_X + DEST_W + GAP
STAND_X = TIME_X + TIME_W + GAP
BADGE_X = STAND_X + STAND_W + GAP
PILL_X = BADGE_X + (BADGE_W - PILL_W) // 2
MARK_X = PILL_X + PAD + MARK_R


# The canvas the helpers below draw into, the one handed to draw() and kept for the whole run
canvas = None


def clock_text(minute):
    """A minute past midnight as a time, going round again after 23:59."""
    return f"{minute // 60 % 24:02d}:{minute % 60:02d}"


def board_minute(elapsed_ms):
    """What the board's clock reads, counted on from CLOCK_START."""
    elapsed = int(elapsed_ms) * CLOCK_RATE // 60000
    return (CLOCK_START[0] * 60 + CLOCK_START[1] + elapsed) % 1440


def departures(now):
    """Every service's departures inside LOOKAHEAD, soonest first."""
    due = []
    for route, place, stand, operator, headway, offset, tracked in SERVICES:
        when = now + (offset - now) % headway
        while when - now <= LOOKAHEAD:
            due.append((when, route, place, stand, operator, tracked))
            when += headway

    due.sort()
    return due


def when_text(when, now, tracked):
    """A service's time column, a countdown once a tracked vehicle is close and the timetable otherwise."""
    away = when - now
    if not tracked or away > RELATIVE_UNDER:
        return clock_text(when)

    return "Due" if away < 1 else f"{away} min"


def draw_bus(x, y, w, h):
    """Draw a bus pictogram beside the title, from shapes."""
    body = h - 2
    canvas.pen = TEXT_COLOUR
    canvas.shape(shape.rounded_rectangle(rect(x, y, w, body), CORNER))
    canvas.pen = HEADER
    canvas.rectangle(rect(x + 2, y + 2, w - 4, body // 3))
    canvas.circle(x + 3, y + body, 2)
    canvas.circle(x + w - 4, y + body, 2)
    canvas.pen = TEXT_COLOUR
    canvas.circle(x + 3, y + body, 1)
    canvas.circle(x + w - 4, y + body, 1)


def draw_mark(kind, mark, centre_y):
    """Draw one operator's mark, from primitives."""
    canvas.pen = mark
    if kind == "peak":
        peak_x = MARK_X - 1
        canvas.triangle(peak_x, centre_y - MARK_R, peak_x + MARK_R, centre_y + MARK_R - 1,
                        peak_x - MARK_R, centre_y + MARK_R - 1)
    elif kind == "bars":
        thick = round(MARK_R * 2 / 5)
        top = round(centre_y - (thick * 5 - 2) / 2)
        for step in range(3):
            canvas.rectangle(rect(MARK_X - MARK_R, top + step * (thick * 2 - 1), MARK_W, thick))
    else:
        canvas.shape(shape.circle(MARK_X, centre_y, MARK_R).stroke(2, shape.ALIGN_INNER))


def draw_row(index, entry, now):
    """Draw one service on its own row, banded against the one above it."""
    when, route, place, stand, operator, tracked = entry
    y = ROW_TOPS[index]
    if index % 2:
        canvas.pen = BAND
        canvas.rectangle(rect(0, y, WIDTH, ROW_H))

    lettering_y = y + ROW_PAD + ROW_LIFT
    canvas.pen = TEXT_COLOUR
    canvas.text(route, ROUTE_X, lettering_y, font_size=ROW_SIZE)
    canvas.text(place, rect(DEST_X, lettering_y, DEST_W, ROW_BOX), font_size=ROW_SIZE,
                overflow=image.ELLIPSES)
    canvas.text(when_text(when, now, tracked), TIME_X, lettering_y, font_size=ROW_SIZE)
    canvas.text(stand, STAND_X, lettering_y, font_size=ROW_SIZE)

    kind, mark = OPERATORS[operator]
    canvas.pen = BADGE
    canvas.shape(shape.rounded_rectangle(rect(PILL_X, y + 1, PILL_W, PILL_H), CORNER))
    draw_mark(kind, mark, y + MARK_CY)


def board(number, now):
    """Draw the whole board, the header band, the column headings, a page of the listing and the note."""
    due = departures(now)
    pages = max(1, (len(due) + ROWS - 1) // ROWS)
    number %= pages

    canvas.pen = BODY
    canvas.clear()

    canvas.pen = HEADER
    canvas.rectangle(rect(0, 0, WIDTH, HEADER_H))
    draw_bus(MARGIN, PAD, BUS_W, BUS_H)
    canvas.pen = TEXT_COLOUR
    canvas.text(TITLE, MARGIN + BUS_W + GAP, PAD + TITLE_LIFT, font_size=TITLE_SIZE)

    status_y = PAD + TITLE_H + TITLE_GAP + STATUS_LIFT
    canvas.text(f"Time now: {clock_text(now)}", MARGIN, status_y, font_size=STATUS_SIZE)
    canvas.text(f"Page {number + 1} of {pages}",
                rect(MARGIN, status_y, WIDTH - MARGIN * 2, STATUS_BOX),
                font_size=STATUS_SIZE, align=(image.RIGHT, image.TOP))

    canvas.pen = STRIP
    canvas.rectangle(rect(0, HEADER_H, WIDTH, STRIP_BAND))
    canvas.pen = STRIP_TEXT
    lettering_y = HEADER_H + PAD + STRIP_LIFT
    for heading, x in (("Service", ROUTE_X), ("Destination", DEST_X), ("Time", TIME_X),
                       ("Stand", STAND_X), ("Operator", BADGE_X)):
        canvas.text(heading, x, lettering_y, font_size=STRIP_SIZE)

    for index, entry in enumerate(due[number * ROWS:(number + 1) * ROWS]):
        draw_row(index, entry, now)

    canvas.pen = NOTE_TEXT
    canvas.text(NOTES[number % len(NOTES)], rect(MARGIN, NOTE_Y, WIDTH - MARGIN * 2, NOTE_BOX),
                font_size=NOTE_SIZE, line_height=NOTE_SPACING)


shown = None


def draw(given, elapsed):
    global canvas, shown
    if canvas is None:
        if (given.width, given.height) != (WIDTH, HEIGHT):
            raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                             f"rotation 0, and was given {given.width}x{given.height}")
        canvas = given
        canvas.font = board_font
        canvas.antialias = ANTIALIAS

    # The page turns every PAGE_HOLD_MS, and the board is only drawn again when it or the minute changes
    elapsed_ms = elapsed * 1000
    page = int(elapsed_ms // PAGE_HOLD_MS)
    now = board_minute(elapsed_ms)
    frame = (now, page)
    if frame != shown:
        board(page, now)
        shown = frame
