import time
from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, font, image, rect

"""
Draw a railway departure board across a screen hub, a service to each panel, every one
paging its calling points on its own clock.

Press "Boot" to exit the program.
"""

# Constants for drawing
BOARD_FONT = "nope"             # A dot-matrix look. sins and winds suit as well, and dir(font) lists all 37
# The operator's name is set larger than the rest of the board. Doubling keeps it a matrix
# unit like the others, and winds is one of only two faces in ROM narrow enough to carry the
# longest operator name across a 240px panel at double size. The condensed faces fit at
# single size instead, manticore being the tallest of those.
OPERATOR_FONT = "winds"
OPERATOR_SCALE = 2
PRINTED_HEADING = True          # Show the calling points heading printed on the board's face, or lit on a module
HEADING_FONT = "smart"          # What it is printed in, being lettering the board does not light
AMBER = color.rgb(255, 176, 0)  # The colour of a lit lamp
HEADING = color.rgb(255, 240, 220)  # Printed lettering, which a real board sets apart from what it lights
MATRIX = color.rgb(20, 20, 16)  # The unlit face of a matrix module, against the black bars between them
HEADER_SCALE = 2                # Pixel fonts scale by whole numbers, so 2 is double size
INSET = 6                       # How far in from the panel's left and right edges lettering starts
BAR = 3                         # The black bar between one module and the next, in pixels
PAD = 2                         # Space inside a module, above and below its lettering
PAGE_HOLD = 6.0                 # How long every panel holds a page for, in seconds
CALLING_ROW = 3                 # Where the calling points heading sits in the stack of modules

# A panel cannot be asked its size, so the board is told, and every panel is taken as this
# one. A hub is free to mix sizes and a board like this does not: one size keeps a single
# canvas serving every panel, and 2.8 is the safer guess either way, its taller window
# wrapping harmlessly on a 1.54" where the shorter one would leave a 2.8" part dark.
SCREEN_SIZE = "2.8"

# The board's content, one service to a panel. The stations are real and called at in order,
# and everything else is made up, operators included. A platform of "-" is one that has not
# been announced, and a via of "" leaves that row of the board unlit.
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

# Build every panel the hub reaches and keep whichever answered, so a partly populated
# hub still shows a board. reveal_together holds the shared backlight until all of them
# carry a service, which is what makes the fill below arrive as one board
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

# No group and no alignment here. A group exists to put one frame on several panels at
# once, where every panel on this board carries its own service and turns its page at its
# own moment, so each is written on its own and waits its own tearing-effect signal.
board_font = getattr(font, BOARD_FONT)
operator_font = getattr(font, OPERATOR_FONT)
heading_font = getattr(font, HEADING_FONT)


def module_height(scale):
    """The height of one matrix module, lettering and the space around it."""
    return board_font.height * scale + PAD * 2


def module(canvas, y, height):
    """Draw one module's face across the panel, whether anything will be shown on it."""
    canvas.pen = MATRIX
    canvas.rectangle(rect(0, y, canvas.width, height))


