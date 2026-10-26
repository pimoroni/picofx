import math
import random
from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import Screen280
from picovector import color, font, image, mat3, rect, shape

"""
Draw a mechanical odometer, a row of number drums in a brass frame. The last drum turns
steadily, and each of the others is carried round as the drum to its right passes from 9 to 0.

A drum's ten digits are drawn once, flat, as a strip as long as its circumference. Each row of the
drum on screen then copies the row of the strip that faces it on the curve, which crowds the digits
together towards the top and bottom, as a real drum does.

Press "Boot" to exit the program.
"""

# Constants for drawing
START = 429996                                      # The reading it counts on from, the last drum being tenths
SPEED = 1.5                                         # How fast the last drum turns, in digits a second
DRUMS = 6
MAKER = "PIMORONI & CO."                            # Engraved above the drums
UNITS = ("MILES", "TENTHS")                         # And under them, the first under the whole miles and the second under the tenths

DRUM_W = 44                                         # Panel pixels across a drum
DRUM_GAP = 4                                        # Between one drum and the next
DRUM_H = 130                                        # How much of a drum shows, top to bottom
VIEW = 30                                           # How far round the drum shows above and below its middle, in degrees
DIGIT_FILL = 0.62                                   # How much of a digit's place on the drum its lettering fills
DIGIT_FONT = "/rom/fonts/Oswald.af"
ANTIALIAS = image.X4

# The screens drive the panel at 12 bit, 16 levels a channel in steps of 17, so the colours below sit
# on those levels
FACE = (221, 221, 204)                              # A drum's face
DIGIT = color.rgb(17, 17, 17)                       # And the digits printed on it
LAST_DIGIT = color.rgb(204, 17, 17)                 # The last drum's digits, printed red
INSIDE = color.rgb(17, 17, 17)                      # The dark inside the opening, between the drums
DRUM_FALLOFF = 0.7                                  # How dark a drum gets at the top and bottom of what shows, 1 being black

# The brass frame
BRASS = color.rgb(170, 136, 68)
BRIGHTER = color.rgb(221, 187, 119).with_alpha(30)  # A brush mark catching the light, faint so the brass reads as metal
DARKER = color.rgb(119, 85, 34).with_alpha(30)      # And one in shadow
STREAKS = 4                                         # Brush marks a row of the brass carries
EDGE_LIT = color.rgb(238, 204, 136)                 # An edge facing up and to the left, the light being above
EDGE_SHADED = color.rgb(68, 51, 17)                 # And one facing away from it
ENGRAVED = color.rgb(85, 68, 34)                    # Lettering cut into the brass
ENGRAVE_SIZE = 20                                   # Its em height, in panel pixels
ENGRAVE_GAP = 6                                     # Between the lettering and the opening
OPENING_PAD = 6                                     # Panel pixels between the drums and the opening's edge
CORNER = 6                                          # How far the opening's corners are rounded
SCREW = 9                                           # A screw head's radius, in panel pixels
SCREW_INSET = 14                                    # From the panel's edge to a screw's middle
SCREW_RIM = color.rgb(238, 238, 238)                # The steel head's edge, catching the light
SCREW_HEAD = color.rgb(153, 153, 170)               # And its dome
SCREW_SLOT = color.rgb(51, 51, 51)
SLOTS = (30, 110, 165, 75)                          # Each screw's slot, in degrees, tightened by hand so no two alike

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Drawn landscape and turned a quarter onto the panel at each update
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height
canvas.antialias = ANTIALIAS

# The drum's radius follows from how much of it shows, and its strip is as long as its circumference
RADIUS = DRUM_H / 2 / math.sin(math.radians(VIEW))
STRIP_H = round(2 * math.pi * RADIUS)
CELL_H = STRIP_H / 10               # A digit's place on the drum
DRUMS_W = DRUMS * DRUM_W + (DRUMS - 1) * DRUM_GAP
LEFT = (WIDTH - DRUMS_W) // 2
TOP = (HEIGHT - DRUM_H) // 2
digit_font = font.load(DIGIT_FONT)


