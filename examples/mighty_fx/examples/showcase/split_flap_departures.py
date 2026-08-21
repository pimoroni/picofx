import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import color, font, image, rect, shape

"""
Draw a split-flap departures board, every card climbing through the drum until it reaches
its letter.

Press "Boot" to exit the program.
"""

# Constants for drawing
FLAP_FONT = "/rom/fonts/Oswald.af"   # A condensed vector face, which is what a board wants
# What is on a card, in the order it comes round. A column is fitted with the drum it needs rather
# than one carrying everything, as a real board is. A time never shows a letter, so its cards are
# eleven round instead of thirty-seven and settle in a third of the travel. Blank leads each one,
# so a board turns up from blank the same way whatever its cards carry
DIGITS = " 0123456789"
ALPHA = " ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BOTH = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
FLAP_MS = 150                       # How long one card takes to fall
HOLD = 7.0                          # How long a page stands before the next one is called up
# A card sits two levels above the board. The panel is 12 bit, so a channel has 16 levels in steps of
# 17, and one level up from black reads as barely there against it
CARD = color.rgb(34, 34, 38)        # The face of a card
INK = color.rgb(238, 238, 232)      # And the lettering on it, and the colons painted beside them
HEADING = color.rgb(232, 176, 24)   # The column headings, painted on the board, not flapped
SPLIT = color.rgb(8, 8, 9)          # The line the cards are hinged on, and the gaps between them
BOARD = color.black                 # What the cards are set into
GAP = 1                             # Between one card and the next inside a column
COLUMN_GAP = 12                     # The least between columns, which carry no cards at all
COLON_W = 9                         # The colon in a time, painted on the board, not flapped

# A card is sized to its letter, not to the space going spare. Sized to the space, a row
# cannot be told from the one below it, the cards meeting with nothing between them
CARD_PAD = 2                        # Card left above and below its lettering
ROW_GAP = 6                         # Between one row of cards and the next
SPLIT_H = 1                         # How thick the hinge reads, matching the gap between cards
EDGE = 2                            # Under this a falling card shows its thickness, not its face
CORNER = 2                          # How far the outer corners of a card are rounded off
MARGIN = 4                          # Around the whole board
HEADING_GAP = 4                     # Under the headings, before the first row
HEADING_MAX = 1                     # A cap on the headings, as a multiple of the card lettering
LETTER_MAX = 24                     # How tall the lettering aims to be, the card sized to suit
ANTIALIAS = image.X2                # Lettering off a vector face wants smoothing at this size

# The columns, each a heading, how many cards wide it is, how many cards into it a colon is painted,
# and what its cards are fitted with. A colon is not carried on a card, so a time is four cards, not
# five
COLUMNS = (("TIME", 4, 2, DIGITS), ("DEST", 6, 0, ALPHA), ("GATE", 3, 0, BOTH))

# What the board shows, a page at a time and a row to a service. A name longer than its column is
# cut to it, as a real board's would be
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

# The board is wider than it is tall, so the canvas is drawn landscape and every update turns it a
# quarter turn onto the panel. From the screen, not image(), which puts it in SRAM: a falling
# card is written by a blit and read again by the update, so both halve
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height

ROWS = len(PAGES[0])
CARDS = sum(wide for _, wide, _, _drum in COLUMNS)

# Everything across the board that is not a card, so what is left over divides between them
spare = MARGIN * 2 + COLUMN_GAP * (len(COLUMNS) - 1)
for _, wide, colon, _drum in COLUMNS:
    spare += GAP * (wide - 1) + (COLON_W - GAP if colon else 0)

CELL_W = (WIDTH - spare) // CARDS

# Dividing the width between the cards leaves a few pixels over. They go between the columns rather
# than as padding down one side, so the board fills its width. COLUMN_GAP is the least they may be
COLUMN_SPACE = COLUMN_GAP + (WIDTH - spare - CELL_W * CARDS) // (len(COLUMNS) - 1)

flap_font = font.load(FLAP_FONT)
canvas.font = flap_font
canvas.antialias = ANTIALIAS

# A vector face takes font_size as the em height, and neither how much of that a letter's ink fills
# nor how wide the widest of them runs is knowable without asking. Both scale with the size, so one
# probe of each prices every size after it
REFERENCE = 64
WIDTH_PER_PX = max(canvas.measure_text(letter, font_size=REFERENCE)[0]
                   for letter in BOTH) / REFERENCE


def ink_rows(size, letters):
    """Which rows these letters' ink occupies, drawn at their own y of zero.

    Read from a drawing rather than from metrics: the em box carries ascender and descender space no
    capital reaches, so it says nothing about how tall the lettering comes out. The probe is generous
    in both directions because text() clips to the rect it is given.
    """
    tall = round(size) * 3
    probe = image(round(size) * 2, tall)
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = flap_font
    probe.antialias = ANTIALIAS
    inked = []
    for letter in letters:
        probe.text(letter, rect(0, 0, probe.width, tall), font_size=size)
    raw, stride = probe.raw, probe.stride
    for y in range(tall):
        if any(raw[y * stride + x * 4] > 60 for x in range(probe.width)):
            inked.append(y)
    return (inked[0], inked[-1]) if inked else None


REACH = ink_rows(REFERENCE, "HW8O")
INK_PER_PX = (REACH[1] - REACH[0] + 1) / REFERENCE

