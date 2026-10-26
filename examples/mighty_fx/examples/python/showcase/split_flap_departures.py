from mighty_fx import MightyFX, SPCE
from timing import Pacer, Roller
from screens import Screen280
from picovector import color, font, image, rect, shape

"""
Draw a split-flap departures board, each card climbing through the drum to its letter.

Press "Boot" to exit the program.
"""

# Constants for drawing
FLAP_FONT = "/rom/fonts/Oswald.af"   # A condensed vector face, which is what a board wants

# What is on a card, in the order it comes round. A column takes only the drum it needs, so a time's
# cards go eleven round, not thirty-seven. Blank leads each
DIGITS = " 0123456789"
ALPHA = " ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BOTH = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
FLAP_MS = 150                           # How long one card takes to fall
HOLD = 2.0                              # How long a page stands before the next one is called up
# A card sits two levels above the board. The screens drive the panel at 12 bit, so a channel has 16
# levels in steps of 17, and one level up from black reads as barely there against it
CARD = color.rgb(34, 34, 38)            # The face of a card
TEXT_COLOUR = color.rgb(238, 238, 232)  # And the lettering on it, and the colons painted beside them
HEADING = color.rgb(232, 176, 24)       # The column headings, painted on the board, not flapped
SPLIT = color.rgb(8, 8, 9)              # The line the cards are hinged on, and the gaps between them
BOARD = color.black                     # What the cards are set into
GAP = 1                                 # Between one card and the next inside a column
COLUMN_GAP = 12                         # The least between columns, which carry no cards at all
COLON_W = 9                             # The colon in a time, painted on the board, not flapped

# A card is sized to its letter, so rows do not run into each other
CARD_PAD = 2                            # Card left above and below its lettering
ROW_GAP = 6                             # Between one row of cards and the next
SPLIT_H = 1                             # How thick the hinge reads, matching the gap between cards
EDGE = 2                                # Under this a falling card shows its thickness, not its face
CORNER = 2                              # How far the outer corners of a card are rounded off
MARGIN = 4                              # Around the whole board
HEADING_GAP = 4                         # Under the headings, before the first row
HEADING_MAX = 1                         # A cap on the headings, as a multiple of the card lettering
LETTER_MAX = 24                         # How tall the lettering aims to be, the card sized to suit
ANTIALIAS = image.X2                    # Lettering off a vector face wants smoothing at this size

# The columns, each a heading, cards wide, where a painted colon falls, and its drum.
# A time is four cards, with its colon painted after the second
COLUMNS = (("TIME", 4, 2, DIGITS), ("DEST", 6, 0, ALPHA), ("GATE", 3, 0, BOTH))

# What the board shows, a page at a time and a row to a service.
# A name longer than its column is cut to it, as a real board's would be
PAGES = (
    (("11:32", "LONDON", "A42"), ("11:55", "TOKYO", "B32"), ("12:08", "PARIS", "C75"),
     ("12:24", "MADRID", "A06"), ("12:42", "MOSCOW", "D35"), ("13:05", "MILAN", "B71")),
    (("13:18", "DUBLIN", "C12"), ("13:40", "VIENNA", "A18"), ("14:02", "BERLIN", "B44"),
     ("14:15", "OSLO", "D19"), ("14:31", "LISBON", "C63"), ("14:50", "PRAGUE", "A27")),
    (("15:06", "ATHENS", "B08"), ("15:22", "MALAGA", "D51"), ("15:44", "ZURICH", "A33"),
     ("16:01", "KRAKOW", "C26"), ("16:20", "SOFIA", "B47"), ("16:38", "RIGA", "D15")),
)

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Drawn landscape and turned a quarter onto the panel at each update
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height

ROWS = len(PAGES[0])
CARDS = sum(wide for _, wide, _, _drum in COLUMNS)

# Everything across the board that is not a card, so what is left over divides between them
spare = MARGIN * 2 + COLUMN_GAP * (len(COLUMNS) - 1)
for _, wide, colon, _drum in COLUMNS:
    spare += GAP * (wide - 1) + (COLON_W - GAP if colon else 0)

CELL_W = (WIDTH - spare) // CARDS

# Spare pixels go between the columns, COLUMN_GAP being the least
COLUMN_SPACE = COLUMN_GAP + (WIDTH - spare - CELL_W * CARDS) // (len(COLUMNS) - 1)

flap_font = font.load(FLAP_FONT)
canvas.font = flap_font
canvas.antialias = ANTIALIAS

# One probe prices every size, as drawn height and width both scale with font_size
REFERENCE = 64
WIDTH_PER_PX = max(canvas.measure_text(letter, font_size=REFERENCE)[0]
                   for letter in BOTH) / REFERENCE


