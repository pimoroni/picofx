from mighty_fx import MightyFX, SPCE
from timing import Pacer, Roller
from screens import SCREEN_TYPES
from picovector import color, font, image, rect

"""
Draw a railway departure board across a screen hub, a service to each panel, every one
paging its calling points on its own clock.

Press "Boot" to exit the program.

Section: Transport signs
"""

# Constants for drawing
BOARD_FONT = font.nope          # A dot-matrix look. sins and winds suit as well, and dir(font) lists them all
# The operator's name, doubled to stay a matrix unit. winds is one of two ROM faces narrow
# enough for the longest name across a 240px panel
OPERATOR_FONT = font.winds
OPERATOR_SCALE = 2
PRINTED_HEADING = True          # Show the calling points heading printed on the board's face, or lit on a module
HEADING_FONT = font.smart       # What it is printed in, being lettering the board does not light
AMBER = color.rgb(255, 176, 0)  # The colour of a lit lamp
HEADING = color.rgb(255, 240, 220)  # Printed lettering, which a real board sets apart from what it lights
MATRIX = color.rgb(20, 20, 16)  # The unlit face of a matrix module, against the black bars between them
HEADER_SCALE = 2                # Pixel fonts scale by whole numbers, so 2 is double size
INSET = 6                       # How far in from the panel's left and right edges lettering starts
BAR = 3                         # The black bar between one module and the next, in pixels
PAD = 2                         # Space inside a module, above and below its lettering
PAGE_HOLD = 6.0                 # How long every panel holds a page for, in seconds
CALLING_ROW = 3                 # Where the calling points heading sits in the stack of modules

# A panel cannot be asked its size, so every panel is taken as this one and one canvas
# serves them all. 2.8 is the safer guess, wrapping harmlessly on a 1.54".
SCREEN_SIZE = "2.8"

# One service to a panel. The stations are real and in order, the rest made up. A platform of
# "-" is unannounced, and an empty via leaves its row unlit.
SERVICES = (
    {"departs": "14:31", "platform": "5B", "destination": "Scarborough",
     "via": "via Hull", "coaches": 2, "operator": "Cutlass Coast Railway",
     "calling": ("Meadowhall", "Doncaster", "Goole", "Brough", "Hull", "Cottingham",
                 "Beverley", "Driffield", "Bridlington", "Bempton", "Hunmanby", "Filey",
                 "Seamer", "Scarborough")},
    {"departs": "14:34", "platform": "2", "destination": "London St Pancras",
     "via": "via Leicester", "coaches": 10, "operator": "Spritsail Trains",
     "calling": ("Chesterfield", "Derby", "Long Eaton", "East Midlands Parkway",
                 "Loughborough", "Leicester", "Corby", "Kettering", "Wellingborough", "Luton",
                 "London St Pancras")},
    {"departs": "14:38", "platform": "6A", "destination": "Liverpool Lime Street",
     "via": "via Manchester", "coaches": 3, "operator": "Hornpipe Express",
     "calling": ("Stockport", "Manchester Piccadilly", "Manchester Oxford Road", "Urmston",
                 "Irlam", "Birchwood", "Warrington Central", "Liverpool South Parkway",
                 "Liverpool Lime Street")},
    {"departs": "14:42", "platform": "5", "destination": "Edinburgh",
     "via": "via York", "coaches": 5, "operator": "Longships Railway",
     "calling": ("Doncaster", "York", "Darlington", "Durham", "Newcastle", "Morpeth",
                 "Berwick-upon-Tweed", "Dunbar", "Edinburgh")},
    {"departs": "14:47", "platform": "7", "destination": "Norwich",
     "via": "via Nottingham", "coaches": 4, "operator": "Spritsail Trains",
     "calling": ("Chesterfield", "Alfreton", "Langley Mill", "Ilkeston", "Nottingham",
                 "Grantham", "Peterborough", "Ely", "Thetford", "Attleborough", "Wymondham",
                 "Norwich")},
    {"departs": "14:53", "platform": "-", "destination": "Penzance",
     "via": "via Birmingham", "coaches": 7, "operator": "Longships Railway",
     "calling": ("Chesterfield", "Derby", "Burton-on-Trent", "Birmingham New Street",
                 "Cheltenham Spa", "Bristol Parkway", "Bristol Temple Meads", "Taunton",
                 "Tiverton Parkway", "Exeter St Davids", "Newton Abbot", "Totnes", "Plymouth",
                 "Liskeard", "Bodmin Parkway", "Par", "St Austell", "Truro", "Redruth",
                 "Camborne", "Hayle", "St Erth", "Penzance")},
)

