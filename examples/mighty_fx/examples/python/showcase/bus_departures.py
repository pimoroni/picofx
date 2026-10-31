from mighty_fx import MightyFX, SPCE
from timing import Pacer, Roller
from screens import Reserve, Screen280, ScreenPair
from picovector import color, font, image, rect, shape

"""
Draw a bus departure board on a television used for signage, antialiased vector type on a panel
that is plainly a panel. A second panel lengthens the board, with one listing across both.

Press "Boot" to exit the program.
"""

# Constants for drawing
BOARD_FONT = "/rom/fonts/Oswald.af"  # A condensed vector face, so a destination fits a narrow column
ANTIALIAS = image.X4                 # What smooths a vector face. OFF is the default, X2 the cheaper step
PORTRAIT = True                      # A television hung on its side, as signage often is, or the usual way up
# One panel of a pair is mounted turned round, so their narrowest bezels meet. 0 for SP/CE A, 1 for B, or None
TURNED = 0
TITLE = "Departures from here"
CLOCK_START = (8, 9)                 # The time the board counts on from, Mighty FX having no clock to read
CLOCK_RATE = 5                       # Board seconds to the real one, so the times move while you watch
PAGE_HOLD = 6.0                      # How long a page of the listing stands, in seconds
RELATIVE_UNDER = 30                  # Minutes. Nearer than this a tracked service counts down instead
LOOKAHEAD = 90                       # How far ahead the board lists, in minutes

# The screens drive the panel at 16 levels a channel, and these are whole steps of 17 so none shifts on the glass
HEADER = color.rgb(136, 17, 51)      # The band along the top, carrying the title, the time and the page
BODY = color.rgb(102, 0, 34)         # The listing's background
BAND = color.rgb(68, 0, 17)          # Every other row, which is what lets the eye follow one across
STRIP = color.rgb(255, 204, 102)     # The column headings sit on a pale strip, as printed ones do
STRIP_TEXT = color.rgb(68, 0, 17)
TEXT_COLOUR = color.white            # The listing itself
NOTE_TEXT = color.rgb(238, 187, 170)  # The note at the foot, set back from the listing
BADGE = color.rgb(255, 255, 238)     # The pale background an operator's mark sits on

# How tall the lettering comes out, in pixels, the face sized to reach each one
LETTER_H = 11                        # The listing
TITLE_H = 14                         # The board's name
STATUS_H = 10                        # The time and the page count
STRIP_H = 9                          # The column headings
NOTE_H = 9                           # The note at the foot

MARGIN = 4                           # Down either side of the board
PAD = 2                              # Around the lettering in a band, and inside a badge
ROW_PAD = 2                          # Over a row's lettering, so this is what sets it in its row
ROW_DROP = 4                         # And under it, which is also where a descender goes
GAP = 4                              # Between one column and the next
CORNER = 2                           # How far a badge's corners are rounded off
MARK_AIR = 1                         # Left inside a badge over its mark and under it
TITLE_GAP = 2                        # Between the board's name and the line under it
LIST_GAP = 6                         # Under the last row, so the note reads as a note and not a row
NOTE_SPACING = 1.15                  # Line spacing in the note, which is the only wrapped text here
REFERENCE = 64                       # The size the face is measured at, every other size scaling off it

# The operators, each a mark drawn from primitives in place of a logo, and its colour
OPERATORS = (("peak", color.rgb(0, 119, 187)),     # Hilltop
             ("ring", color.rgb(204, 51, 34)),     # Crosstown
             ("bars", color.rgb(0, 136, 68)))      # Riverside

# The timetable, each route, destination, stand, operator, headway in minutes, a minute one departure
# falls on, and whether tracked. The listing is calculated from it, so it never empties
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

# The note at the foot, one a page and the only text that wraps
NOTES = (("Stands A to E are on the near side of the road, past the taxi rank."
          " Please have your fare ready."),
         ("A time counting down is a tracked vehicle."
          " A time in full is as timetabled and may run early or late."))

# Create a MightyFX object with both SP/CE ports set up for screens
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A portrait television is drawn as the panel already is, and a landscape one turned a quarter onto it.
# Either way the board runs down the canvas, and a pair stacks its panels one above the other
ROTATION = 0 if PORTRAIT else 90

# A screen refuses to be created where no panel answers, so one panel runs the board and a second
# lengthens it. The reserve lets a pair convert from the heap
screens = []
for port in (mighty.spce_a, mighty.spce_b):
    try:
        screens.append(Screen280(port, reserve=Reserve.FULL_SIZE_IMAGES, rotation=ROTATION))
    except ValueError as e:
        print(e)

