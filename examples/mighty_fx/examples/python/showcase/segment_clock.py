import random
from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import Screen280
from picovector import color, font, image, rect, shape, vec2

"""
Draw an LED seven-segment clock, its digits made of bars lit behind a coloured filter.

Every segment, lit or not, is drawn once into the background every frame starts from, which is
how an unlit segment still shows faintly through the filter. A frame is that background with the
lit segments over it.

The window is set into a brushed gunmetal case, printed with what each pair of digits shows, as an
instrument panel would be. METAL_CASE = False leaves it bare on black.

Press "Boot" to exit the program.

Section: Mechanical and glowing displays
"""

# Constants for drawing
CLOCK_START = (11, 32, 45)          # The time it counts on from, Mighty FX having no clock to read
BLANK_LEADING_ZERO = True           # Whether an hour under ten shows one digit, as an LED clock's does
SECONDS = True                      # Whether the seconds show, the hours and minutes drawing larger without them
COLON_MS = 500                      # How long the colons stay lit each second

# A segment is set out in a digit one unit wide between its outer bars' centres, and this many tall
DIGIT_TALL = 1.8
STROKE = 0.2                        # How thick a bar is
SEGMENT_GAP = 0.035                 # Between one bar and the next, along the line they meet on
SLANT = 0.1                         # How far the top of a digit leans over its foot, per unit of height
SPACING = 0.3                       # Between one digit and the next
COLON_SPACING = 0.35                # And added either side of a colon
MARGIN = 8                          # Panel pixels around the window, and between it and the digits
CORNER = 4                          # How far the window's corners are rounded

# The colour a lit segment glows, which the filter and the unlit segments take theirs from.
# (255, 153, 0) is an amber display and (51, 255, 68) a green one
LED = (255, 34, 17)


def dimmed(fraction):
    """
    Calculate the LED's colour at a fraction of its brightness.

    The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so each channel is
    rounded to a level.
    """
    return color.rgb(*(round(channel * fraction / 17) * 17 for channel in LED))


LIT = color.rgb(*LED)               # A segment carrying current
GHOST = dimmed(0.267)               # One that is not, seen through the filter
FILTER = dimmed(0.067)              # The filter itself, filling the window
KEYLINE = dimmed(0.267)             # A bare window's edge, which finds it against the black
CASE = color.black
ANTIALIAS = image.X4                # Every bar is slanted, so its edges want smoothing

# The metal case
METAL_CASE = True                   # Whether the window is set into a brushed metal case, or stands bare on black
METAL = color.rgb(85, 85, 102)      # The case, a gunmetal brushed metal
BRIGHTER = color.rgb(136, 136, 153).with_alpha(60)  # A brush mark catching the light
DARKER = color.rgb(34, 34, 51).with_alpha(60)       # And one in shadow
STREAKS = 4                         # Brush marks a row of the metal carries
EDGE_LIT = color.rgb(153, 153, 170)         # An edge facing up and to the left, the light being above
EDGE_SHADED = color.rgb(17, 17, 17)         # And one facing away from it
LABELS = ("HOUR", "MIN", "SEC")     # Printed over each pair of digits
CAPTION = "PRESENT TIME"            # And under the window
LABEL_FONT = "/rom/fonts/Oswald.af"  # A condensed face, so a label sits over its pair of digits
LABEL_SIZE = 22                     # The lettering's em height, in panel pixels
PLAQUE = color.rgb(153, 34, 34)     # The red a label is printed on
CAPTION_PLATE = color.black         # And the plate the caption is printed on
LETTERING = color.rgb(238, 238, 221)
PLATE_PAD = 4                       # Panel pixels around the lettering on a plate
PLATE_GAP = 8                       # Between a plate and the window

# Which bars each character lights, named a to g as a display's datasheet names them
#
#    aaaaaaa
#   f       b
#   f       b
#    ggggggg
#   e       c
#   e       c
#    ddddddd
LIGHTS = {
    " ": (),
    "0": ("a", "b", "c", "d", "e", "f"),
    "1": ("b", "c"),
    "2": ("a", "b", "g", "e", "d"),
    "3": ("a", "b", "g", "c", "d"),
    "4": ("f", "g", "b", "c"),
    "5": ("a", "f", "g", "c", "d"),
    "6": ("a", "f", "g", "e", "d", "c"),
    "7": ("a", "b", "c"),
    "8": ("a", "b", "c", "d", "e", "f", "g"),
    "9": ("a", "b", "c", "d", "f", "g"),
}

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Drawn landscape and turned a quarter onto the panel at each update
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height
canvas.antialias = ANTIALIAS

