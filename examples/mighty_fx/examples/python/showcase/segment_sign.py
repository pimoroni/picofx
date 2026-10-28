import random
from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import Screen280
from picovector import color, image, rect, shape, vec2

"""
Draw an LED sign of fourteen-segment characters, three rows of them in windows set into a
brushed metal case. A row too long for its window scrolls through it.

Fourteen segments split a seven-segment digit's middle bar in two and add a vertical in two
halves and four diagonals, which is enough to spell. Every segment, lit or not, is drawn once into
the background every frame starts from, so an unlit one still shows faintly through the window.
METAL_CASE = False leaves the windows bare on black.

Press "Boot" to exit the program.

Section: Mechanical and glowing displays
"""

# What the sign shows, a launch control panel's readouts, a page at a time with a line to each row.
# A full stop lights the decimal point of the character before it, so it takes no place of its own
PAGES = (
    ("LAUNCH", "CONTROL", "READY"),
    ("T-MINUS", "00.10.00", "HOLD"),
    ("FUEL", "98.5 PCT", "NOMINAL"),
    ("RANGE", "WEATHER", "WINDS 12 KNOTS WITHIN LIMITS"),
    ("MAIN", "ENGINE", "START"),
    ("WE HAVE", "LIFTOFF", "T+00.01"),
)
HOLD_MS = 2000                      # How long a page holds before its rows scroll, and again after
SCROLL_MS = 250                     # How long a scrolling row holds each step

# Constants for drawing
COLUMNS = 7                         # Characters across each row

# A segment is set out in a character one unit wide between its outer bars' centres, and this many tall
CHARACTER_TALL = 1.6
STROKE = 0.14                       # How thick a bar is
SEGMENT_GAP = 0.03                  # Between one bar and the next, along the line they meet on
DIAGONAL = 0.09                     # How wide a diagonal is, along a row
POINT = 0.09                        # The decimal point's radius
SLANT = 0.1                         # How far the top of a character leans over its foot, per unit of height
SPACING = 0.32                      # Between one character and the next, the decimal point sitting in it
ANTIALIAS = image.X4                # A diagonal is all edge

# The case
METAL_CASE = True                   # Whether the windows are set into a brushed metal case, or stand bare on black
BORDER = 8                          # Panel pixels between the panel's edge and the windows
WINDOW_GAP = 10                     # Between one window and the next
WINDOW_PAD = 4                      # Between a window's edge and its characters
CORNER = 4                          # How far a window's corners are rounded
METAL = color.rgb(85, 85, 102)      # The case, a gunmetal brushed metal
BRIGHTER = color.rgb(136, 136, 153).with_alpha(60)  # A brush mark catching the light
DARKER = color.rgb(34, 34, 51).with_alpha(60)       # And one in shadow
STREAKS = 4                         # Brush marks a row of the metal carries
EDGE_LIT = color.rgb(153, 153, 170)         # An edge facing up and to the left, the light being above
EDGE_SHADED = color.rgb(17, 17, 17)         # And one facing away from it

# The colour each row's lit segments glow, top row first, which its window and unlit segments take
# theirs from. Red, green and amber, and a row more for each colour added
LEDS = ((255, 34, 17), (51, 255, 68), (255, 153, 0))
ROWS = len(LEDS)


def dimmed(led, fraction):
    """
    Calculate an LED's colour at a fraction of its brightness.

    The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so each channel is
    rounded to a level.
    """
    return color.rgb(*(round(channel * fraction / 17) * 17 for channel in led))


# A row's colours, a list of each with one entry a row
LIT = [color.rgb(*led) for led in LEDS]             # A segment carrying current
GHOST = [dimmed(led, 0.267) for led in LEDS]        # One that is not, seen through the window
FILTER = [dimmed(led, 0.067) for led in LEDS]       # A window, a filter in the LED's colour
KEYLINE = [dimmed(led, 0.267) for led in LEDS]      # A bare window's edge, which finds it against the black

# Which bars each character lights, named as a display's datasheet commonly names them
#
#    aaaaaaa
#   f h i j b
#   f  hij  b
#    g1   g2
#   e  klm  c
#   e k l m c
#    ddddddd
LIGHTS = {
    " ": "",
    "A": "a b c e f g1 g2", "B": "a b c d i l g2", "C": "a d e f", "D": "a b c d i l",
    "E": "a d e f g1", "F": "a e f g1", "G": "a c d e f g2", "H": "b c e f g1 g2",
    "I": "a d i l", "J": "b c d e", "K": "e f g1 j m", "L": "d e f",
    "M": "b c e f h j", "N": "b c e f h m", "O": "a b c d e f", "P": "a b e f g1 g2",
    "Q": "a b c d e f m", "R": "a b e f g1 g2 m", "S": "a c d f g1 g2", "T": "a i l",
    "U": "b c d e f", "V": "e f j k", "W": "b c e f k m", "X": "h j k m",
    "Y": "h j l", "Z": "a d j k",
    "0": "a b c d e f j k", "1": "b c j", "2": "a b d e g1 g2", "3": "a b c d g2",
    "4": "b c f g1 g2", "5": "a c d f g1 g2", "6": "a c d e f g1 g2", "7": "a b c",
    "8": "a b c d e f g1 g2", "9": "a b c d f g1 g2",
    "-": "g1 g2", "+": "g1 g2 i l", "*": "g1 g2 h i j k l m", "/": "j k",
    "<": "j m", ">": "h k", "=": "d g1 g2", "_": "d", "'": "i",
}
LIGHTS = {character: tuple(names.split()) for character, names in LIGHTS.items()}

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Drawn landscape and turned a quarter onto the panel at each update
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height
canvas.antialias = ANTIALIAS

