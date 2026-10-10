import time
from mighty_fx import MightyFX, SPCE
from screens import Reserve, Screen280, ScreenPair
from picovector import color, font, image, rect

"""
Draw a railway departures list on one screen, or spread across a pair with both panels
turning their page together.

Press "Boot" to exit the program.

Section: Transport signs
"""

# Constants for drawing
BOARD_FONT = "nope"                 # The listing's dot-matrix lettering. dir(font) lists all 37
PRINTED_HEADING = True              # Show the column headings printed on the board's face, or lit on a module
HEADING_FONT = "smart"              # What they are printed in, being lettering the board does not light
LARGE_FONT = "winds"                # The board's own lettering, at the top and the foot
AMBER = color.rgb(255, 176, 0)      # The colour of a lit lamp
HEADING = color.rgb(255, 240, 220)  # Printed lettering, which a real board sets apart from what it lights
MATRIX = color.rgb(20, 20, 16)      # The unlit face of a matrix module, against the black bars between them
LARGE_SCALE = 2                     # Pixel fonts scale by whole numbers, so 2 is double size
INSET = 6                           # How far in from the panel's left and right edges lettering starts
GAP = 8                             # The space between one column and the next
BAR = 3                             # The black bar between one module and the next, in pixels
PAD = 2                             # Space inside a module, above and below its lettering
PAGE_HOLD = 8.0                     # How long the board holds a page for, in seconds
HEADINGS_ROW = 1                    # Where the column headings sit in the stack of modules
FIRST_ROW = 2                       # And where the listing starts, the module below them
CLOCK_START = (14, 5, 0)            # The time the board counts on from, MightyFX having no clock to read

# The board's content, made up but for the stations. A service fills a row, and its via line and
# each line of its note fill one more each; a platform heading stands on its own. So an entry's
# height varies, which is what paging has to work out, and a note stays with the train it is about.
ENTRIES = (
    {"departs": "14:02", "destination": "Leeds", "platform": "4A", "status": "Exp 14:07"},
    {"departs": "14:10", "destination": "Manchester Piccadilly", "platform": "2A", "status": "On time"},
    {"heading": "PLATFORM 1"},
    {"departs": "14:15", "destination": "York", "platform": "1A", "status": "Delayed"},
    {"departs": "14:18", "destination": "Cleethorpes", "platform": "1B", "status": "Cancelled"},
    {"departs": "14:31", "destination": "Scarborough", "platform": "5B", "status": "On time"},
    {"departs": "14:34", "destination": "London St Pancras", "platform": "2", "status": "On time"},
    {"departs": "14:38", "destination": "Liverpool Lime Street", "via": "via Manchester",
     "platform": "6A", "status": "On time"},
    {"departs": "14:42", "destination": "Edinburgh", "platform": "5", "status": "On time",
     "note": ("First Class is at the front,", "Light refreshments available.")},
    {"departs": "14:47", "destination": "Norwich", "platform": "7", "status": "On time"},
    {"departs": "14:53", "destination": "Penzance", "platform": "-", "status": "On time"},
)

# Create a MightyFX object with both SP/CE ports set up for screens
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A screen refuses to be created where no panel answered on its port, and claims nothing when
# it does, so one panel runs the board on its own and a second widens it. The reserve is what
# a pair needs to convert full-size images; a lone screen simply does not draw on it.
#
# A 2.8" either way, the four columns needing its longer edge across: a 1.54" leaves the
# destination 77px, about ten characters, so all but the shortest name comes out an ellipsis
screens = []
for port in (mighty.spce_a, mighty.spce_b):
    try:
        screens.append(Screen280(port, reserve=Reserve.FULL_SIZE_IMAGES))
    except ValueError as e:
        print(e)

if not screens:
    mighty.shutdown()
    raise RuntimeError("No panels answered! Plug a screen into SP/CE A, and a second into SP/CE B to spread the board across two")

# Two panels are one board, so a page has to turn on both at the same moment. A pair holds
# them to one refresh rate and writes them on the same frame, where two screens written one
# after the other would leave one showing the new page while the other still held the old.
# Working out how takes a few seconds when the pair is created.
pair = ScreenPair(*screens) if len(screens) == 2 else None