HALF = STROKE / 2
MIDDLE = DIGIT_TALL / 2


def bar(x0, y0, x1, y1):
    """Outline a bar between two points on a row or a column, pointed at both ends so neighbours meet on a mitre."""
    if y0 == y1:
        x0, x1 = x0 + SEGMENT_GAP, x1 - SEGMENT_GAP
        return ((x0, y0), (x0 + HALF, y0 - HALF), (x1 - HALF, y0 - HALF),
                (x1, y0), (x1 - HALF, y0 + HALF), (x0 + HALF, y0 + HALF))

    y0, y1 = y0 + SEGMENT_GAP, y1 - SEGMENT_GAP
    return ((x0, y0), (x0 + HALF, y0 + HALF), (x0 + HALF, y1 - HALF),
            (x0, y1), (x0 - HALF, y1 - HALF), (x0 - HALF, y0 + HALF))


OUTLINES = {
    "a": bar(0, 0, 1, 0),
    "b": bar(1, 0, 1, MIDDLE),
    "c": bar(1, MIDDLE, 1, DIGIT_TALL),
    "d": bar(0, DIGIT_TALL, 1, DIGIT_TALL),
    "e": bar(0, MIDDLE, 0, DIGIT_TALL),
    "f": bar(0, 0, 0, MIDDLE),
    "g": bar(0, MIDDLE, 1, MIDDLE),
}

DIGITS = 6 if SECONDS else 4
COLONS = (1, 3) if SECONDS else (1,)    # The digits a colon follows

# A digit's outer edges reach half a bar past the unit square, and its top leans the slant further over
DIGIT_W = 1 + STROKE + SLANT * DIGIT_TALL
UNITS_W = DIGITS * DIGIT_W + (DIGITS - 1) * SPACING + len(COLONS) * COLON_SPACING * 2
UNITS_H = DIGIT_TALL + STROKE
SCALE = min((WIDTH - MARGIN * 4) / UNITS_W, (HEIGHT - MARGIN * 4) / UNITS_H)
LEFT = (WIDTH - UNITS_W * SCALE) / 2
TOP = (HEIGHT - UNITS_H * SCALE) / 2


def placed(outline, across):
    """Turn an outline in a digit's units into panel points, for a digit this many units from the left."""
    return [vec2(LEFT + (across + HALF + x + SLANT * (DIGIT_TALL - y)) * SCALE,
                 TOP + (HALF + y) * SCALE) for x, y in outline]


# Every bar of every digit made once, a shape built per frame being an allocation
digits = []
colons = []
starts = []                         # Where each digit's box starts across the panel
across = 0
for position in range(DIGITS):
    digits.append({name: shape.custom(placed(outline, across)) for name, outline in OUTLINES.items()})
    starts.append(LEFT + across * SCALE)
    across += DIGIT_W + SPACING

    # A colon is two dots in the gap after its digit, leaning with the digits
    if position in COLONS:
        across += COLON_SPACING
        for y in (MIDDLE * 0.6, MIDDLE * 1.4):
            x = LEFT + (across - SPACING / 2 + SLANT * (MIDDLE - y)) * SCALE
            colons.append(shape.circle(x, TOP + (HALF + y) * SCALE, STROKE * 0.6 * SCALE))
        across += COLON_SPACING

print(f"{DIGITS} digits, {DIGIT_W * SCALE:.0f}x{UNITS_H * SCALE:.0f}px each")

# The background every frame starts from, the case with the filter's window and every segment unlit
background = image(WIDTH, HEIGHT)
background.antialias = ANTIALIAS
background.pen = METAL if METAL_CASE else CASE
background.clear()

window = rect(MARGIN, round(TOP - MARGIN), WIDTH - MARGIN * 2, round(UNITS_H * SCALE + MARGIN * 2))


