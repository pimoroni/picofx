from picovector import color, font, image, rect, shape

"""
Drawing: Split-flap departures
A split-flap departures board, each card climbing through the drum to its letter.
Section: Transport signs
"""

# Entry: screenA rotation=90: graphics file=split_flap_departures.py fps=100   (a 2.8" screen)

# Constants for drawing
FLAP_FONT = "/rom/fonts/Oswald.af"

DIGITS = " 0123456789"
ALPHA = " ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BOTH = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
FLAP_MS = 150
HOLD_MS = 2000
CARD = color.rgb(34, 34, 38)
TEXT_COLOUR = color.rgb(238, 238, 232)
HEADING = color.rgb(232, 176, 24)
SPLIT = color.rgb(8, 8, 9)
BOARD = color.black
GAP = 1
COLUMN_GAP = 12
COLON_W = 9

CARD_PAD = 2
ROW_GAP = 6
SPLIT_H = 1
EDGE = 2
CORNER = 2
MARGIN = 4
HEADING_GAP = 4
HEADING_MAX = 1
LETTER_MAX = 24
ANTIALIAS = image.X2

COLUMNS = (("TIME", 4, 2, DIGITS), ("DEST", 6, 0, ALPHA), ("GATE", 3, 0, BOTH))

PAGES = (
    (("11:32", "LONDON", "A42"), ("11:55", "TOKYO", "B32"), ("12:08", "PARIS", "C75"),
     ("12:24", "MADRID", "A06"), ("12:42", "MOSCOW", "D35"), ("13:05", "MILAN", "B71")),
    (("13:18", "DUBLIN", "C12"), ("13:40", "VIENNA", "A18"), ("14:02", "BERLIN", "B44"),
     ("14:15", "OSLO", "D19"), ("14:31", "LISBON", "C63"), ("14:50", "PRAGUE", "A27")),
    (("15:06", "ATHENS", "B08"), ("15:22", "MALAGA", "D51"), ("15:44", "ZURICH", "A33"),
     ("16:01", "KRAKOW", "C26"), ("16:20", "SOFIA", "B47"), ("16:38", "RIGA", "D15")),
)

# The canvas this drawing expects, a 2.8" screen at rotation=90. The module body cannot see
# the canvas, and the layout below is built from it, so it is stated and checked on the first call
WIDTH, HEIGHT = 320, 240

ROWS = len(PAGES[0])
CARDS = sum(wide for _, wide, _, _drum in COLUMNS)

spare = MARGIN * 2 + COLUMN_GAP * (len(COLUMNS) - 1)
for _, wide, colon, _drum in COLUMNS:
    spare += GAP * (wide - 1) + (COLON_W - GAP if colon else 0)

CELL_W = (WIDTH - spare) // CARDS
COLUMN_SPACE = COLUMN_GAP + (WIDTH - spare - CELL_W * CARDS) // (len(COLUMNS) - 1)

flap_font = font.load(FLAP_FONT)

# measure_text needs an image, and the canvas is not here yet
ruler = image(8, 8)
ruler.font = flap_font
ruler.antialias = ANTIALIAS

REFERENCE = 64
WIDTH_PER_PX = max(ruler.measure_text(letter, font_size=REFERENCE)[0]
                   for letter in BOTH) / REFERENCE


def lettering_rows(size, letters):
    """Measure which rows these letters fill at this size, font_size being the em height."""
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

SIZE = min(LETTER_MAX / LETTERING_PER_PX, CELL_W / WIDTH_PER_PX)
LETTER_H = round(LETTERING_PER_PX * SIZE)
CELL_H = LETTER_H + CARD_PAD * 2
CELL_H += CELL_H % 2
HALF = CELL_H // 2

LETTERING_TOP = (CELL_H - LETTER_H) // 2 - round(lettering_rows(SIZE, "HW8O")[0])
EM_BOX = round(SIZE) + 2

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

