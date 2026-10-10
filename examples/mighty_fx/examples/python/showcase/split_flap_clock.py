import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import color, font, image, rect, shape

"""
Draw a split-flap clock, its digits climbing through the drum a flap at a time as a real
board does.

Press "Boot" to exit the program.
"""

# Constants for drawing
FLAP_FONT = "/rom/fonts/AdventPro-Medium.af"  # A vector face, so it sizes to the card
DRUM = " 0123456789"                # What is on a card, in the order it comes round
CLOCK_START = (11, 32, 45)          # The time it counts on from, MightyFX having no clock to read
FLAP_MS = 260                       # How long one card takes to fall
# A card sits two levels above the board. The panel is 12 bit, so a channel has 16 levels in steps of
# 17, and one level up from black reads as barely there against it
CARD = color.rgb(34, 34, 38)        # The face of a card
SHADOW = color.rgb(17, 17, 19)      # The top edge of a card, recessed behind the one in front
HOUSING = color.rgb(17, 17, 19)     # The case the cards are set into, a level between them and board
KEYLINE = color.rgb(51, 51, 56)     # The case edge, which finds it against the board
HIGHLIGHT = color.rgb(85, 85, 92)   # A lit edge along the top of the case, light coming from above
INK = color.rgb(238, 238, 232)      # And the lettering on it
SPLIT = color.rgb(8, 8, 9)          # The line the cards are hinged on, and the gaps between them
BOARD = color.black                 # What the cards are set into
GAP = 4                             # Between one card and the next
SPLIT_H = 2                         # How thick the hinge line reads
EDGE = 3                            # Under this a falling card shows its thickness, not its face
CORNER = 6                          # How far the outer corners of a card are rounded off
SHADOW_H = 3                        # How deep the shadow on a card top reads
BEZEL = 8                           # How far the case stands out around the cards
MARGIN = 6                          # Around the whole row
SEPARATOR = 14                      # The colons, which are painted on, not flapped
ANTIALIAS = image.X2                # Lettering this size is worth smoothing
CELL_H = 96                         # How tall a card is

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# The row is wider than it is tall, so the canvas is drawn landscape and every update turns it a
# quarter turn onto the panel. From the screen, not image(), which puts it in SRAM: every
# pixel of a falling card is written by a blit and read again by the update, so both halve
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height

# Six cards and two colons, which is what a clock is
FLAPS = 6
CELL_W = (WIDTH - MARGIN * 2 - SEPARATOR * 2 - GAP * (FLAPS + 1)) // FLAPS
TOP = (HEIGHT - CELL_H) // 2
HALF = CELL_H // 2

flap_font = font.load(FLAP_FONT)


def ink_extent(size):
    """Which rows a round digit's ink occupies when drawn at this size, from its own y of zero.

    font_size is the em height, and a digit reaches neither the ascender above it nor the descender
    below, so how much of the card the lettering fills is only knowable from a drawn glyph. The probe
    is generous in both directions because text() clips to the rect it is given.
    """
    tall = round(size) * 2
    probe = image(CELL_W * 2, tall)
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = flap_font
    probe.antialias = ANTIALIAS
    probe.text("8", rect(0, 0, CELL_W * 2, tall), font_size=size)

    raw, stride = probe.raw, probe.stride
    inked = [y for y in range(tall)
             if any(raw[y * stride + x * 4] > 60 for x in range(CELL_W * 2))]
    return (inked[0], inked[-1]) if inked else None


def card_size():
    """The largest lettering a card can carry, measured on the ink rather than the em box.

    font_size is the em height, and how much of it a digit's ink actually fills varies enormously
    between faces: measured across three, anywhere from 29% to 67%. So capping font_size at the card
    leaves most of the card empty on some faces. Both the ink height and the width scale with the
    size, so one probe prices every size after it and the fit is two divisions.
    """
    canvas.font = flap_font
    probe = 48
    per_pixel = max(canvas.measure_text(letter, font_size=probe)[0] for letter in DRUM) / probe
    extent = ink_extent(probe)
    if extent is None:
        return probe
    ink_per_pixel = (extent[1] - extent[0] + 1) / probe
    return min((CELL_H - SPLIT_H * 2) / ink_per_pixel, (CELL_W - GAP * 2) / per_pixel)