def digit_rows(size):
    """
    Measure the first and last rows a digit fills, below the y it is drawn at.

    Read off a drawing, as the face's em box leaves room above its capitals for accents. A row counts
    where it is at least half covered, so a faint antialiased edge weighs the same at the top as the foot.
    """
    probe = image(round(size) * 2, round(size) * 2)
    probe.raw[:] = bytes(len(probe.raw))
    probe.font = digit_font
    probe.antialias = ANTIALIAS
    probe.pen = color.white
    probe.text("0", 0, 0, size)

    raw, stride = probe.raw, probe.stride
    filled = [y for y in range(probe.height)
              if any(raw[y * stride + x * 4 + 3] >= 128 for x in range(probe.width))]
    return filled[0], filled[-1]


def printed(ink):
    """Draw a drum's ten digits flat, one above the next, on a strip as long as the drum is round."""
    strip = image(DRUM_W, STRIP_H)
    strip.antialias = ANTIALIAS
    strip.pen = color.rgb(*FACE)
    strip.clear()
    strip.font = digit_font
    strip.pen = ink
    for digit in range(10):
        wide = strip.measure_text(str(digit), font_size=SIZE)[0]
        strip.text(str(digit), (DRUM_W - wide) / 2, digit * CELL_H + (CELL_H - DIGIT_INK) / 2 - INK_TOP, SIZE)
    return strip


# The digits are sized on their drawn height, a face's size being its em box
top, bottom = digit_rows(100)
SIZE = 100 * CELL_H * DIGIT_FILL / (bottom - top + 1)
INK_TOP, ink_bottom = digit_rows(SIZE)
DIGIT_INK = ink_bottom - INK_TOP + 1
strips = [printed(DIGIT)] * (DRUMS - 1) + [printed(LAST_DIGIT)]

# Where on its strip each row of a drum looks, as an arc's length from the drum's middle. A row at a
# distance from the middle sees the drum at the angle whose sine is that distance over the radius
facing = [RADIUS * math.asin((row + 0.5 - DRUM_H / 2) / RADIUS) for row in range(DRUM_H)]

