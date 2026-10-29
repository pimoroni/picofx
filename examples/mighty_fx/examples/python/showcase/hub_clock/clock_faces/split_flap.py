from picovector import color, font, image, rect, shape

"""
A split-flap card for the hub clock, the old upper half falling to show the new digit. A colon is
painted on the board beside the card. showcase/split_flap_clock.py is the fuller version.

Each place has a unit carrying the cards it needs in the order they come round, so every change is one
card. The two hour units turn together, a card an hour, as one unit of 24 would.
"""

FLAP_FONT = "/rom/fonts/AdventPro-Medium.af"   # A vector face, so it sizes to the card
LETTERING = " 0123456789"           # Every character a card can carry, a blank where the hour's leading zero is left off
CHANGE_STEPS = 3                    # Frames through a card's fall
COLON_BLINKS = False                # The colon is painted on, so it never goes out
WRITE_BUDGET = None                 # Every card of a climb falls, however long a wrap's cascade takes

# What each unit carries, by what it shows
SEQUENCES = {
    "units": "0123456789",
    "tens": "012345",
    "hour tens": "0" * 10 + "1" * 10 + "2" * 4,
    "blank hour tens": " " * 10 + "1" * 10 + "2" * 4,
    "hour units": "0123456789" * 2 + "0123",
}


def shows(reading, place):
    """Find the unit a place of HHMMSS takes and its card, the hour units both going by the hour."""
    if place < 2:
        if place == 1:
            return ("hour units", int(reading[:2]))
        return ("blank hour tens" if reading[0] == " " else "hour tens", int(reading[:2]))
    return ("tens" if place % 2 == 0 else "units", int(reading[place]))


def change_steps(previous, showing):
    """
    Count the frames through a climb, a card's fall in full where it is one card and two a card where it
    is two. A longer climb, as from the lamp test, shows each card once, mid-fall, as every panel's frames
    share the hub's wire.
    """
    cards = (showing[1] - previous[1]) % len(SEQUENCES[showing[0]])
    if cards == 1:
        return CHANGE_STEPS
    return cards * 2 if cards == 2 else cards

# A card sits two levels above the board. The screens drive the panel at 12 bit, so a channel has 16
# levels in steps of 17, and one level up from black reads as barely there against it
CARD = color.rgb(34, 34, 38)        # The face of a card
SHADOW = color.rgb(17, 17, 19)      # The top edge of a card, recessed behind the one in front
HOUSING = color.rgb(17, 17, 19)     # The case the card is set into, a level between it and the board
KEYLINE = color.rgb(51, 51, 56)     # The case edge, which finds it against the board
HIGHLIGHT = color.rgb(85, 85, 92)   # A lit edge along the top of the case, light coming from above
TEXT_COLOUR = color.rgb(238, 238, 232)  # The lettering, and the colon painted on the board
SPLIT = color.rgb(8, 8, 9)          # The line the card is hinged on
BOARD = color.black                 # What the case is set into
SPLIT_H = 3                         # How thick the hinge line reads
EDGE = 4                            # Under this a falling card shows its thickness, not its face
CORNER = 8                          # How far the outer corners of a card are rounded off
SHADOW_H = 4                        # How deep the shadow on a card top reads
BEZEL = 8                           # How far the case stands out around the card
SIDE = 26                           # Panel pixels from the case to the panel's side, where a colon goes
TALL = 1.4                          # A card's height, against its width
ANTIALIAS = image.X2                # Lettering this size is worth smoothing

# Made by prepare() for the panel's size, and kept
drum = None                         # Every card drawn once side by side, so a flap is a blit
background = None                   # The board and the case, which a frame starts from the first time
cased = set()                       # The frames already holding the board and the case, by id
colon = []
cell_w = cell_h = half = left = top = 0
source = rect(0, 0, 0, 0)
target = rect(0, 0, 0, 0)


def lettering_rows(face, size):
    """Measure the first and last rows a digit fills at this size, font_size being the em height."""
    tall = round(size) * 2
    probe = image(cell_w * 2, tall)
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = face
    probe.antialias = ANTIALIAS
    probe.text("8", rect(0, 0, cell_w * 2, tall), font_size=size)
    raw, stride = probe.raw, probe.stride
    drawn = [y for y in range(tall) if any(raw[y * stride + x * 4] > 60 for x in range(cell_w * 2))]
    return drawn[0], drawn[-1]