if not screens:
    mighty.shutdown()
    raise RuntimeError("No panels answered! Plug a screen into SP/CE A, and a second into SP/CE B for a board twice as long")

# A pair turns the page on both panels on one frame. Working out how takes a few seconds
pair = ScreenPair(*screens) if len(screens) == 2 else None

# Only a pair turns a panel round, half a turn on the one TURNED names
TURNS = tuple(screen.rotation + 180 * (port == TURNED) for port, screen in enumerate(screens))

# PANEL_ROWS is what one panel shows
PANEL_ROWS = screens[0].height if PORTRAIT else screens[0].width
WIDTH = screens[0].width if PORTRAIT else screens[0].height
HEIGHT = PANEL_ROWS * len(screens)
canvas = image(WIDTH, HEIGHT)

board_font = font.load(BOARD_FONT)
canvas.font = board_font
canvas.antialias = ANTIALIAS


def lettering_rows(size, letters):
    """Measure which rows these letters fill from y zero. A face's metrics are not where they land."""
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

# A rect one line tall, since text() clips to the rect it is given and lays out a second line inside
# a taller one. Two pixels over the em box is what a capital's overshoot needs
ROW_BOX = round(ROW_SIZE) + 2
STATUS_BOX = round(STATUS_SIZE) + 2

# The bands down the board, and what they leave the listing between them
BUS_H = TITLE_H                 # The bus beside the title, as tall as its lettering
BUS_W = round(TITLE_H * 1.4)    # And a little wider
HEADER_H = PAD + TITLE_H + TITLE_GAP + STATUS_H + PAD
STRIP_BAND = PAD + STRIP_H + PAD
NOTE_BOX = round(max(canvas.measure_text(note, rect(0, 0, WIDTH - MARGIN * 2, HEIGHT),
                                         font_size=NOTE_SIZE, line_height=NOTE_SPACING)[1]
                     for note in NOTES)) + 2
LIST_Y = HEADER_H + STRIP_BAND
LIST_END = HEIGHT - NOTE_BOX - LIST_GAP - MARGIN