def lettering_rows(size, letters):
    """
    Measure which rows these letters fill at this size, font_size being the em height.

    The probe is generous as text() clips to its rect.
    """
    tall = round(size) * 3
    probe = image(round(size) * 2, tall)
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = flap_font
    probe.antialias = ANTIALIAS
    drawn = []
    for letter in letters:
        probe.text(letter, rect(0, 0, probe.width, tall), font_size=size)
    raw, stride = probe.raw, probe.stride
    for y in range(tall):
        if any(raw[y * stride + x * 4] > 60 for x in range(probe.width)):
            drawn.append(y)
    return (drawn[0], drawn[-1]) if drawn else None


REACH = lettering_rows(REFERENCE, "HW8O")
LETTERING_PER_PX = (REACH[1] - REACH[0] + 1) / REFERENCE

# The largest lettering a card can carry, usually set by the width of the drum's W
SIZE = min(LETTER_MAX / LETTERING_PER_PX, CELL_W / WIDTH_PER_PX)
LETTER_H = round(LETTERING_PER_PX * SIZE)
# Rounded up to even, so no row falls between the two halves
CELL_H = LETTER_H + CARD_PAD * 2
CELL_H += CELL_H % 2
HALF = CELL_H // 2

# Where the lettering sits inside the em box, so a letter centres on its card, not its box centring
LETTERING_TOP = (CELL_H - LETTER_H) // 2 - round(lettering_rows(SIZE, "HW8O")[0])
EM_BOX = round(SIZE) + 2

# Where every card sits across the board, and where the painted colons go between them. Cards are
# laid only where a column has one, so the space between columns is board, not blank cards
spots = []
colons = []
at = MARGIN
for _, wide, colon, _drum in COLUMNS:
    for index in range(wide):
        spots.append(at)
        at += CELL_W
        if index == colon - 1:
            colons.append(at)
            at += COLON_W
        elif index < wide - 1:
            at += GAP

    at += COLUMN_SPACE

# The headings sit over their own columns, at one size so the row reads as a row. A column's last
# gap is board too, so a heading may use it and is not held to the cards alone
HEADING_SIZE = SIZE * HEADING_MAX
starts = []
card = 0
for name, wide, _, _drum in COLUMNS:
    starts.append(card)
    room = spots[card + wide - 1] + CELL_W - spots[card] + COLUMN_SPACE
    HEADING_SIZE = min(HEADING_SIZE,
                       room / (canvas.measure_text(name, font_size=REFERENCE)[0] / REFERENCE))
    card += wide

HEADING_LETTER_H = round(LETTERING_PER_PX * HEADING_SIZE)
HEADING_TOP = -round(lettering_rows(HEADING_SIZE, "HW8O")[0])

# Whatever the rows do not need goes under the headings and not the foot of the
# board, where it reads as a row that failed to draw. HEADING_GAP is the least it may be
over = HEIGHT - (MARGIN * 2 + HEADING_LETTER_H + ROWS * CELL_H + (ROWS - 1) * ROW_GAP)
HEADING_H = HEADING_LETTER_H + max(HEADING_GAP, over)
TOP = MARGIN + HEADING_H

if TOP + ROWS * CELL_H + (ROWS - 1) * ROW_GAP + MARGIN > HEIGHT:
    raise ValueError(f"{ROWS} rows of {CELL_H}px do not fit: drop a row, or a few pixels off LETTER_MAX")


def place(row, card):
    """Where a card sits on the board."""
    return spots[card], TOP + row * (CELL_H + ROW_GAP)