# The largest lettering a card can carry. LETTER_MAX is what the cards were sized to before, and the
# width is what usually decides it: the drum carries a W, which is wider against its own height than
# a purpose-drawn pixel face would be
SIZE = min(LETTER_MAX / INK_PER_PX, CELL_W / WIDTH_PER_PX)
LETTER_H = round(INK_PER_PX * SIZE)
# Rounded up to even: a card halves at its hinge, so an odd height leaves its last row in
# neither half and so never drawn
CELL_H = LETTER_H + CARD_PAD * 2
CELL_H += CELL_H % 2
HALF = CELL_H // 2

# Where the ink sits inside the em box, so a letter centres on its card, not its box centring
INK_TOP = (CELL_H - LETTER_H) // 2 - round(ink_rows(SIZE, "HW8O")[0])
EM_BOX = round(SIZE) + 2

# Where every card sits across the board, and where the painted colons go between them. Cards are
# laid only where a column has one, so the space between columns is board, not blank cards
spots = []
colons = []
at = MARGIN
for _, wide, colon, _drum in COLUMNS:
    room = at
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

HEADING_INK = round(INK_PER_PX * HEADING_SIZE)
HEADING_TOP = -round(ink_rows(HEADING_SIZE, "HW8O")[0])

# Whatever the rows do not need goes under the headings and not the foot of the
# board, where it reads as a row that failed to draw. HEADING_GAP is the least it may be
over = HEIGHT - (MARGIN * 2 + HEADING_INK + ROWS * CELL_H + (ROWS - 1) * ROW_GAP)
HEADING_H = HEADING_INK + max(HEADING_GAP, over)
TOP = MARGIN + HEADING_H

if TOP + ROWS * CELL_H + (ROWS - 1) * ROW_GAP + MARGIN > HEIGHT:
    raise ValueError(f"{ROWS} rows of {CELL_H}px do not fit: drop a row, or a few pixels off LETTER_MAX")


def place(row, card):
    """Where a card sits on the board."""
    return spots[card], TOP + row * (CELL_H + ROW_GAP)


def sheet_for(letters):
    """Every character of one drum drawn once, a card to each.

    A flap is then a blit, not lettering laid out again, and a drum's cards are all in one
    image, so a column's whole set is one sheet however many cards are fitted with it.
    """
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
        made.pen = INK
        # The rect covers the em box, not the card, text() clipping to it and the box starting
        # above the card to bring the ink down onto it
        made.text(letter, rect(left + round((CELL_W - wide) / 2), INK_TOP, CELL_W, EM_BOX),
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
    """A card part way down, and the half standing behind it.

    The front carries the old character's upper half and falls onto the hinge; past halfway the
    back carries the new character's lower half and rises from it. The standing half is drawn every
    frame, not only while the card is above the hinge, or the last sliver of it outlives the card.
    """
    left, top = place(row, card)
    drum = sheets[card_drum[card]]
    target.x, target.w = left, CELL_W

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

    # Near enough edge on, a card shows its thickness rather than its face
    if showing <= EDGE:
        canvas.pen = SPLIT
        canvas.rectangle(target)
    else:
        canvas.blit(drum, half_of(index, not above), target)


print(f"{ROWS} rows of {CARDS} cards, {CELL_W}x{CELL_H}, lettering {LETTER_H}px, "
      f"headings {HEADING_INK}px, drums of {[len(letters) for letters in sheets]}")

# The board comes up blank and climbs to its first page, as a real one does from cold. A card only ever
# goes forwards, so how long it takes is how far round its letter is: the page lands raggedly, and that
# is the mechanism rather than an effect
canvas.pen = BOARD
canvas.clear()

showing_at = [[0] * CARDS for _ in range(ROWS)]
wanted_at = [[0] * CARDS for _ in range(ROWS)]
turning_at = [[None] * CARDS for _ in range(ROWS)]

for row in range(ROWS):
    for card in range(CARDS):
        settled(row, card, 0)

canvas.pen = HEADING
for (name, _wide, _, _drum), start in zip(COLUMNS, starts):
    canvas.text(name, rect(spots[start], MARGIN + HEADING_TOP, WIDTH, round(HEADING_SIZE) + 2),
                font_size=HEADING_SIZE)

# The colons, painted on the board between the pairs they separate, not carried on a card,
# and in the cards' own ink since they read as part of the time
canvas.pen = INK
dot = max(2, CELL_W // 8)
for left in colons:
    middle = left + (COLON_W - dot) // 2
    for row in range(ROWS):
        top = TOP + row * (CELL_H + ROW_GAP)
        canvas.rectangle(rect(middle, top + HALF // 2, dot, dot))
        canvas.rectangle(rect(middle, top + HALF + HALF // 2 - dot, dot, dot))

screen.update(canvas, rotation=90)


def call_up(index):
    """Set every card after the page it should be showing, a column's text starting at its own.

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
due = time.ticks_add(time.ticks_ms(), int(HOLD * 1000))

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        now = time.ticks_ms()
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
                part = min(1.0, time.ticks_diff(now, started) / FLAP_MS)
                step = (showing_at[row][card] + 1) % len(card_drum[card])
                falling(row, card, showing_at[row][card], step, part)
                drew = True

                if part >= 1.0:
                    showing_at[row][card] = step
                    settled(row, card, step)
                    turning_at[row][card] = (now if step != wanted_at[row][card] else None)

        if drew:
            screen.update(canvas, rotation=90)
        elif resting and time.ticks_diff(now, due) >= 0:
            page = (page + 1) % len(PAGES)
            call_up(page)
            due = time.ticks_add(now, int(HOLD * 1000))
        else:
            time.sleep_ms(10)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
