from picovector import color, font, image, rect

"""
Drawing: Departures list
A railway departures list, its pages turning and its clock ticking.
Section: Transport signs
"""

# Entry: screenA rotation=90: graphics file=departures_list.py fps=50

# Constants for drawing
TITLE = "Departures"                # The board's name, along the top
BOARD_FONT = font.nope
PRINTED_HEADING = True
HEADING_FONT = font.smart
LARGE_FONT = font.winds
AMBER = color.rgb(255, 176, 0)
HEADING = color.rgb(255, 240, 220)
MATRIX = color.rgb(20, 20, 16)
BOARD = color.black                 # What the modules are set into, showing as the bars between them
LARGE_SCALE = 2
INSET = 6
GAP = 8
BAR = 3
PAD = 2
PAGE_HOLD_MS = 8000                 # How long the board holds a page for, longer where a line is still to scroll through
SCROLL_HOLD_MS = 1500               # How long a line too long for its place rests at each end
SCROLL_SPEED = 40                   # How fast it scrolls through, in pixels a second
HEADINGS_ROW = 1
FIRST_ROW = 2
CLOCK_START = (14, 5, 0)            # The time the board counts on from, Mighty FX having no clock to read

# Made up but for the stations. A service takes a row, and its via, its calling points and each note line
# one more
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
     "calling": "Calling at Doncaster, York, Darlington, Durham, Newcastle, Morpeth, Berwick-upon-Tweed, Dunbar and Edinburgh",
     "note": ("First Class is at the front.",)},
    {"departs": "14:47", "destination": "Norwich", "platform": "7", "status": "On time"},
    {"departs": "14:53", "destination": "Penzance", "platform": "-", "status": "On time"},
)

# Column widths measured from the widest thing each carries, on an image of their own as the
# canvas is not here yet
ruler = image(8, 8)
ruler.font = BOARD_FONT
time_width = int(ruler.measure_text("00:00")[0])
plat_width = int(ruler.measure_text("Plat")[0])
status_width = int(ruler.measure_text("Cancelled")[0])
del ruler

destination_x = INSET + time_width + GAP

# Placed on the first call, from the canvas's size
status_x = plat_x = destination_width = wide_width = 0
places = pages = page_strips = None
headings_y = 0

# A destination or calling points too long for their place scroll through it, so each is drawn once onto
# a strip of its own, kept with the width it shows through. Any other line is cut with an ellipsis
strips = {}


def lines_under(entry):
    """The lines an entry carries under its service, its via, its calling points and its note."""
    return tuple(entry[key] for key in ("via", "calling") if entry.get(key)) + entry.get("note", ())


def scrolling(entry):
    """The lines of an entry that scroll where too long for their place, its destination and calling points."""
    if "heading" in entry:
        return ()
    return ((entry["destination"], destination_width),) + (((entry["calling"], wide_width),) if entry.get("calling") else ())


def scroll_cycle(strip, room):
    """Calculate how long a strip takes to scroll through once, resting at both ends, in milliseconds."""
    return SCROLL_HOLD_MS * 2 + (strip.width - room) * 1000 // SCROLL_SPEED