HEADING_SIZE = SIZE * HEADING_MAX
starts = []
card = 0
for name, wide, _, _drum in COLUMNS:
    starts.append(card)
    room = spots[card + wide - 1] + CELL_W - spots[card] + COLUMN_SPACE
    HEADING_SIZE = min(HEADING_SIZE,
                       room / (ruler.measure_text(name, font_size=REFERENCE)[0] / REFERENCE))
    card += wide

del ruler

HEADING_LETTER_H = round(LETTERING_PER_PX * HEADING_SIZE)
HEADING_TOP = -round(lettering_rows(HEADING_SIZE, "HW8O")[0])

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
        made.text(letter, rect(left + round((CELL_W - wide) / 2), LETTERING_TOP, CELL_W, EM_BOX),
                  font_size=SIZE)

    return made


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


def settled(canvas, row, card, index):
    """A card at rest, both halves showing the same character."""
    left, top = place(row, card)
    drum = sheets[card_drum[card]]
    target.x, target.w = left, CELL_W
    for lower in (False, True):
        target.y, target.h = top + (HALF if lower else 0), HALF
        canvas.blit(drum, half_of(index, lower), target)


def falling(canvas, row, card, from_index, to_index, part):
    """Draw a card part way down."""
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

    if showing <= EDGE:
        canvas.pen = SPLIT
        canvas.rectangle(target)
    else:
        canvas.blit(drum, half_of(index, not above), target)


def board(canvas):
    """Draw the blank cards, the headings and the colons, which no falling card writes over."""
    if (canvas.width, canvas.height) != (WIDTH, HEIGHT):
        raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                         f"rotation=90, and was given {canvas.width}x{canvas.height}")

    canvas.font = flap_font
    canvas.antialias = ANTIALIAS
    canvas.pen = BOARD
    canvas.clear()

    for row in range(ROWS):
        for card in range(CARDS):
            settled(canvas, row, card, 0)

    canvas.pen = HEADING
    for (name, _wide, _, _drum), start in zip(COLUMNS, starts):
        canvas.text(name, rect(spots[start], MARGIN + HEADING_TOP, WIDTH, round(HEADING_SIZE) + 2),
                    font_size=HEADING_SIZE)

    canvas.pen = TEXT_COLOUR
    dot = max(2, CELL_W // 8)
    for left in colons:
        middle = left + (COLON_W - dot) // 2
        for row in range(ROWS):
            top = TOP + row * (CELL_H + ROW_GAP)
            canvas.rectangle(rect(middle, top + HALF // 2, dot, dot))
            canvas.rectangle(rect(middle, top + HALF + HALF // 2 - dot, dot, dot))


showing_at = [[0] * CARDS for _ in range(ROWS)]
wanted_at = [[0] * CARDS for _ in range(ROWS)]
turning_at = [[None] * CARDS for _ in range(ROWS)]  # When each started falling, in ms into the page


def call_up(index):
    """Set every card after the page it should be showing, a column's text starting at its own."""
    for row in range(ROWS):
        for card in range(CARDS):
            wanted_at[row][card] = 0

        for (_, wide, _, drum_of), start, text in zip(COLUMNS, starts, PAGES[index][row]):
            letters = text.replace(":", "")
            for offset in range(min(wide, len(letters))):
                wanted_at[row][start + offset] = max(0, drum_of.find(letters[offset]))


call_up(0)
page = 0
standing = False
page_from = None        # When the page in progress was called up, in elapsed ms
due = 0                 # When the next page is called up once this one stands, in elapsed ms


def draw(canvas, elapsed):
    global page, standing, page_from, due
    if page_from is None:
        board(canvas)
        page_from = elapsed * 1000

    now = elapsed * 1000 - page_from
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
            falling(canvas, row, card, showing_at[row][card], step, part)
            drew = True

            if part >= 1.0:
                showing_at[row][card] = step
                settled(canvas, row, card, step)
                turning_at[row][card] = (now if step != wanted_at[row][card] else None)

    if drew:
        return

    if resting and not standing:
        standing = True
        due = elapsed * 1000 + HOLD_MS
    elif resting and elapsed * 1000 >= due:
        page = (page + 1) % len(PAGES)
        call_up(page)
        standing = False
        page_from = elapsed * 1000