def ink_top(size):
    """Where to draw the lettering so its ink centres on a card, not its em box."""
    extent = ink_extent(size)
    if extent is None:
        return round((CELL_H - size) / 2)
    return (CELL_H - (extent[1] - extent[0] + 1)) // 2 - extent[0]


SIZE = card_size()
INK_TOP = ink_top(SIZE)
EM_BOX = round(SIZE) + 2          # What a text rect has to cover, text() clipping to it

# Every character of the drum drawn once, a card to each, so a flap is a blit, not lettering
# drawn again. Two rows of it: the top half of a card and the bottom half, which fall separately
drum = image(CELL_W * len(DRUM), CELL_H)
drum.pen = SPLIT
drum.clear()
drum.font = flap_font
drum.antialias = ANTIALIAS

for index, letter in enumerate(DRUM):
    left = index * CELL_W
    # Rounded away from the hinge and square against it, the radii running clockwise from top left
    drum.pen = CARD
    drum.shape(shape.rounded_rectangle(rect(left, 0, CELL_W, HALF - SPLIT_H // 2),
                                       CORNER, CORNER, 0, 0))
    drum.shape(shape.rounded_rectangle(rect(left, HALF + SPLIT_H - SPLIT_H // 2,
                                            CELL_W, HALF - SPLIT_H), 0, 0, CORNER, CORNER))

    # Each card is recessed behind the one in front, so its top edge is shadowed. Drawn into the drum and not
    # per frame, and under both halves: the lower one is shadowed by the hinge above it
    drum.pen = SHADOW
    drum.rectangle(rect(left, 0, CELL_W, SHADOW_H))
    drum.rectangle(rect(left, HALF + SPLIT_H - SPLIT_H // 2, CELL_W, SHADOW_H))

    wide = drum.measure_text(letter, font_size=SIZE)[0]
    drum.pen = INK
    # text() clips to the rect, so it covers the whole em box rather than the card. The box starts
    # above the card to bring the ink down onto it, and a rect sized to the card would cut the ink off
    drum.text(letter, rect(left + round((CELL_W - wide) / 2), INK_TOP, CELL_W, EM_BOX),
              font_size=SIZE)

cards = drum.spritesheet(len(DRUM), 1)

# Where each card sits, and where the colons go between them
places = []
at = MARGIN + GAP
for position in range(FLAPS):
    places.append(at)
    at += CELL_W + GAP
    if position % 2 == 1 and position < FLAPS - 1:
        at += SEPARATOR

print(f"{FLAPS} cards of {CELL_W}x{CELL_H}, lettering {SIZE:.0f}px em from {INK_TOP}, drum of {len(DRUM)}")

source = rect(0, 0, CELL_W, HALF)
target = rect(0, 0, CELL_W, HALF)


def half_of(index, lower):
    """The upper or lower half of one drum card, as a source rect."""
    source.x = index * CELL_W
    source.y = HALF if lower else 0
    source.h = HALF
    return source


def settled(flap, index):
    """A card at rest, both halves showing the same character."""
    target.x, target.w = places[flap], CELL_W
    for lower in (False, True):
        target.y, target.h = TOP + (HALF if lower else 0), HALF
        canvas.blit(drum, half_of(index, lower), target)


def falling(flap, from_index, to_index, part):
    """A card part way down, and whatever it has stopped covering.

    The front of the card carries the old character's upper half and falls to nothing against the
    hinge; past halfway its back carries the new character's lower half and rises from the hinge.
    What the front uncovers as it falls is the new character's upper half, waiting behind it.
    """
    target.x, target.w = places[flap], CELL_W

    # The new character's upper half stands behind for the whole fall, whole and the right way up:
    # it is waiting there and not arriving, so it is never squashed. Drawn every frame, and not
    # only while the card is above the hinge, or the last sliver of card outlives the card
    target.y, target.h = TOP, HALF
    canvas.blit(drum, half_of(to_index, False), target)

    if part < 0.5:
        showing, above, index = round(HALF * (1 - part * 2)), True, from_index
    else:
        showing, above, index = round(HALF * (part - 0.5) * 2), False, to_index

    if showing <= 0:
        return

    target.y = TOP + HALF - showing if above else TOP + HALF
    target.h = showing

    # Near enough edge on, a card shows its thickness rather than its face. A whole half sampled
    # down to a row or two is a smear, and a smear is what the eye catches at the handover
    if showing <= EDGE:
        canvas.pen = SPLIT
        canvas.rectangle(target)
    else:
        canvas.blit(drum, half_of(index, not above), target)


def clock_now(started):
    """The time the board is showing, counted on from CLOCK_START."""
    elapsed = time.ticks_diff(time.ticks_ms(), started) // 1000
    hours, minutes, seconds = CLOCK_START
    total = (hours * 3600 + minutes * 60 + seconds + elapsed) % 86400
    return f"{total // 3600:02d}{total // 60 % 60:02d}{total % 60:02d}"


# The board comes up blank and climbs to the time, a card at a time, which is what a real one does
# from cold and what shows the drum being wound round and not set
canvas.pen = BOARD
canvas.clear()

# The case the cards are set into, drawn once. It stands for the whole run: a falling card is blitted
# only inside its own column, so nothing ever writes over the bezel around them
case = rect(places[0] - BEZEL, TOP - BEZEL,
            places[-1] + CELL_W + BEZEL - (places[0] - BEZEL), CELL_H + BEZEL * 2)

# A keyline around it, then the face inset over the top. The face has to stay dark, being a recess the
# cards sit in, and one level above the board is not enough to find in the dark: what makes the case
# read is its edge catching light, not its face
canvas.pen = KEYLINE
canvas.shape(shape.rounded_rectangle(case, CORNER, CORNER, CORNER, CORNER))
canvas.pen = HOUSING
canvas.shape(shape.rounded_rectangle(rect(case.x + 1, case.y + 1, case.w - 2, case.h - 2),
                                     CORNER, CORNER, CORNER, CORNER))

# Brightest along the top and black along the bottom, so the light reads as coming from above
canvas.pen = HIGHLIGHT
canvas.rectangle(rect(case.x + CORNER, case.y, case.w - CORNER * 2, 1))
canvas.pen = BOARD
canvas.rectangle(rect(case.x + CORNER, case.y + case.h - 1, case.w - CORNER * 2, 1))

showing = [0] * FLAPS               # Where each card is in the drum, blank to begin with
wanted = [0] * FLAPS
turning = [None] * FLAPS            # When the card at this place started falling

for flap in range(FLAPS):
    settled(flap, 0)

# The colons, painted on the board between the pairs, not carried on a card
canvas.pen = INK
for position in (1, 3):
    middle = places[position] + CELL_W + GAP + SEPARATOR // 2
    for y in (TOP + HALF // 2, TOP + HALF + HALF // 2):
        canvas.rectangle(rect(middle - 2, y - 2, 4, 4))

screen.update(canvas, rotation=90)
started = time.ticks_ms()

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        now = time.ticks_ms()
        reading = clock_now(started)

        # A card only ever climbs, so it keeps flapping until it reaches what it should show
        for flap in range(FLAPS):
            wanted[flap] = DRUM.index(reading[flap])

        drew = False
        for flap in range(FLAPS):
            if turning[flap] is None:
                if showing[flap] != wanted[flap]:
                    turning[flap] = now
                continue

            part = min(1.0, time.ticks_diff(now, turning[flap]) / FLAP_MS)
            step = (showing[flap] + 1) % len(DRUM)
            falling(flap, showing[flap], step, part)
            drew = True

            if part >= 1.0:
                showing[flap] = step
                settled(flap, step)
                turning[flap] = now if showing[flap] != wanted[flap] else None

        if drew:
            screen.update(canvas, rotation=90)
        else:
            time.sleep_ms(10)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