HALF = STROKE / 2
MIDDLE = CHARACTER_TALL / 2


def bar(x0, y0, x1, y1):
    """Outline a bar between two points on a row or a column, pointed at both ends so neighbours meet on a mitre."""
    if y0 == y1:
        x0, x1 = x0 + SEGMENT_GAP, x1 - SEGMENT_GAP
        return ((x0, y0), (x0 + HALF, y0 - HALF), (x1 - HALF, y0 - HALF),
                (x1, y0), (x1 - HALF, y0 + HALF), (x0 + HALF, y0 + HALF))

    y0, y1 = y0 + SEGMENT_GAP, y1 - SEGMENT_GAP
    return ((x0, y0), (x0 + HALF, y0 + HALF), (x0 + HALF, y1 - HALF),
            (x0, y1), (x0 - HALF, y1 - HALF), (x0 - HALF, y0 + HALF))


def diagonal():
    """
    Outline the upper left diagonal, from the corner of the bars around it to the middle of the character.

    Both ends are cut along the bars they meet, and the band's sides run parallel to the line between
    its corners, so it is as wide all the way along.
    """
    inset = HALF + SEGMENT_GAP
    left, top = inset, inset
    right, bottom = 0.5 - inset, MIDDLE - inset
    across = DIAGONAL
    down = DIAGONAL * (bottom - top) / (right - left)
    return ((left, top), (left + across, top), (right, bottom - down),
            (right, bottom), (right - across, bottom), (left, top + down))


UPPER_LEFT = diagonal()
OUTLINES = {
    "a": bar(0, 0, 1, 0),
    "b": bar(1, 0, 1, MIDDLE),
    "c": bar(1, MIDDLE, 1, CHARACTER_TALL),
    "d": bar(0, CHARACTER_TALL, 1, CHARACTER_TALL),
    "e": bar(0, MIDDLE, 0, CHARACTER_TALL),
    "f": bar(0, 0, 0, MIDDLE),
    "g1": bar(0, MIDDLE, 0.5, MIDDLE),
    "g2": bar(0.5, MIDDLE, 1, MIDDLE),
    "i": bar(0.5, 0, 0.5, MIDDLE),
    "l": bar(0.5, MIDDLE, 0.5, CHARACTER_TALL),
    # The other three diagonals are the first mirrored across the character, down it, or both
    "h": UPPER_LEFT,
    "j": tuple((1 - x, y) for x, y in UPPER_LEFT),
    "k": tuple((x, CHARACTER_TALL - y) for x, y in UPPER_LEFT),
    "m": tuple((1 - x, CHARACTER_TALL - y) for x, y in UPPER_LEFT),
}

# A character's outer edges reach half a bar past the unit square, and its decimal point sits in the
# spacing after it. The windows share the panel's height
CHARACTER_W = 1 + STROKE
UNITS_W = COLUMNS * (CHARACTER_W + SPACING)
UNITS_H = CHARACTER_TALL + STROKE
WINDOW_W = WIDTH - BORDER * 2
WINDOW_H = (HEIGHT - BORDER * 2 - WINDOW_GAP * (ROWS - 1)) // ROWS
SCALE = min((WINDOW_W - WINDOW_PAD * 2) / UNITS_W, (WINDOW_H - WINDOW_PAD * 2) / UNITS_H)
LEFT = BORDER + (WINDOW_W - UNITS_W * SCALE) / 2

windows = [rect(BORDER, BORDER + row * (WINDOW_H + WINDOW_GAP), WINDOW_W, WINDOW_H) for row in range(ROWS)]


def placed(outline, across, top):
    """Turn an outline in a character's units into panel points, for a character this many units from the left."""
    return [vec2(LEFT + (across + HALF + x + SLANT * (CHARACTER_TALL - y)) * SCALE,
                 top + (HALF + y) * SCALE) for x, y in outline]


