from picovector import color, font, image, rect, shape

"""
Drawing: CRT terminal
A green screen terminal. An operator types a command and the machine answers, on a tube that glows.
Section: Mechanical and glowing displays
"""

# Entry: screenA rotation=90: graphics file=crt_terminal.py fps=100   (a 2.8" screen)

# Constants for drawing
TINT = color.rgb(51, 255, 51)
TERM_FONT = font.ark
CELL_SCALE = 1
LEADING = 4

BORDER = 6
PAD = 12
CORNER = 20
EDGE = 1
BACKGROUND = color.rgb(0, 34, 17)
SURROUND = color.black
EDGE_COLOUR = color.rgb(0, 119, 68)

SPACING = 3
SCANLINE = 160
TUBE = 0.7
GLOW_FROM = 35
GLOW = 500
GLOW_SPREAD = 14
GRAIN = 5

CPS = 1
CURSOR_MS = 500
THINK_MS = 500
READ_MS = 1500
END_MS = 3000
PROMPT = "> "

# The session, a line to an entry. One opening with PROMPT is typed, every other arrives whole. A tuple
# is a table, the character filling between its columns and then its rows, the columns spread across the
# tube. A 2.8" tube is 40 columns wide, and a longer line wraps at a space
SESSION = (
    "FX-11 TIMESHARING SYSTEM V2.4",
    "48K CORE   TAPE 0 READY",
    "",
    "> LOGIN OPERATOR",
    "PASSWORD ACCEPTED",
    "LAST LOGIN 14 MAR 06:12",
    "",
    "> LIST SITES /ACTIVE",
    (" ",
     ("SITE", "NAME", "STATE", "LOAD"),
     ("01", "HILLSIDE", "UP", "118"),
     ("02", "WEIR LANE", "UP", "94"),
     ("03", "CROSSGATE", "STANDBY", "0"),
     ("04", "TANNERY ROW", "UP", "207")),
    "4 SITES, 3 ACTIVE, LOAD 419",
    "",
    "> RUN DIAGNOSTIC 3",
    (".",
     ("CHANNEL 0", "PASS"),
     ("CHANNEL 1", "PASS"),
     ("CHANNEL 2", "RETRY 2, PASS"),
     ("CHANNEL 3", "NO CARRIER")),
    "1 FAULT LOGGED TO TAPE 0",
    "",
    "> MAIL",
    "1 MESSAGE WAITING",
    "FROM: NIGHT SHIFT",
    "CROSSGATE STAYS ON STANDBY UNTIL THE WEATHER CLEARS. LEAVE IT BE.",
    "",
    "> LOGOUT",
    "SESSION ENDED.",
    "00:14 CONNECTED.",
)

# The canvas this drawing expects, a 2.8" screen at rotation=90, stated as the module body
# cannot see the canvas
WIDTH, HEIGHT = 320, 240

probe = image(round(TERM_FONT.height * CELL_SCALE) * 3, round(TERM_FONT.height * CELL_SCALE) * 3)
probe.font = TERM_FONT


def lettering_rows(letters):
    """Measure which rows these characters fill from y zero."""
    probe.pen = BACKGROUND
    probe.clear()
    probe.pen = color.white
    for letter in letters:
        probe.text(letter, 0, 0, CELL_SCALE)

    raw, stride = probe.raw, probe.stride
    drawn = [y for y in range(probe.height)
             if any(raw[y * stride + x * 4] > 100 for x in range(probe.width))]
    return drawn[0], drawn[-1]


LETTERING_TOP, LETTERING_END = lettering_rows("HWgjy0")
CAP_TOP, CAP_END = lettering_rows("HW0")

CELL_W = round(probe.measure_text("M", font_size=CELL_SCALE)[0])
CELL_H = LETTERING_END - LETTERING_TOP + 1
PITCH = CELL_H + LEADING * CELL_SCALE
INSET = BORDER + PAD
COLUMNS = (WIDTH - INSET * 2) // CELL_W
ROWS = (HEIGHT - INSET * 2) // PITCH

TEXT_X = (WIDTH - COLUMNS * CELL_W) // 2
TEXT_Y = (HEIGHT - ((ROWS - 1) * PITCH + CELL_H)) // 2
FACE = rect(BORDER, BORDER, WIDTH - BORDER * 2, HEIGHT - BORDER * 2)
CURSOR_UP = CAP_TOP - LETTERING_TOP
CURSOR_H = CAP_END - CAP_TOP + 1


def gap(width, fill):
    """A gap between two columns, a run of the fill with a space at either end where there is room."""
    if width < 3:
        return " " * width
    return " " + fill * (width - 2) + " "


def table(fill, rows):
    """
    Lay a table's rows out as lines across the tube, each column as wide as its widest entry.

    The first column starts at the left edge and the last ends at the right, what is spare spread
    evenly between them and the last column's padding joining the gap before it.
    """
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    gaps = len(widths) - 1
    spare = max(gaps, COLUMNS - sum(widths))
    laid = []
    for row in rows:
        line = ""
        for column in range(gaps):
            between = spare // gaps + (column < spare % gaps)
            if column == gaps - 1:
                between += widths[gaps] - len(row[gaps])
            line += row[column] + " " * (widths[column] - len(row[column])) + gap(between, fill)
        laid.append(line + row[gaps])
    return laid