def layout(canvas):
    """Where every module sits on the panel, top to bottom, and how many rows there are.

    A board is assembled from matrix units of two heights: thick ones carrying the large
    lettering and thin ones carrying the calling points. So the two at the top and the note
    at the bottom are thick and the rows between them are thin, and how many rows there are
    comes from the panel's own height, a 1.54" holding fewer than a 2.8".

    Pixels left over after the stack go into the gaps beside the thick units, which carry
    more bezel than the thin ones, so the stack starts at the top edge and any remainder is
    a black sliver at the bottom rather than a border at both ends.
    """
    thick = module_height(HEADER_SCALE)
    thin = module_height(1)
    rows = max(2, (canvas.height - thick * 3 - BAR * 2) // (thin + BAR))

    heights = [thick, thick] + [thin] * rows + [thick]
    thick_at = (0, 1, len(heights) - 1)
    slack = canvas.height - sum(heights) - BAR * (len(heights) - 1)

    gaps = [BAR] * (len(heights) - 1)
    for position in range(len(gaps)):
        if slack <= 0:
            break
        if position in thick_at or position + 1 in thick_at:
            gaps[position] += 1
            slack -= 1

    places = []
    y = 0
    for position, height in enumerate(heights):
        places.append((y, height))
        y += height + (gaps[position] if position < len(gaps) else 0)

    return places, rows


# One canvas serves every panel, drawn again before each write, which is what taking them
# all as one size buys. It goes on the regular heap rather than through canvas(), six
# panels' workspaces leaving no SRAM to claim, and the faster conversion SRAM buys is worth
# nothing to a board that redraws every few seconds.
canvas = image(panels[0].width, panels[0].height)
places, rows = layout(canvas)

# Printed lettering is not held to a module, so it sits centred in the band between the one
# above and the list below, which lets HEADING_FONT be taller than the board's own lettering.
# A page number does change, so each of its digits keeps a matrix module of its own, one
# character wide and inset in the printed words. One module holds one digit, so a service
# running past nine pages would outgrow its cell
band_top = places[CALLING_ROW - 1][0] + places[CALLING_ROW - 1][1]
heading_y = band_top + (places[CALLING_ROW + 1][0] - band_top - heading_font.height) // 2

canvas.font = heading_font
page_label_width = int(canvas.measure_text("Page ")[0])
of_label_width = int(canvas.measure_text(" of ")[0])

canvas.font = board_font
digit_cell_width = int(canvas.measure_text("0")[0]) + PAD * 2
page_count_width = page_label_width + of_label_width + digit_cell_width * 2


def row(index, scale=1):
    """A rect covering one module's lettering, for text that needs bounds to align in."""
    y, height = places[index]
    return rect(INSET, y + PAD, canvas.width - INSET * 2, board_font.height * scale)


def draw(index, page):
    """One service on the canvas, showing the given page of its calling points."""
    service = SERVICES[index % len(SERVICES)]

    # The last stop is announced with an ampersand and a full stop, as a real board does
    stops = list(service["calling"])
    stops[-1] = f"& {stops[-1]}."

    # The thin rows carry the via line, the heading, the calling points and the coach count
    list_lines = rows - 3
    pages = max(1, (len(stops) + list_lines - 1) // list_lines)

    canvas.pen = color.black
    canvas.clear()
    canvas.font = board_font

    # Every module face first, lit or not: the modules are there whether they are showing
    # anything, and the black bars between them are what makes each row its own. A printed
    # heading gets none, its lettering being on the board's face rather than on a module
    for index, (y, height) in enumerate(places):
        if index != CALLING_ROW or not PRINTED_HEADING:
            module(canvas, y, height)

    canvas.pen = AMBER

    # The departure time, with the platform against the right edge of the same module. A
    # platform that has not been announced shows as a dash rather than as nothing
    header = row(0, HEADER_SCALE)
    canvas.text(service["departs"], header, font_size=HEADER_SCALE)
    canvas.text(f"Plat {service['platform']}", header, font_size=HEADER_SCALE,
                align=(image.RIGHT, image.TOP))

    # The destination, truncated with an ellipsis where it will not fit, as a real board
    # does rather than shrinking the lettering, and the via line on the row below it
    canvas.text(service["destination"], row(1, HEADER_SCALE), font_size=HEADER_SCALE,
                overflow=image.ELLIPSES)
    if service["via"]:
        canvas.text(service["via"], INSET, places[2][0] + PAD)

    # The heading, with the page count against the right edge of the same row. A position
    # is passed as loose arguments: text() takes at= as a vec2 or as x and y, and silently
    # continues at the caret where a plain (x, y) tuple is handed to it
    if PRINTED_HEADING:
        canvas.font = heading_font
        canvas.pen = HEADING
        canvas.text("Calling at:", INSET, heading_y)

        count_x = canvas.width - INSET - page_count_width
        canvas.text("Page ", count_x, heading_y)
        canvas.text(" of ", count_x + page_label_width + digit_cell_width, heading_y)

        # The two numbers, each on a matrix module of its own inset in that lettering
        canvas.font = board_font
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

    for offset, stop in enumerate(stops[page * list_lines:(page + 1) * list_lines]):
        canvas.text(stop, INSET, places[4 + offset][0] + PAD)

    # The coach count on the last thin row, above the operator on the thick module at the
    # foot of the board, its lettering sitting low in it as a real one's does
    canvas.text(f"Formed of {service['coaches']} coaches", INSET, places[-2][0] + PAD)

    operator_y, operator_height = places[-1]
    canvas.font = operator_font
    canvas.text(service["operator"],
                rect(INSET, operator_y, canvas.width - INSET * 2, operator_height - PAD),
                font_size=OPERATOR_SCALE, align=(image.LEFT, image.BOTTOM),
                overflow=image.ELLIPSES)

    return pages


# Every panel holds a page for the same time and turns it at its own moment, spread evenly
# across that time. One shared period with a different offset each is what guarantees no two
# panels ever change together, however long the board runs: holds of differing lengths only
# postpone the collision, two of 4 and 8 seconds meeting every 8.
pages = [0] * len(panels)
stagger = PAGE_HOLD / len(panels)

# The whole board is filled before any of it starts turning, so it comes up complete rather
# than a panel at a time
for index, panel in enumerate(panels):
    count = draw(index, 0)
    panel.update(canvas)

    # The next page to show, which stays at the first where a service only has one
    pages[index] = 1 % count

started = time.ticks_ms()
due = [time.ticks_add(started, int((index + 1) * stagger * 1000)) for index in range(len(panels))]

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        now = time.ticks_ms()

        for index, panel in enumerate(panels):
            if time.ticks_diff(now, due[index]) < 0:
                continue

            count = draw(index, pages[index])
            panel.update(canvas)

            pages[index] = (pages[index] + 1) % count
            due[index] = time.ticks_add(due[index], int(PAGE_HOLD * 1000))

        time.sleep_ms(20)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