def capital_rows():
    """
    Measure the first and last rows a capital fills, below the y it is drawn at.

    Read off a drawing, as the face's em box leaves room above its capitals for accents. A row counts
    where it is at least half covered, so a faint antialiased edge weighs the same at the top as the foot.
    """
    probe = image(LABEL_SIZE * 2, LABEL_SIZE * 2)
    probe.raw[:] = bytes(len(probe.raw))
    probe.font = background.font
    probe.antialias = ANTIALIAS
    probe.pen = color.white
    probe.text("H", 0, 0, LABEL_SIZE)

    raw, stride = probe.raw, probe.stride
    filled = [y for y in range(probe.height)
              if any(raw[y * stride + x * 4 + 3] >= 128 for x in range(probe.width))]
    return filled[0], filled[-1]


def plate(text, centre_x, top, fill):
    """Print lettering onto the case on a plate of its own, centred across the panel on centre_x."""
    wide = background.measure_text(text, font_size=LABEL_SIZE)[0]
    background.pen = fill
    background.shape(shape.rounded_rectangle(rect(round(centre_x - wide / 2 - PLATE_PAD), top,
                                                  round(wide + PLATE_PAD * 2), PLATE_H), 2, 2, 2, 2))
    background.pen = LETTERING
    background.text(text, centre_x - wide / 2, top + PLATE_PAD - CAPITAL_TOP, LABEL_SIZE)


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

    # The window is set in, so its edge is shaded along the top and lit along the bottom
    background.pen = EDGE_SHADED
    background.shape(shape.rounded_rectangle(rect(window.x - 2, window.y - 2, window.w + 2, window.h + 2),
                                             CORNER, CORNER, CORNER, CORNER))
    background.pen = EDGE_LIT
    background.shape(shape.rounded_rectangle(rect(window.x, window.y, window.w + 2, window.h + 2),
                                             CORNER, CORNER, CORNER, CORNER))

    # A plate holds its lettering's capitals with the same space above as below
    background.font = font.load(LABEL_FONT)
    CAPITAL_TOP, CAPITAL_BOTTOM = capital_rows()
    PLATE_H = CAPITAL_BOTTOM - CAPITAL_TOP + 1 + PLATE_PAD * 2
    for pair, label in enumerate(LABELS[:DIGITS // 2]):
        centre_x = (starts[pair * 2] + starts[pair * 2 + 1] + DIGIT_W * SCALE) / 2
        plate(label, centre_x, window.y - PLATE_GAP - PLATE_H, PLAQUE)
    plate(CAPTION, WIDTH / 2, window.y + window.h + PLATE_GAP, CAPTION_PLATE)
else:
    background.pen = KEYLINE
    background.shape(shape.rounded_rectangle(rect(window.x - 1, window.y - 1, window.w + 2, window.h + 2),
                                             CORNER, CORNER, CORNER, CORNER))
background.pen = FILTER
background.shape(shape.rounded_rectangle(window, CORNER, CORNER, CORNER, CORNER))

background.pen = GHOST
for bars in digits:
    for segment in bars.values():
        background.shape(segment)
for dot in colons:
    background.shape(dot)


def clock_now(elapsed):
    """Calculate the time the clock is showing, counted on from CLOCK_START, a character a digit."""
    elapsed //= 1000
    hours, minutes, seconds = CLOCK_START
    total = (hours * 3600 + minutes * 60 + seconds + elapsed) % 86400
    reading = f"{total // 3600:02d}{total // 60 % 60:02d}{total % 60:02d}"
    if BLANK_LEADING_ZERO and reading[0] == "0":
        reading = " " + reading[1:]
    return reading[:DIGITS]


def draw(reading, colons_lit):
    """Draw one frame, the background with the segments each character lights over it."""
    # Cleared under first. The background's blended pixels fall a little short of opaque, so without the
    # clear the previous frame shows through them
    canvas.pen = CASE
    canvas.clear()
    canvas.blit(background, 0, 0)

    canvas.pen = LIT
    for bars, character in zip(digits, reading):
        for name in LIGHTS[character]:
            canvas.shape(bars[name])
    if colons_lit:
        for dot in colons:
            canvas.shape(dot)


shown = None
pacer = Pacer(0.01)                 # The clock's pace, looking for a change every 10ms

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = pacer.elapsed
        showing = (clock_now(elapsed), elapsed % 1000 < COLON_MS)
        if showing != shown:
            draw(*showing)
            screen.update(canvas, rotation=90)
            shown = showing

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