def prepare(width, height):
    """Build the drum and the case, sized to fill a panel this size."""
    global drum, background, cell_w, cell_h, half, left, top
    cell_w = width - (SIDE + BEZEL) * 2
    cell_h = min(round(cell_w * TALL), height - BEZEL * 4)
    half = cell_h // 2
    left, top = (width - cell_w) // 2, (height - cell_h) // 2
    source.w = target.w = cell_w

    # The largest lettering a card can carry, sized on what it draws. One probe prices every size, as
    # drawn height and width both scale with it
    face = font.load(FLAP_FONT)
    probe = image(8, 8)
    probe.font = face
    per_pixel = max(probe.measure_text(letter, font_size=48)[0] for letter in LETTERING) / 48
    first, last = lettering_rows(face, 48)
    size = min((cell_h - SPLIT_H * 4) / ((last - first + 1) / 48), (cell_w * 0.8) / per_pixel)
    first, last = lettering_rows(face, size)
    lettering_top = (cell_h - (last - first + 1)) // 2 - first

    drum = image(cell_w * len(LETTERING), cell_h)
    drum.pen = SPLIT
    drum.clear()
    drum.font = face
    drum.antialias = ANTIALIAS
    for index, letter in enumerate(LETTERING):
        x = index * cell_w
        # Rounded away from the hinge and square against it, the radii running clockwise from top left
        drum.pen = CARD
        drum.shape(shape.rounded_rectangle(rect(x, 0, cell_w, half - SPLIT_H // 2), CORNER, CORNER, 0, 0))
        drum.shape(shape.rounded_rectangle(rect(x, half + SPLIT_H - SPLIT_H // 2, cell_w, half - SPLIT_H),
                                           0, 0, CORNER, CORNER))
        # Each half's top edge is shadowed, the lower half's by the hinge
        drum.pen = SHADOW
        drum.rectangle(rect(x, 0, cell_w, SHADOW_H))
        drum.rectangle(rect(x, half + SPLIT_H - SPLIT_H // 2, cell_w, SHADOW_H))
        wide = drum.measure_text(letter, font_size=size)[0]
        drum.pen = TEXT_COLOUR
        # text() clips to its rect, so the rect starts above the card and covers the em box
        drum.text(letter, rect(x + round((cell_w - wide) / 2), lettering_top, cell_w, round(size) + 2), font_size=size)

    # The case, a keyline with the dark face inset over it, lit along the top and dark along the bottom
    drawn = image(width, height)
    drawn.pen = BOARD
    drawn.clear()
    case = rect(left - BEZEL, top - BEZEL, cell_w + BEZEL * 2, cell_h + BEZEL * 2)
    drawn.pen = KEYLINE
    drawn.shape(shape.rounded_rectangle(case, CORNER, CORNER, CORNER, CORNER))
    drawn.pen = HOUSING
    drawn.shape(shape.rounded_rectangle(rect(case.x + 1, case.y + 1, case.w - 2, case.h - 2),
                                        CORNER, CORNER, CORNER, CORNER))
    drawn.pen = HIGHLIGHT
    drawn.rectangle(rect(case.x + CORNER, case.y, case.w - CORNER * 2, 1))
    drawn.pen = BOARD
    drawn.rectangle(rect(case.x + CORNER, case.y + case.h - 1, case.w - CORNER * 2, 1))

    # Laid over black once, as its blended pixels fall a little short of opaque, so a frame can take its
    # bytes whole
    background = image(width, height)
    background.pen = BOARD
    background.clear()
    background.blit(drawn, 0, 0)

    # The colon, two painted squares midway between the case and the panel's right edge
    middle = (case.x + case.w + width) // 2
    for y in (top + half // 2, top + half + half // 2):
        colon.append(rect(middle - 3, y - 3, 6, 6))


def half_of(index, lower):
    """Find the upper or lower half of one drum card, as a source rect."""
    source.x = index * cell_w
    source.y = half if lower else 0
    source.h = half
    return source


def settled(frame, index):
    """Draw a card at rest, both halves showing the same character."""
    target.x = left
    for lower in (False, True):
        target.y, target.h = top + (half if lower else 0), half
        frame.blit(drum, half_of(index, lower), target)


def falling(frame, from_index, to_index, part):
    """
    Draw a card part way down, its front falling with the old upper half and its back rising with the new
    lower half, while the new upper half waits behind it.
    """
    target.x = left
    target.y, target.h = top, half
    frame.blit(drum, half_of(to_index, False), target)

    if part < 0.5:
        showing, above, index = round(half * (1 - part * 2)), True, from_index
    else:
        showing, above, index = round(half * (part - 0.5) * 2), False, to_index
    if showing <= 0:
        return

    target.y = top + half - showing if above else top + half
    target.h = showing
    # A card near edge on shows its thickness, as a half squashed to a row or two smears
    if showing <= EDGE:
        frame.pen = SPLIT
        frame.rectangle(target)
    else:
        frame.blit(drum, half_of(index, not above), target)


def draw(frame, showing, colon_lit, previous=None, progress=1.0):
    """
    Draw a whole panel into the frame, the case with the card in it.

    showing is a unit and its card, from shows(). colon_lit is None on a panel without a colon. On the
    way from a previous card the unit is part way through its climb, by progress from 0 to 1, a card at
    a time with the one between falling.

    Only the card changes from frame to frame, its two halves covering it whole, so a frame takes the
    board and case once and after that only the card and the colon are drawn into it.
    """
    if id(frame) not in cased:
        frame.raw[:] = background.raw
        cased.add(id(frame))
    cards = SEQUENCES[showing[0]]
    if previous is None or progress >= 1:
        settled(frame, LETTERING.index(cards[showing[1]]))
    else:
        start = previous[1]
        along = progress * ((showing[1] - start) % len(cards))
        passed = int(along)
        # The card in front comes from the unit it is leaving, until it has fallen, which differs only where
        # the hour's leading zero changes between blank and drawn
        before = cards[(start + passed) % len(cards)] if passed else SEQUENCES[previous[0]][start]
        after = cards[(start + passed + 1) % len(cards)]
        settled(frame, LETTERING.index(before))
        falling(frame, LETTERING.index(before), LETTERING.index(after), along - passed)

    # Painted out where the panel has no colon, as the frame may last have held one that did
    frame.pen = BOARD if colon_lit is None else TEXT_COLOUR
    for dot in colon:
        frame.rectangle(dot)