def scroll_offset(strip, room, since):
    """
    Calculate how far a strip has scrolled through its place, since= milliseconds into its page.

    It rests at the start, scrolls until its end shows, rests there, and starts again.
    """
    into = since % scroll_cycle(strip, room)
    return min(strip.width - room, max(0, (into - SCROLL_HOLD_MS) * SCROLL_SPEED // 1000))


def put(canvas, text, place, x, room, since):
    """Draw a line in its place, or the window of its strip that has scrolled into it."""
    if text in strips:
        strip, _ = strips[text]
        canvas.blit(strip, rect(scroll_offset(strip, room, since), 0, room, strip.height), bounds(place, x, room))
    else:
        canvas.text(text, bounds(place, x, room), overflow=image.ELLIPSES)


def page_hold(number):
    """Calculate how long a page holds, in milliseconds, long enough for every line on it to scroll through once."""
    return max([PAGE_HOLD_MS] + [scroll_cycle(*strip) for strip in page_strips[number]])


def module_height(scale):
    """The height of one matrix module, lettering and the space around it."""
    return BOARD_FONT.height * scale + PAD * 2


def layout(canvas):
    """Return where every module sits from top to bottom, and how many listing rows there are."""
    thick = module_height(LARGE_SCALE)
    thin = module_height(1)
    rows = max(1, (canvas.height - thick * 2 - thin - BAR * 2) // (thin + BAR))

    heights = [thick, thin] + [thin] * rows + [thick]
    slack = canvas.height - sum(heights) - BAR * (len(heights) - 1)
    gap = BAR + slack // (len(heights) - 1)

    found = []
    y = 0
    for height in heights:
        found.append((y, height))
        y += height + gap

    return found, rows


def bounds(place, x, width, scale=1):
    """The rect covering lettering inside one module, for text that needs bounds to align in."""
    return rect(x, place[0] + PAD, width, BOARD_FONT.height * scale)


def entry_rows(entry):
    """How many listing rows an entry fills."""
    if "heading" in entry:
        return 1

    return 1 + len(lines_under(entry))


def paginate(rows):
    """Split the entries into pages, each filling the listing without splitting an entry."""
    found = []
    page = []
    used = 0
    for entry in ENTRIES:
        needed = entry_rows(entry)
        if page and used + needed > rows:
            found.append(page)
            page, used = [], 0

        page.append(entry)
        used += needed

    if page:
        found.append(page)

    return found


def setup(canvas):
    """Place the columns and modules on the canvas, draw the strips, and split the entries into pages."""
    global status_x, plat_x, destination_width, wide_width, places, pages, page_strips, headings_y
    status_x = canvas.width - INSET - status_width
    plat_x = status_x - GAP - plat_width
    destination_width = plat_x - GAP - destination_x
    wide_width = canvas.width - INSET - destination_x

    canvas.font = BOARD_FONT
    for entry in ENTRIES:
        for text, room in scrolling(entry):
            wide = canvas.measure_text(text)[0]
            if wide > room:
                strip = image(int(wide) + 1, BOARD_FONT.height)
                strip.font = BOARD_FONT
                strip.pen = color.transparent
                strip.clear()
                strip.pen = AMBER
                strip.text(text, 0, 0)
                strips[text] = (strip, room)

    places, rows = layout(canvas)
    pages = paginate(rows)

    # The strips each page scrolls, so the board is only drawn again when one of them moves
    page_strips = [[strips[text] for entry in page for text, _ in scrolling(entry) if text in strips] for page in pages]

    band_top = places[HEADINGS_ROW - 1][0] + places[HEADINGS_ROW - 1][1]
    headings_y = band_top + (places[FIRST_ROW][0] - band_top - HEADING_FONT.height) // 2


def page_of(canvas, number, clock, since):
    """Draw one page of the listing on the canvas, with its number and the time at the foot, since= milliseconds into it."""
    canvas.pen = BOARD
    canvas.clear()

    canvas.pen = MATRIX
    for index, (y, height) in enumerate(places):
        if index != HEADINGS_ROW or not PRINTED_HEADING:
            canvas.rectangle(rect(0, y, canvas.width, height))

    canvas.pen = AMBER
    canvas.font = LARGE_FONT
    canvas.text(TITLE, bounds(places[0], INSET, canvas.width - INSET * 2, LARGE_SCALE),
                font_size=LARGE_SCALE)

    face = HEADING_FONT if PRINTED_HEADING else BOARD_FONT
    text_y = headings_y if PRINTED_HEADING else places[HEADINGS_ROW][0] + PAD
    canvas.font = face
    canvas.pen = HEADING if PRINTED_HEADING else AMBER
    canvas.text("Time", INSET, text_y)
    canvas.text("Destination", destination_x, text_y)
    canvas.text("Plat", rect(plat_x, text_y, plat_width, face.height), align=(image.RIGHT, image.TOP))
    canvas.text("Status", rect(status_x, text_y, status_width, face.height), align=(image.RIGHT, image.TOP))

    canvas.font = BOARD_FONT
    canvas.pen = AMBER
    row = 0
    for entry in pages[number]:
        if "heading" in entry:
            put(canvas, entry["heading"], places[FIRST_ROW + row], destination_x, wide_width, since)
            row += 1
            continue

        place = places[FIRST_ROW + row]
        canvas.text(entry["departs"], INSET, place[0] + PAD)
        put(canvas, entry["destination"], place, destination_x, destination_width, since)
        canvas.text(entry["platform"], bounds(place, plat_x, plat_width), align=(image.RIGHT, image.TOP))
        canvas.text(entry["status"], bounds(place, status_x, status_width), align=(image.RIGHT, image.TOP))
        row += 1

        # The via, calling points and note sit under their service, indented to the destination column
        # and running on into the platform and status columns, which are empty beside them
        for text in lines_under(entry):
            put(canvas, text, places[FIRST_ROW + row], destination_x, wide_width, since)
            row += 1

    canvas.font = LARGE_FONT
    foot = bounds(places[-1], INSET, canvas.width - INSET * 2, LARGE_SCALE)
    canvas.text(f"Page {number + 1} of {len(pages)}", foot, font_size=LARGE_SCALE)
    canvas.text(clock, foot, font_size=LARGE_SCALE, align=(image.RIGHT, image.TOP))


def clock_at(elapsed_ms):
    """The time the board is showing, counted on from CLOCK_START."""
    hours, minutes, seconds = CLOCK_START
    total = (hours * 3600 + minutes * 60 + seconds + int(elapsed_ms // 1000)) % 86400
    return f"{total // 3600:02d}:{total // 60 % 60:02d}:{total % 60:02d}"


page = 0
due = 0                 # When the page next turns, in elapsed ms, set once the pages are known
turned_at = 0           # When the page turned, which its lines scroll from
shown = None


def draw(canvas, elapsed):
    global page, due, turned_at, shown
    if pages is None:
        setup(canvas)
        due = page_hold(page)

    now = int(elapsed * 1000)
    if now >= due:
        page = (page + 1) % len(pages)
        turned_at = now
        due += page_hold(page)

    # The canvas keeps the last page, so one is only drawn when the page or the second changes, which
    # ticks the clock, or a line scrolls
    clock = clock_at(now)
    since = now - turned_at
    frame = (page, clock, tuple(scroll_offset(*strip, since) for strip in page_strips[page]))
    if frame != shown:
        page_of(canvas, page, clock, since)
        shown = frame