# Every bar of every character on the sign made once, a shape built per frame being an allocation. A
# character's bars are keyed by name, with its decimal point as "dp"
cells = []
for window in windows:
    top = window.y + (WINDOW_H - UNITS_H * SCALE) / 2
    row = []
    for column in range(COLUMNS):
        across = column * (CHARACTER_W + SPACING)
        bars = {name: shape.custom(placed(outline, across, top)) for name, outline in OUTLINES.items()}
        point = placed(((1 + HALF + SPACING / 2, CHARACTER_TALL),), across, top)[0]
        bars["dp"] = shape.circle(point.x, point.y, POINT * SCALE)
        row.append(bars)
    cells.append(row)

print(f"{ROWS} rows of {COLUMNS}, {CHARACTER_W * SCALE:.0f}x{UNITS_H * SCALE:.0f}px a character")


def characters(text):
    """Split a row's text into what each place on the sign shows, a character and whether its point is lit."""
    places = []
    for character in text.upper():
        if character == ".":
            # A point with nothing before it to carry it, or one already lit, takes a blank place of its own
            if not places or places[-1][1]:
                places.append((" ", True))
            else:
                places[-1] = (places[-1][0], True)
        elif character in LIGHTS:
            places.append((character, False))
        else:
            raise ValueError(f"'{character}' in \"{text}\" has no segments to show it. Use letters, digits, spaces, full stops or - + * / < > = _ '")

    # A row that fits is centred in its window
    spare = max(0, COLUMNS - len(places))
    return [(" ", False)] * (spare // 2) + places + [(" ", False)] * (spare - spare // 2)


pages = [[characters(text) for text in page] for page in PAGES]


def page_ms(page):
    """Calculate how long a page shows, holding before and after its longest row scrolls through."""
    longest = max(len(row) for row in page)
    return HOLD_MS + (longest - COLUMNS) * SCROLL_MS + HOLD_MS


def scrolled(row, into):
    """Find how many places a row has scrolled, this many milliseconds into its page."""
    return max(0, min(len(row) - COLUMNS, (into - HOLD_MS) // SCROLL_MS))


# The background every frame starts from, the case with its windows and every segment unlit
background = image(WIDTH, HEIGHT)
background.antialias = ANTIALIAS
background.pen = METAL if METAL_CASE else color.black
background.clear()

if METAL_CASE:
    # Brush marks run along the rows, a few to each and in no pattern, which is what reads as brushed.
    # Seeded, so the case is the same every time it runs
    random.seed(1)
    for y in range(HEIGHT):
        for _ in range(STREAKS):
            background.pen = BRIGHTER if random.getrandbits(1) else DARKER
            # A mark can start up to its own length off the left edge, so the marks are as dense there as
            # anywhere, hspan() clipping it to the panel
            length = random.randrange(20, 120)
            background.hspan(random.randrange(-length, WIDTH), y, length)

for index, window in enumerate(windows):
    if METAL_CASE:
        # A window is set in, so its edge is shaded along the top and lit along the bottom
        background.pen = EDGE_SHADED
        background.shape(shape.rounded_rectangle(rect(window.x - 2, window.y - 2, window.w + 2, window.h + 2),
                                                 CORNER, CORNER, CORNER, CORNER))
        background.pen = EDGE_LIT
        background.shape(shape.rounded_rectangle(rect(window.x, window.y, window.w + 2, window.h + 2),
                                                 CORNER, CORNER, CORNER, CORNER))
    else:
        background.pen = KEYLINE[index]
        background.shape(shape.rounded_rectangle(rect(window.x - 1, window.y - 1, window.w + 2, window.h + 2),
                                                 CORNER, CORNER, CORNER, CORNER))
    background.pen = FILTER[index]
    background.shape(shape.rounded_rectangle(window, CORNER, CORNER, CORNER, CORNER))

for ghost, row in zip(GHOST, cells):
    background.pen = ghost
    for bars in row:
        for segment in bars.values():
            background.shape(segment)


def draw(page, offsets):
    """Draw one frame, the background with the segments each place on the sign lights over it."""
    # Cleared under first. The background's blended pixels fall a little short of opaque, so without the
    # clear the previous frame shows through them
    canvas.pen = color.black
    canvas.clear()
    canvas.blit(background, 0, 0)

    for lit, row, places, offset in zip(LIT, cells, page, offsets):
        canvas.pen = lit
        for bars, (character, point) in zip(row, places[offset:offset + COLUMNS]):
            for name in LIGHTS[character]:
                canvas.shape(bars[name])
            if point:
                canvas.shape(bars["dp"])


page_index = 0
started = 0                         # When the page showing came up, on the pacer's clock
shown = None
pacer = Pacer(0.01)                 # The sign's clock, looking for a change every 10ms

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        now = pacer.elapsed
        if now - started >= page_ms(pages[page_index]):
            page_index = (page_index + 1) % len(pages)
            started = now

        page = pages[page_index]
        offsets = tuple(scrolled(row, now - started) for row in page)
        if (page_index, offsets) != shown:
            draw(page, offsets)
            screen.update(canvas, rotation=90)
            shown = (page_index, offsets)

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