# The board is wider than it is tall, so each canvas is drawn landscape and every update turns
# it a quarter turn onto the panel. A pair carries two pages at once, so it draws two
board_font = getattr(font, BOARD_FONT)
heading_font = getattr(font, HEADING_FONT)
large_font = getattr(font, LARGE_FONT)
canvases = [image(screens[0].height, screens[0].width) for _ in screens]

# Where the columns fall, measured from the widest thing each carries rather than counted in
# characters, so a different BOARD_FONT moves them instead of overrunning them
canvases[0].font = board_font
time_width = int(canvases[0].measure_text("00:00")[0])
plat_width = int(canvases[0].measure_text("Plat")[0])
status_width = int(canvases[0].measure_text("Cancelled")[0])

destination_x = INSET + time_width + GAP
status_x = canvases[0].width - INSET - status_width
plat_x = status_x - GAP - plat_width
destination_width = plat_x - GAP - destination_x
wide_width = canvases[0].width - INSET - destination_x   # For the lines with no columns beside them


def module_height(scale):
    """The height of one matrix module, lettering and the space around it."""
    return board_font.height * scale + PAD * 2


def layout(canvas):
    """Where every module sits on the panel, top to bottom, and how many listing rows there are.

    A board is assembled from matrix units of two heights. The thick ones carry the large
    lettering, so one sits at the top for the board's name and one at the foot for the page
    count and the clock, with the column headings and the listing on thin ones between them.
    How many rows there are comes from the panel's own height and BOARD_FONT's, so a taller
    face costs rows.

    Pixels left over after the stack widen the bars evenly, so the modules sit across the whole
    panel and any last pixel is a black sliver at the bottom rather than a border at both ends.

    Every module is sized from BOARD_FONT, the modules being one unit whatever they carry, so a
    taller LARGE_FONT is clipped by the module it sits on.
    """
    thick = module_height(LARGE_SCALE)
    thin = module_height(1)
    rows = max(1, (canvas.height - thick * 2 - thin - BAR * 3) // (thin + BAR))

    heights = [thick, thin] + [thin] * rows + [thick]
    slack = canvas.height - sum(heights) - BAR * (len(heights) - 1)
    gap = BAR + slack // (len(heights) - 1)

    places = []
    y = 0
    for height in heights:
        places.append((y, height))
        y += height + gap

    return places, rows


def bounds(place, x, width, scale=1):
    """A rect covering lettering inside one module, for text that needs bounds to align in."""
    return rect(x, place[0] + PAD, width, board_font.height * scale)


def entry_rows(entry):
    """How many listing rows an entry fills."""
    if "heading" in entry:
        return 1

    return 1 + (1 if entry.get("via") else 0) + len(entry.get("note", ()))


def paginate(rows):
    """The entries split into pages, each filling the listing without splitting an entry."""
    pages = []
    page = []
    used = 0
    for entry in ENTRIES:
        needed = entry_rows(entry)
        if page and used + needed > rows:
            pages.append(page)
            page, used = [], 0

        page.append(entry)
        used += needed

    if page:
        pages.append(page)

    return pages


places, rows = layout(canvases[0])
pages = paginate(rows)

# Printed lettering is not held to a module, so it sits centred in the band between the one above
# and the listing below, which lets HEADING_FONT be taller than the listing's own lettering
band_top = places[HEADINGS_ROW - 1][0] + places[HEADINGS_ROW - 1][1]
headings_y = band_top + (places[FIRST_ROW][0] - band_top - heading_font.height) // 2

print(f"Board on {len(screens)} of 2 SP/CE ports, {rows} rows a page, {len(pages)} pages of departures")


def draw(canvas, number, clock):
    """One page of the listing on the canvas, with its number and the time at the foot."""
    canvas.pen = color.black
    canvas.clear()

    # Every module face first, lit or not: the modules are there whether they are showing
    # anything, and the black bars between them are what makes each row its own. The column
    # headings get none, being printed on the board's face rather than shown on a module
    canvas.pen = MATRIX
    for index, (y, height) in enumerate(places):
        if index != HEADINGS_ROW or not PRINTED_HEADING:
            canvas.rectangle(rect(0, y, canvas.width, height))

    # The board's name, at double size on the thick module at the top
    canvas.pen = AMBER
    canvas.font = large_font
    canvas.text("Departures", bounds(places[0], INSET, canvas.width - INSET * 2, LARGE_SCALE),
                font_size=LARGE_SCALE)

    # The column headings, printed on the board's face or lit on a module of their own. A
    # position is passed as loose arguments: text() takes at= as a vec2 or as x and y, and
    # silently continues at the caret where a plain (x, y) tuple is handed to it
    face = heading_font if PRINTED_HEADING else board_font
    text_y = headings_y if PRINTED_HEADING else places[HEADINGS_ROW][0] + PAD
    canvas.font = face
    canvas.pen = HEADING if PRINTED_HEADING else AMBER
    canvas.text("Time", INSET, text_y)
    canvas.text("Destination", destination_x, text_y)
    canvas.text("Plat", rect(plat_x, text_y, plat_width, face.height), align=(image.RIGHT, image.TOP))
    canvas.text("Status", rect(status_x, text_y, status_width, face.height), align=(image.RIGHT, image.TOP))

    # The listing, an entry at a time, each taking as many rows as it needs. A page was built
    # to fit, so the row count is only reached by the last entry on it
    canvas.font = board_font
    canvas.pen = AMBER
    row = 0
    for entry in pages[number]:
        if row >= rows:
            break

        if "heading" in entry:
            canvas.text(entry["heading"], bounds(places[FIRST_ROW + row], destination_x, wide_width),
                        overflow=image.ELLIPSES)
            row += 1
            continue

        place = places[FIRST_ROW + row]
        canvas.text(entry["departs"], INSET, place[0] + PAD)

        # The destination is truncated with an ellipsis where it will not fit, as a real board
        # does rather than shrinking the lettering
        canvas.text(entry["destination"], bounds(place, destination_x, destination_width),
                    overflow=image.ELLIPSES)
        canvas.text(entry["platform"], bounds(place, plat_x, plat_width), align=(image.RIGHT, image.TOP))
        canvas.text(entry["status"], bounds(place, status_x, status_width), align=(image.RIGHT, image.TOP))
        row += 1

        # The via line and the note sit under their service, indented to the destination column
        # and running on into the platform and status columns, which are empty beside them
        for text in ((entry["via"],) if entry.get("via") else ()) + entry.get("note", ()):
            if row >= rows:
                break

            canvas.text(text, bounds(places[FIRST_ROW + row], destination_x, wide_width),
                        overflow=image.ELLIPSES)
            row += 1

    # The page count and the clock share the thick module at the foot, as a real board does
    canvas.font = large_font
    foot = bounds(places[-1], INSET, canvas.width - INSET * 2, LARGE_SCALE)
    canvas.text(f"Page {number + 1} of {len(pages)}", foot, font_size=LARGE_SCALE)
    canvas.text(clock, foot, font_size=LARGE_SCALE, align=(image.RIGHT, image.TOP))


def clock_at(started):
    """The time the board is showing, counted on from CLOCK_START."""
    elapsed = time.ticks_diff(time.ticks_ms(), started) // 1000
    hours, minutes, seconds = CLOCK_START
    total = (hours * 3600 + minutes * 60 + seconds + elapsed) % 86400
    return f"{total // 3600:02d}:{total // 60 % 60:02d}:{total % 60:02d}"


# Which page each panel starts on, so a pair reads left to right as one longer board
started = time.ticks_ms()
page = 0
turn_due = time.ticks_add(started, int(PAGE_HOLD * 1000))
shown = None

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if time.ticks_diff(time.ticks_ms(), turn_due) >= 0:
            page = (page + len(canvases)) % len(pages)
            turn_due = time.ticks_add(turn_due, int(PAGE_HOLD * 1000))

        # The board is drawn again whenever the page or the second changes, which is what makes
        # the clock tick. Nothing else on it moves, so the rest of the time it is left alone
        clock = clock_at(started)
        frame = (page, clock)
        if frame != shown:
            for position, canvas in enumerate(canvases):
                draw(canvas, (page + position) % len(pages), clock)

            if pair is not None:
                pair.update(canvases[0], canvases[1], rotation=90)
            else:
                screens[0].update(canvases[0], rotation=90)

            shown = frame

        time.sleep_ms(20)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