# Create a MightyFX object with a screen hub across both SP/CE ports, one carrying the
# bus and the other giving up its five lines as extra chip selects
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_SELECTS)

# Build a screen on every hub port and keep those that answer, as a hub need not be full.
# reveal_together holds the shared backlight until all of them carry a service
panels = []
answered = []
for index, port in enumerate(mighty.hub.ports):
    try:
        panels.append(SCREEN_TYPES[SCREEN_SIZE](port, reveal_together=True))
        answered.append(index)
    except ValueError:
        pass

if not panels:
    mighty.shutdown()
    raise RuntimeError("No panels answered! Check the hub is plugged into SP/CE A, with its panels on the hub rather than on the board")

# Which positions answered, so a panel that stayed dark can be told from a position left empty
print(f"{len(panels)} of {len(mighty.hub.ports)} hub positions answered, {answered}, "
      f"showing {min(len(panels), len(SERVICES))} of {len(SERVICES)} services")


def module_height(scale):
    """The height of one matrix module, lettering and the space around it."""
    return BOARD_FONT.height * scale + PAD * 2


def module(canvas, y, height):
    """Draw one module's face across the panel, whether anything will be shown on it."""
    canvas.pen = MATRIX
    canvas.rectangle(rect(0, y, canvas.width, height))


def layout(canvas):
    """
    Return where every module sits from top to bottom, and how many thin rows there are.

    Thick modules carry the large lettering at the top and foot, thin ones the calling points
    between, as many as the panel holds. Spare pixels widen the gaps beside the thick modules.
    """
    thick = module_height(HEADER_SCALE)
    thin = module_height(1)
    rows = (canvas.height - thick * 3 - BAR * 2) // (thin + BAR)

    heights = [thick, thick] + [thin] * rows + [thick]
    thick_at = (0, 1, len(heights) - 1)
    slack = canvas.height - sum(heights) - BAR * (len(heights) - 1)

    gaps = [BAR] * (len(heights) - 1)
    beside = [position for position in range(len(gaps)) if position in thick_at or position + 1 in thick_at]
    for count in range(slack):
        gaps[beside[count % len(beside)]] += 1

    places = []
    y = 0
    for position, height in enumerate(heights):
        places.append((y, height))
        y += height + (gaps[position] if position < len(gaps) else 0)

    return places, rows


# One canvas serves every panel, drawn again before each write
canvas = image(panels[0].width, panels[0].height)
places, rows = layout(canvas)

# Printed lettering sits centred in the band between modules, so HEADING_FONT may be taller.
# Each page digit keeps a module of its own, so nine pages is the most
band_top = places[CALLING_ROW - 1][0] + places[CALLING_ROW - 1][1]
heading_y = band_top + (places[CALLING_ROW + 1][0] - band_top - HEADING_FONT.height) // 2

# The page count's printed words and its two digit modules, measured once to set it against the right edge
canvas.font = HEADING_FONT
page_label_width = int(canvas.measure_text("Page ")[0])
of_label_width = int(canvas.measure_text(" of ")[0])

canvas.font = BOARD_FONT
digit_cell_width = int(canvas.measure_text("0")[0]) + PAD * 2
page_count_width = page_label_width + of_label_width + digit_cell_width * 2


def row(index, scale=1):
    """The rect covering one module's lettering, for text that needs bounds to align in."""
    y, _ = places[index]
    return rect(INSET, y + PAD, canvas.width - INSET * 2, BOARD_FONT.height * scale)


