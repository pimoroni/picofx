from mighty_fx import MightyFX, SPCE
from timing import Pacer, Roller
from screens import Reserve, Screen280, ScreenPair
from picovector import color, font, image, rect

"""
Draw a railway departures list on one screen, or across a pair turning their page together.

Press "Boot" to exit the program.

Section: Transport signs
"""

# Constants for drawing
BOARD_FONT = font.nope              # The listing's dot-matrix lettering. dir(font) lists them all
PRINTED_HEADING = True              # Show the column headings printed on the board's face, or lit on a module
HEADING_FONT = font.smart           # What they are printed in, being lettering the board does not light
LARGE_FONT = font.winds             # The board's own lettering, at the top and the foot
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
CLOCK_START = (14, 5, 0)            # The time the board counts on from, Mighty FX having no clock to read

# Made up but for the stations. A service takes a row, and its via and each note line one more
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

# A screen refuses to be created where no panel answers, so one panel runs the board and a
# second widens it. A 2.8" either way, as a 1.54" leaves the destination about ten characters
screens = []
for port in (mighty.spce_a, mighty.spce_b):
    try:
        screens.append(Screen280(port, reserve=Reserve.FULL_SIZE_IMAGES))
    except ValueError as e:
        print(e)

if not screens:
    mighty.shutdown()
    raise RuntimeError("No panels answered! Plug a screen into SP/CE A, and a second into SP/CE B to spread the board across two")

# A pair turns the page on both panels on one frame. Working out how takes a few seconds
pair = ScreenPair(*screens) if len(screens) == 2 else None

# A canvas per panel, drawn landscape and turned a quarter at each update
canvases = [image(screens[0].height, screens[0].width) for _ in screens]

# Column positions measured from the widest thing each carries, so another BOARD_FONT moves them
canvases[0].font = BOARD_FONT
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
    return BOARD_FONT.height * scale + PAD * 2


def layout(canvas):
    """
    Return where every module sits from top to bottom, and how many listing rows there are.

    Thick modules carry the large lettering at the top and foot. Thin ones carry the headings
    and listing, as many as the panel and BOARD_FONT allow. Spare pixels widen the bars evenly, and
    a taller LARGE_FONT is clipped by its module.
    """
    thick = module_height(LARGE_SCALE)
    thin = module_height(1)
    rows = max(1, (canvas.height - thick * 2 - thin - BAR * 2) // (thin + BAR))

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
    """The rect covering lettering inside one module, for text that needs bounds to align in."""
    return rect(x, place[0] + PAD, width, BOARD_FONT.height * scale)


def entry_rows(entry):
    """How many listing rows an entry fills."""
    if "heading" in entry:
        return 1

    return 1 + (1 if entry.get("via") else 0) + len(entry.get("note", ()))


def paginate(rows):
    """Split the entries into pages, each filling the listing without splitting an entry."""
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

# Printed lettering sits centred in the band between modules, so HEADING_FONT may be taller
band_top = places[HEADINGS_ROW - 1][0] + places[HEADINGS_ROW - 1][1]
headings_y = band_top + (places[FIRST_ROW][0] - band_top - HEADING_FONT.height) // 2

print(f"Board on {len(screens)} of 2 SP/CE ports, {rows} rows a page, {len(pages)} pages of departures")


def draw(canvas, number, clock):
    """Draw one page of the listing on the canvas, with its number and the time at the foot."""
    canvas.pen = color.black
    canvas.clear()

    # A module face for every row first, lit or not, but none behind the printed headings
    canvas.pen = MATRIX
    for index, (y, height) in enumerate(places):
        if index != HEADINGS_ROW or not PRINTED_HEADING:
            canvas.rectangle(rect(0, y, canvas.width, height))

    # The board's name, at double size on the thick module at the top
    canvas.pen = AMBER
    canvas.font = LARGE_FONT
    canvas.text("Departures", bounds(places[0], INSET, canvas.width - INSET * 2, LARGE_SCALE),
                font_size=LARGE_SCALE)

    # The column headings, printed on the board's face or lit on a module of their own. Positions
    # go as loose x and y, as text() ignores an (x, y) tuple
    face = HEADING_FONT if PRINTED_HEADING else BOARD_FONT
    text_y = headings_y if PRINTED_HEADING else places[HEADINGS_ROW][0] + PAD
    canvas.font = face
    canvas.pen = HEADING if PRINTED_HEADING else AMBER
    canvas.text("Time", INSET, text_y)
    canvas.text("Destination", destination_x, text_y)
    canvas.text("Plat", rect(plat_x, text_y, plat_width, face.height), align=(image.RIGHT, image.TOP))
    canvas.text("Status", rect(status_x, text_y, status_width, face.height), align=(image.RIGHT, image.TOP))

    # The listing, an entry at a time, each taking as many rows as it needs. A page was built to fit
    canvas.font = BOARD_FONT
    canvas.pen = AMBER
    row = 0
    for entry in pages[number]:
        if "heading" in entry:
            canvas.text(entry["heading"], bounds(places[FIRST_ROW + row], destination_x, wide_width),
                        overflow=image.ELLIPSES)
            row += 1
            continue

        place = places[FIRST_ROW + row]
        canvas.text(entry["departs"], INSET, place[0] + PAD)

        # The destination, cut with an ellipsis where it will not fit
        canvas.text(entry["destination"], bounds(place, destination_x, destination_width),
                    overflow=image.ELLIPSES)
        canvas.text(entry["platform"], bounds(place, plat_x, plat_width), align=(image.RIGHT, image.TOP))
        canvas.text(entry["status"], bounds(place, status_x, status_width), align=(image.RIGHT, image.TOP))
        row += 1

        # The via line and the note sit under their service, indented to the destination column
        # and running on into the platform and status columns, which are empty beside them
        for text in ((entry["via"],) if entry.get("via") else ()) + entry.get("note", ()):
            canvas.text(text, bounds(places[FIRST_ROW + row], destination_x, wide_width),
                        overflow=image.ELLIPSES)
            row += 1

    # The page count and the clock share the thick module at the foot, as a real board does
    canvas.font = LARGE_FONT
    foot = bounds(places[-1], INSET, canvas.width - INSET * 2, LARGE_SCALE)
    canvas.text(f"Page {number + 1} of {len(pages)}", foot, font_size=LARGE_SCALE)
    canvas.text(clock, foot, font_size=LARGE_SCALE, align=(image.RIGHT, image.TOP))


def clock_at(elapsed):
    """The time the board is showing, counted on from CLOCK_START."""
    elapsed //= 1000
    hours, minutes, seconds = CLOCK_START
    total = (hours * 3600 + minutes * 60 + seconds + elapsed) % 86400
    return f"{total // 3600:02d}:{total // 60 % 60:02d}:{total % 60:02d}"


# The pacer is the board's clock and holds it to a look every 20ms. The roller turns the page
pacer = Pacer(0.02)
turn = Roller(PAGE_HOLD)
page = 0
shown = None

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if turn.is_due():
            # On by as many pages as there are panels, so a pair never shows one twice
            page = (page + len(canvases)) % len(pages)
            turn.advance()

        # Draw the board again when the page or the second changes, which ticks the clock
        clock = clock_at(pacer.elapsed)
        frame = (page, clock)
        if frame != shown:
            # Each panel shows the next page on, so a pair reads left to right as one longer board
            for position, canvas in enumerate(canvases):
                draw(canvas, (page + position) % len(pages), clock)

            if pair is not None:
                pair.update(canvases[0], canvases[1], rotation=90)
            else:
                screens[0].update(canvases[0], rotation=90)

            shown = frame

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