# The shade over a drum, the same for every drum and drawn once. It darkens as the drum turns away
# from the panel, leaving the drum's middle row the brightest. A row's brightness falls between two of
# the panel's levels, so its pixels are spread between both in a fixed 4x4 pattern, an ordered dither,
# where one level to a row would show as bands
DITHER = (0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)
shade = image(DRUM_W, DRUM_H)
shade.raw[:] = bytes(len(shade.raw))
for row, arc in enumerate(facing):
    darkened = DRUM_FALLOFF * (1 - math.cos(arc / RADIUS)) / (1 - math.cos(math.radians(VIEW)))
    brightness = FACE[0] * (1 - darkened)

    below = int(brightness // 17) * 17
    for x in range(DRUM_W):
        level = below + 17 if (DITHER[row % 4 * 4 + x % 4] + 0.5) / 16 < (brightness - below) / 17 else below
        # Whether the pixel falls below the face's own level
        if level < FACE[0]:
            # Laid over with just enough black to bring the face down to it
            shade.pen = color.black.with_alpha(round(255 * (1 - level / FACE[0])))
            shade.hspan(x, row, 1)

print(f"{DRUMS} drums of {DRUM_W}x{DRUM_H}, radius {RADIUS:.0f}, digits {DIGIT_INK}px tall")

# The rows a drum is copied through, made once, a rect built per row being an allocation
source = rect(0, 0, DRUM_W, 1)
target = rect(0, 0, DRUM_W, 1)


def draw_drum(drum, turned):
    """Draw a drum turned this many digits round from 0, copying each row from where it faces on the strip."""
    strip = strips[drum]
    middle = turned * CELL_H + CELL_H / 2
    target.x = LEFT + drum * (DRUM_W + DRUM_GAP)
    for row, arc in enumerate(facing):
        source.y = int((middle + arc) % STRIP_H)
        target.y = TOP + row
        canvas.blit(strip, source, target)
    canvas.blit(shade, target.x, TOP)


def positions(whole, fraction):
    """
    Calculate how far round each drum has turned, left to right, for a count in the last drum's units.

    A drum is carried round while the drum to its right turns from 9 to 0, so a run of nines rolls over
    together.
    """
    turned = [whole % 10 + fraction]
    for place in range(1, DRUMS):
        digit = whole // 10 ** place % 10
        carried = max(0, turned[-1] - 9)
        turned.append(digit + carried)
    turned.reverse()
    return turned


# The frame is drawn once, straight onto the canvas, as only the drums change from then on
canvas.pen = BRASS
canvas.clear()

# Brush marks run along the rows, a few to each and in no pattern, which is what reads as brushed.
# Seeded, so the frame is the same every time it runs
random.seed(1)
for y in range(HEIGHT):
    for _ in range(STREAKS):
        canvas.pen = BRIGHTER if random.getrandbits(1) else DARKER
        # A mark can start up to its own length off the left edge, so the marks are as dense there as
        # anywhere, hspan() clipping it to the panel
        length = random.randrange(20, 120)
        canvas.hspan(random.randrange(-length, WIDTH), y, length)

# The opening is cut into the frame, so its edge is shaded along the top and lit along the bottom
opening = rect(LEFT - OPENING_PAD, TOP - OPENING_PAD, DRUMS_W + OPENING_PAD * 2, DRUM_H + OPENING_PAD * 2)
canvas.pen = EDGE_SHADED
canvas.shape(shape.rounded_rectangle(rect(opening.x - 2, opening.y - 2, opening.w + 2, opening.h + 2),
                                     CORNER, CORNER, CORNER, CORNER))
canvas.pen = EDGE_LIT
canvas.shape(shape.rounded_rectangle(rect(opening.x, opening.y, opening.w + 2, opening.h + 2),
                                     CORNER, CORNER, CORNER, CORNER))
canvas.pen = INSIDE
canvas.shape(shape.rounded_rectangle(opening, CORNER, CORNER, CORNER, CORNER))

# A steel screw in each corner, its domed head casting a shadow on the brass
corners = [(x, y) for x in (SCREW_INSET, WIDTH - SCREW_INSET) for y in (SCREW_INSET, HEIGHT - SCREW_INSET)]
for (x, y), slot_angle in zip(corners, SLOTS):
    canvas.pen = EDGE_SHADED
    canvas.shape(shape.circle(x + 1, y + 1, SCREW))
    canvas.pen = SCREW_RIM
    canvas.shape(shape.circle(x, y, SCREW))
    canvas.pen = SCREW_HEAD
    canvas.shape(shape.circle(x + 0.5, y + 0.5, SCREW - 1))
    slot = shape.rectangle(-SCREW + 1, -1, SCREW * 2 - 2, 2)
    slot.transform = mat3().translate(x, y).rotate(slot_angle)
    canvas.pen = SCREW_SLOT
    canvas.shape(slot)


def engrave(text, centre_x, top):
    """
    Cut lettering into the brass, centred across the panel on centre_x with its capitals' tops at top.

    A cut catches the light along its lower edge, so the lettering is drawn first a pixel lower and to
    the right in the lit edge's colour.
    """
    wide = canvas.measure_text(text, font_size=ENGRAVE_SIZE)[0]
    x, y = centre_x - wide / 2, top - ENGRAVE_TOP
    canvas.pen = EDGE_LIT
    canvas.text(text, x + 1, y + 1, ENGRAVE_SIZE)
    canvas.pen = ENGRAVED
    canvas.text(text, x, y, ENGRAVE_SIZE)


# The maker's line above the drums and the units under them. A digit stands as tall as a capital in
# this face, so digit_rows() measures the lettering's height too
canvas.font = digit_font
ENGRAVE_TOP, engrave_bottom = digit_rows(ENGRAVE_SIZE)
engrave(MAKER, WIDTH / 2, opening.y - ENGRAVE_GAP - (engrave_bottom - ENGRAVE_TOP + 1))
last_drum = LEFT + (DRUMS - 1) * (DRUM_W + DRUM_GAP)
engrave(UNITS[0], (LEFT + last_drum - DRUM_GAP) / 2, opening.y + opening.h + ENGRAVE_GAP)
engrave(UNITS[1], last_drum + DRUM_W / 2, opening.y + opening.h + ENGRAVE_GAP)

PACE = round(SPEED * 1000)          # The last drum's speed in thousandths of a digit a second
shown = [None] * DRUMS
pacer = Pacer(0.01)                 # The odometer's clock, looking for a change every 10ms

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Counted in thousandths of a digit as a whole number. As one float the distance would lose
        # the part of a digit within hours, and the last drum would turn in visible steps
        whole, thousandths = divmod(pacer.elapsed * PACE // 1000, 1000)
        turned = positions(START + whole, thousandths / 1000)

        moved = False
        for drum in range(DRUMS):
            if turned[drum] != shown[drum]:
                draw_drum(drum, turned[drum])
                shown[drum] = turned[drum]
                moved = True

        if moved:
            screen.update(canvas, rotation=90)

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