# The session as the lines the machine prints, each table laid out to this tube's width
LINES = []
for part in SESSION:
    if isinstance(part, str):
        LINES.append(part)
    else:
        LINES.extend(table(part[0], part[1:]))

CHARSET = "".join(sorted({letter for line in LINES for letter in line} - {" "}))
glyphs = image(CELL_W * len(CHARSET), CELL_H)
glyphs.font = TERM_FONT
glyphs.pen = color.transparent
glyphs.clear()
glyphs.pen = TINT
for index, letter in enumerate(CHARSET):
    wide = glyphs.measure_text(letter, font_size=CELL_SCALE)[0]
    glyphs.text(letter, index * CELL_W + round((CELL_W - wide) / 2), -LETTERING_TOP, CELL_SCALE)

CELL_AT = {letter: index * CELL_W for index, letter in enumerate(CHARSET)}

source = rect(0, 0, CELL_W, CELL_H)
target = rect(0, 0, CELL_W, CELL_H)

lines = []
writing = ""


def newline():
    """End the line being written, and scroll where that fills the page."""
    global writing
    lines.append(writing)
    writing = ""
    while len(lines) >= ROWS:
        lines.pop(0)


def wrap():
    """
    Carry what does not fit of the line being written onto the lines below, as a terminal does.

    It breaks at the last space that fits, or at the edge for a word longer than the tube is wide.
    """
    global writing
    while len(writing) > COLUMNS:
        space = writing.rfind(" ", 0, COLUMNS + 1)
        cut, rest = (space, space + 1) if space > 0 else (COLUMNS, COLUMNS)
        carried = writing[rest:]
        writing = writing[:cut]
        newline()
        writing = carried


def print_line(text):
    """Print a whole line from the machine, an empty one as a blank line."""
    global writing
    writing = text
    wrap()
    newline()


def put(canvas, text, row):
    """Put one line of characters on the page, each blitted into its own cell on the pitch."""
    target.y = TEXT_Y + row * PITCH
    for column, letter in enumerate(text):
        at = CELL_AT.get(letter)
        if at is None:
            continue
        source.x = at
        target.x = TEXT_X + column * CELL_W
        canvas.blit(glyphs, source, target)


def page(canvas, cursor_on):
    """Draw the page and cursor, then the tube's filters, which reach nothing drawn after."""
    canvas.pen = SURROUND
    canvas.clear()
    canvas.pen = BACKGROUND
    canvas.shape(shape.rounded_rectangle(FACE, CORNER))
    if EDGE:
        canvas.pen = EDGE_COLOUR
        canvas.shape(shape.rounded_rectangle(FACE, CORNER).stroke(EDGE, shape.ALIGN_INNER))

    for row, line in enumerate(lines):
        put(canvas, line, row)

    row = len(lines)
    put(canvas, writing, row)
    if cursor_on:
        canvas.pen = TINT
        canvas.rectangle(rect(TEXT_X + len(writing) * CELL_W,
                              TEXT_Y + row * PITCH + CURSOR_UP, CELL_W, CURSOR_H))

    canvas.crt(SPACING, SCANLINE, TUBE)
    canvas.bloom(GLOW_FROM, GLOW, GLOW_SPREAD)
    if GRAIN:
        canvas.noise(GRAIN, 0)


entry = 0                   # Which of the session's lines is being written
typed = 0                   # And how much of it has arrived, where the operator is typing it
served = 0                  # Counts what has reached the tube, so a redraw is never missed
due = 0                     # When the terminal is next free to write, in elapsed ms
shown = None


def draw(canvas, elapsed):
    global entry, typed, served, due, shown, writing
    if shown is None and (canvas.width, canvas.height) != (WIDTH, HEIGHT):
        raise ValueError(f'this drawing is laid out for {WIDTH}x{HEIGHT}, a 2.8" screen at '
                         f"rotation=90, and was given {canvas.width}x{canvas.height}")

    now = elapsed * 1000
    if now >= due:
        if entry >= len(LINES):
            del lines[:]
            writing = ""
            entry, typed, served = 0, 0, served + 1
        elif LINES[entry].startswith(PROMPT):
            line = LINES[entry]
            arrived = line[typed:typed + CPS]
            typed += len(arrived)
            writing += arrived
            wrap()
            served += 1
            if typed == len(line):
                newline()
                entry, typed = entry + 1, 0
                due = now + THINK_MS
        else:
            print_line(LINES[entry])
            entry, served = entry + 1, served + 1
            if entry >= len(LINES):
                due = now + END_MS
            elif LINES[entry].startswith(PROMPT):
                due = now + READ_MS

    # The canvas keeps the last page, so one is only drawn where something changed
    frame = (served, bool(now // CURSOR_MS % 2))
    if frame != shown:
        page(canvas, frame[1])
        shown = frame