# The listing is banded a panel at a time so no row straddles the join, the bezel gap falling between two
# banks of rows. Every band takes the same count at the same height
ROW_MIN = LETTER_H + ROW_PAD + ROW_DROP
edges = [LIST_Y] + [PANEL_ROWS * panel for panel in range(1, len(screens))] + [LIST_END]
BANDS = [(edges[at], edges[at + 1]) for at in range(len(edges) - 1)]
PER_BAND = min((end - start) // ROW_MIN for start, end in BANDS)

# The rows grown to fill their band, so no void collects above the note
ROW_H = min((end - start) // PER_BAND for start, end in BANDS)
ROW_TOPS = [start + index * ROW_H for start, _ in BANDS for index in range(PER_BAND)]
ROWS = len(ROW_TOPS)

# Anything still over is split above the note and under it, so what is left of it reads as a margin
FILLED = BANDS[-1][0] + PER_BAND * ROW_H
NOTE_Y = FILLED + LIST_GAP + (LIST_END - FILLED) // 2


def widest(strings, size):
    """How much width the longest of these needs at this size."""
    return max(canvas.measure_text(text, font_size=size)[0] for text in strings)


def column(strings, heading):
    """A column's width, measured from the widest thing in it or its heading."""
    return round(max(widest(strings, ROW_SIZE), widest((heading,), STRIP_SIZE)))


ROUTE_W = column([service[0] for service in SERVICES], "Service")
TIME_W = column(("00:00", f"{RELATIVE_UNDER} min"), "Time")
STAND_W = column([service[2] for service in SERVICES], "Stand")

# A badge is a pill sized to its mark, so the mark never sits adrift in a wide column
PILL_H = ROW_H - 2
MARK_CY = 1 + PILL_H / 2            # From a row's top, the pill being inset by one

# An antialiased edge draws half a pixel past a shape, so the mark is sized in by that and the air
MARK_R = PILL_H / 2 - MARK_AIR - 0.5
MARK_W = round(MARK_R * 2)

FIXED = MARGIN * 2 + ROUTE_W + TIME_W + STAND_W + GAP * 4
PILL_W = MARK_W + PAD * 2
BADGE_W = max(PILL_W, round(widest(("Operator",), STRIP_SIZE)))

# Whatever the fitted columns leave goes to the destination, being the one that can use it, and a
# name too long even for that is cut with an ellipsis as a real board's is
DEST_W = WIDTH - FIXED - BADGE_W
ROUTE_X = MARGIN
DEST_X = ROUTE_X + ROUTE_W + GAP
TIME_X = DEST_X + DEST_W + GAP
STAND_X = TIME_X + TIME_W + GAP
BADGE_X = STAND_X + STAND_W + GAP
PILL_X = BADGE_X + (BADGE_W - PILL_W) // 2   # A whole pixel, a pill on a half landing 1px narrower
MARK_X = PILL_X + PAD + MARK_R

print(f"Bus board on {len(screens)} of 2 SP/CE ports at {TURNS if pair else screens[0].rotation},"
      f" a {WIDTH}x{HEIGHT} canvas,"
      f" {ROWS} rows of {ROW_H}px asked {ROW_MIN} in {len(BANDS)} band(s),"
      f" lettering {LETTER_H}px at size {ROW_SIZE:.1f},"
      f" destination {DEST_W}px of {round(widest([service[1] for service in SERVICES], ROW_SIZE))} wanted")


def clock_text(minute):
    """A minute past midnight as a time, going round again after 23:59."""
    return f"{minute // 60 % 24:02d}:{minute % 60:02d}"


def board_minute(elapsed):
    """What the board's clock reads, counted on from CLOCK_START."""
    elapsed = elapsed * CLOCK_RATE // 60000
    return (CLOCK_START[0] * 60 + CLOCK_START[1] + elapsed) % 1440


def departures(now):
    """
    Every service's departures inside LOOKAHEAD, soonest first.

    Sorted as tuples, as MicroPython calls a key function per comparison.
    """
    due = []
    for route, place, stand, operator, headway, offset, tracked in SERVICES:
        # The first departure at or after now, from the minute the service falls on and its headway
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
    canvas.rectangle(rect(x + 2, y + 2, w - 4, body // 3))      # its windows
    canvas.circle(x + 3, y + body, 2)                           # and the arches over its wheels
    canvas.circle(x + w - 4, y + body, 2)
    canvas.pen = TEXT_COLOUR
    canvas.circle(x + 3, y + body, 1)
    canvas.circle(x + w - 4, y + body, 1)


def draw_mark(kind, mark, centre_y):
    """Draw one operator's mark, from primitives."""
    canvas.pen = mark
    if kind == "peak":
        # A filled triangle draws into the row under its base and the column right of its centre, where a
        # circle and a rectangle do neither, so it is drawn a pixel in on both to match the other marks
        peak_x = MARK_X - 1
        canvas.triangle(peak_x, centre_y - MARK_R, peak_x + MARK_R, centre_y + MARK_R - 1,
                        peak_x - MARK_R, centre_y + MARK_R - 1)
    elif kind == "bars":
        # Three bars centred on their own height and on whole rows,
        # as on half rows they thicken and their gaps close
        thick = round(MARK_R * 2 / 5)
        top = round(centre_y - (thick * 5 - 2) / 2)
        for step in range(3):
            canvas.rectangle(rect(MARK_X - MARK_R, top + step * (thick * 2 - 1), MARK_W, thick))
    else:
        # Stroked inwards, a stroke growing outwards from the radius by default and so overflowing
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

    # The operator's badge, a pale pill for the mark to sit on
    kind, mark = OPERATORS[operator]
    canvas.pen = BADGE
    canvas.shape(shape.rounded_rectangle(rect(PILL_X, y + 1, PILL_W, PILL_H), CORNER))
    draw_mark(kind, mark, y + MARK_CY)


def draw(number, now):
    """Draw the whole board, the header band, the column headings, a page of the listing and the note."""
    due = departures(now)
    pages = max(1, (len(due) + ROWS - 1) // ROWS)
    number %= pages

    canvas.pen = BODY
    canvas.clear()

    # The band along the top, saying what the listing is of
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

    # The column headings, on a pale strip as printed ones are
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


# The pacer is the board's clock and holds it to a look every 20ms. The roller turns the page
pacer = Pacer(0.02)
turn = Roller(PAGE_HOLD)
page = 0
shown = None

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if turn.is_due():
            page += 1
            turn.advance()

        # Nothing on the board moves, so it is only drawn again when the minute or the page changes
        now = board_minute(pacer.elapsed)
        frame = (now, page)
        if frame != shown:
            draw(page, now)
            if pair is None:
                screens[0].update(canvas)
            else:
                # One canvas reaches both panels, the second offset up by a panel to show the rest of the
                # board. That needs no second buffer, and holds whichever way a panel is turned
                pair.update(canvas, rotation=TURNS, offset=((0, 0), (0, -PANEL_ROWS)))
            shown = frame

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