def draw(index, page):
    """Draw one service on the canvas, showing the given page of its calling points."""
    service = SERVICES[index % len(SERVICES)]

    # The last stop is announced with an ampersand and a full stop, as a real board does
    stops = list(service["calling"])
    stops[-1] = f"& {stops[-1]}."

    # The thin rows carry the via line, the heading, the calling points and the coach count
    list_lines = rows - 3
    pages = max(1, (len(stops) + list_lines - 1) // list_lines)

    canvas.pen = color.black
    canvas.clear()
    canvas.font = BOARD_FONT

    # A module face for every row first, lit or not, but none behind a printed heading
    for place, (y, height) in enumerate(places):
        if place != CALLING_ROW or not PRINTED_HEADING:
            module(canvas, y, height)

    canvas.pen = AMBER

    # The departure time, with the platform against the right edge of the same module. An
    # unannounced platform shows as a dash
    header = row(0, HEADER_SCALE)
    canvas.text(service["departs"], header, font_size=HEADER_SCALE)
    canvas.text(f"Plat {service['platform']}", header, font_size=HEADER_SCALE,
                align=(image.RIGHT, image.TOP))

    # The destination cut with an ellipsis where it will not fit, and the via line below
    canvas.text(service["destination"], row(1, HEADER_SCALE), font_size=HEADER_SCALE,
                overflow=image.ELLIPSES)
    if service["via"]:
        canvas.text(service["via"], INSET, places[CALLING_ROW - 1][0] + PAD)

    # The heading, and the page count at the row's right edge.
    # Positions go as loose x and y, as text() ignores an (x, y) tuple
    if PRINTED_HEADING:
        canvas.font = HEADING_FONT
        canvas.pen = HEADING
        canvas.text("Calling at:", INSET, heading_y)

        count_x = canvas.width - INSET - page_count_width
        canvas.text("Page ", count_x, heading_y)
        canvas.text(" of ", count_x + page_label_width + digit_cell_width, heading_y)

        # The two numbers, each on a matrix module of its own inset in that lettering
        canvas.font = BOARD_FONT
        first_x = count_x + page_label_width
        second_x = first_x + digit_cell_width + of_label_width
        for cell_x, value in ((first_x, page + 1), (second_x, pages)):
            canvas.pen = MATRIX
            canvas.rectangle(rect(cell_x, places[CALLING_ROW][0], digit_cell_width, places[CALLING_ROW][1]))
            canvas.pen = AMBER
            canvas.text(str(value), cell_x + PAD, places[CALLING_ROW][0] + PAD)

        canvas.pen = AMBER
    else:
        canvas.text("Calling at:", INSET, places[CALLING_ROW][0] + PAD)
        canvas.text(f"Page {page + 1} of {pages}", row(CALLING_ROW), align=(image.RIGHT, image.TOP))

    # This page's share of the calling points, from the row under the heading
    for offset, stop in enumerate(stops[page * list_lines:(page + 1) * list_lines]):
        canvas.text(stop, INSET, places[CALLING_ROW + 1 + offset][0] + PAD)

    # The coach count on the last thin row, above the operator on the thick module at the
    # foot of the board, its lettering sitting low in it as a real one's does
    canvas.text(f"Formed of {service['coaches']} coaches", INSET, places[-2][0] + PAD)

    operator_y, operator_height = places[-1]
    canvas.font = OPERATOR_FONT
    canvas.text(service["operator"],
                rect(INSET, operator_y, canvas.width - INSET * 2, operator_height - PAD),
                font_size=OPERATOR_SCALE, align=(image.LEFT, image.BOTTOM),
                overflow=image.ELLIPSES)

    return pages


# Every panel holds a page as long, staggered evenly across that time so no two change together
pages = [0] * len(panels)
stagger = PAGE_HOLD / len(panels)

# Fill the whole board before any of it turns
for index, panel in enumerate(panels):
    count = draw(index, 0)
    panel.update(canvas)

    # The next page to show, which stays at the first where a service only has one
    pages[index] = 1 % count

# Each panel's first turn falls at its own share of the stagger, and every one after it PAGE_HOLD on
turns = [Roller((index + 1) * stagger) for index in range(len(panels))]
pacer = Pacer(0.02)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        for index, panel in enumerate(panels):
            if not turns[index].is_due():
                continue

            # Each panel is written alone, carrying its own service and turning at its own moment
            count = draw(index, pages[index])
            panel.update(canvas)

            pages[index] = (pages[index] + 1) % count
            turns[index].advance(PAGE_HOLD)

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