def sheet_for(letters):
    """Draw every character of one drum once to a card of its own, so a flap is a blit."""
    made = image(CELL_W * len(letters), CELL_H)
    made.pen = SPLIT
    made.clear()
    made.font = flap_font
    made.antialias = ANTIALIAS

    for index, letter in enumerate(letters):
        left = index * CELL_W
        made.pen = CARD
        made.shape(shape.rounded_rectangle(rect(left, 0, CELL_W, HALF - SPLIT_H // 2),
                                           CORNER, CORNER, 0, 0))
        made.shape(shape.rounded_rectangle(rect(left, HALF + SPLIT_H - SPLIT_H // 2,
                                                CELL_W, HALF - SPLIT_H), 0, 0, CORNER, CORNER))

        wide = made.measure_text(letter, font_size=SIZE)[0]
        made.pen = TEXT_COLOUR
        # text() clips to its rect, so the rect starts above the card and covers the em box
        made.text(letter, rect(left + round((CELL_W - wide) / 2), LETTERING_TOP, CELL_W, EM_BOX),
                  font_size=SIZE)

    return made


# One sheet a drum, and what each card is fitted with. Two columns sharing a drum share its sheet
sheets = {}
card_drum = []
for _, wide, _, letters in COLUMNS:
    if letters not in sheets:
        sheets[letters] = sheet_for(letters)

    card_drum += [letters] * wide

source = rect(0, 0, CELL_W, HALF)
target = rect(0, 0, CELL_W, HALF)


def half_of(index, lower):
    """The upper or lower half of one drum card, as a source rect."""
    source.x = index * CELL_W
    source.y = HALF if lower else 0
    return source


def settled(row, card, index):
    """A card at rest, both halves showing the same character."""
    left, top = place(row, card)
    drum = sheets[card_drum[card]]
    target.x, target.w = left, CELL_W
    for lower in (False, True):
        target.y, target.h = top + (HALF if lower else 0), HALF
        canvas.blit(drum, half_of(index, lower), target)


def falling(row, card, from_index, to_index, part):
    """
    Draw a card part way down.

    Its front falls with the old upper half and its back rises with the new lower half,
    while the new upper half waits behind it.
    """
    left, top = place(row, card)
    drum = sheets[card_drum[card]]
    target.x, target.w = left, CELL_W

    # The new upper half stands behind for the whole fall,
    # drawn every frame so no sliver outlives the card
    target.y, target.h = top, HALF
    canvas.blit(drum, half_of(to_index, False), target)

    if part < 0.5:
        showing, above, index = round(HALF * (1 - part * 2)), True, from_index
    else:
        showing, above, index = round(HALF * (part - 0.5) * 2), False, to_index

    if showing <= 0:
        return

    target.y = top + HALF - showing if above else top + HALF
    target.h = showing

    # Near edge on, a card shows its thickness
    if showing <= EDGE:
        canvas.pen = SPLIT
        canvas.rectangle(target)
    else:
        canvas.blit(drum, half_of(index, not above), target)


print(f"{ROWS} rows of {CARDS} cards, {CELL_W}x{CELL_H}, lettering {LETTER_H}px, "
      f"headings {HEADING_LETTER_H}px, drums of {[len(letters) for letters in sheets]}")

# The board comes up blank and every card climbs to its letter, so the first page lands raggedly
canvas.pen = BOARD
canvas.clear()

showing_at = [[0] * CARDS for _ in range(ROWS)]     # Where each card is in its drum, blank to begin with
wanted_at = [[0] * CARDS for _ in range(ROWS)]      # Where each is climbing to
turning_at = [[None] * CARDS for _ in range(ROWS)]  # When each started falling, on the pacer's clock

for row in range(ROWS):
    for card in range(CARDS):
        settled(row, card, 0)

canvas.pen = HEADING
for (name, _wide, _, _drum), start in zip(COLUMNS, starts):
    canvas.text(name, rect(spots[start], MARGIN + HEADING_TOP, WIDTH, round(HEADING_SIZE) + 2),
                font_size=HEADING_SIZE)

# The colons, painted on the board between the pairs they separate, not carried on a card,
# and in the cards' text colour since they read as part of the time
canvas.pen = TEXT_COLOUR
dot = max(2, CELL_W // 8)
for left in colons:
    middle = left + (COLON_W - dot) // 2
    for row in range(ROWS):
        top = TOP + row * (CELL_H + ROW_GAP)
        canvas.rectangle(rect(middle, top + HALF // 2, dot, dot))
        canvas.rectangle(rect(middle, top + HALF + HALF // 2 - dot, dot, dot))

screen.update(canvas, rotation=90)


def call_up(index):
    """
    Set every card after the page it should be showing, a column's text starting at its own.

    A colon is painted on the board, so it is dropped from a time before the digits are laid out.
    """
    for row in range(ROWS):
        for card in range(CARDS):
            wanted_at[row][card] = 0

        for (_, wide, _, drum_of), start, text in zip(COLUMNS, starts, PAGES[index][row]):
            letters = text.replace(":", "")
            for offset in range(min(wide, len(letters))):
                # A character its column is not fitted with cannot be shown, so it stays blank,
                # which is what a real board does with a name it has no cards for
                wanted_at[row][start + offset] = max(0, drum_of.find(letters[offset]))


call_up(0)
page = 0
standing = False                    # Whether every card has come to rest on the page
pacer = Pacer(0.01)                 # Its elapsed time counts from the call-up of the page in progress
next_page = Roller(HOLD)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        now = pacer.elapsed
        drew = False
        resting = True

        for row in range(ROWS):
            for card in range(CARDS):
                started = turning_at[row][card]
                if started is None:
                    if showing_at[row][card] != wanted_at[row][card]:
                        turning_at[row][card] = now
                        resting = False
                    continue

                resting = False
                part = min(1.0, (now - started) / FLAP_MS)
                step = (showing_at[row][card] + 1) % len(card_drum[card])
                falling(row, card, showing_at[row][card], step, part)
                drew = True

                # Landed, so it falls again at once where the card still has further to climb
                if part >= 1.0:
                    showing_at[row][card] = step
                    settled(row, card, step)
                    turning_at[row][card] = (now if step != wanted_at[row][card] else None)

        if drew:
            screen.update(canvas, rotation=90)
        elif resting and not standing:
            # The page has settled, so it stands from now
            standing = True
            next_page.restart()
        elif resting and next_page.is_due():
            page = (page + 1) % len(PAGES)
            call_up(page)
            standing = False
            pacer.restart()

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
