from mighty_fx import MightyFX, SPCE
from timing import Pacer, Roller
from screens import Screen280
from picovector import color, font, image, rect, shape

"""
Draw a green screen terminal of the kind wheeled up to a minicomputer. An operator types a
command a character at a time and the machine answers a line at a time, on a tube that glows.

The tube is three filters over plain lettering, scanlines fading into the corners, a bloom and a grain.

Filters rewrite the pixels they cover, so the page is held as text and drawn in full each frame,
then filtered once. No ROM face is fixed pitch, so the characters are baked into a strip of cells.

Press "Boot" to exit the program.

Program: CRT terminal
Section: Mechanical and glowing displays
"""

# Constants for drawing
TINT = color.rgb(51, 255, 51)   # The phosphor, P1 green, or rgb(255, 187, 0) for amber
TERM_FONT = font.ark            # The character ROM. The narrowest ROM face with a lowercase
CELL_SCALE = 1                  # How large the character ROM is drawn, in whole steps. 2 gives a bolder
                                # 20x10 page with unmistakable scanlines, but the session's listing then wraps
LEADING = 4                     # Blank rows between one line of characters and the next

# The tube's face, which no CRT fills to its own edge. BORDER is the surround outside it and PAD the
# unused face inside, between the two keeping the lettering out of the corners the curve darkens most
BORDER = 6
PAD = 12
CORNER = 20                             # How far the face is rounded off, a tube having no square corner
EDGE = 1                                # A line at the face's edge, the glass catching light. 0 leaves it off
BACKGROUND = color.rgb(0, 34, 17)       # An unlit tube, dark green and not black so the curve has something to darken
SURROUND = color.black                  # Outside the face
EDGE_COLOUR = color.rgb(0, 119, 68)     # The face's edge, well clear of the background so the glow leaves it

# SCANLINE darkens a scan row every SPACING panel pixels, and TUBE scales the curve and scanlines. At
# 1.0 a corner is a sixth as bright as the middle
SPACING = 3
SCANLINE = 160
TUBE = 0.7
GLOW_FROM = 35                  # The brightness a pixel glows from, low enough that all lit type does
GLOW = 500                      # How much of the halo is added back, 255 being all of it
GLOW_SPREAD = 14                # How far it reaches, in panel pixels
GRAIN = 5                       # A signed grain under half a level, breaking up the banding 16 levels
                                # a channel leave in the glow. 0 turns it off

CPS = 1                         # Characters the operator types a frame
CURSOR_MS = 500                 # How long the block cursor stays on, and off
THINK_MS = 500                  # After a typed command, before the machine answers
READ_MS = 1500                  # After an answer, so it can be read before the next command
END_MS = 3000                   # At the end of the session, before the tube clears and it runs again
PROMPT = "> "                   # What opens a line the operator types

# The session, a line to an entry. One opening with PROMPT is typed, every other arrives whole. Replace
# these and the terminal says something else
SESSION = (
    "FX-11 TIMESHARING SYSTEM  V2.4",
    "48K CORE   TAPE 0 READY",
    "",
    "> LOGIN OPERATOR",
    "PASSWORD ACCEPTED",
    "LAST LOGIN 14 MAR 06:12",
    "",
    "> LIST SITES /ACTIVE",
    "SITE  NAME            STATE         LOAD",
    "01    HILLSIDE        UP             118",
    "02    WEIR LANE       UP              94",
    "03    CROSSGATE       STANDBY          0",
    "04    TANNERY ROW     UP             207",
    "4 SITES, 3 ACTIVE, LOAD 419",
    "",
    "> RUN DIAGNOSTIC 3",
    "CHANNEL 0 ............. PASS",
    "CHANNEL 1 ............. PASS",
    "CHANNEL 2 ............. RETRY 2, PASS",
    "CHANNEL 3 ............. NO CARRIER",
    "1 FAULT LOGGED TO TAPE 0",
    "",
    "> MAIL",
    "1 MESSAGE WAITING",
    "FROM: NIGHT SHIFT",
    "CROSSGATE STAYS ON STANDBY UNTIL",
    "THE WEATHER CLEARS. LEAVE IT BE.",
    "",
    "> LOGOUT",
    "SESSION ENDED. 00:14 CONNECTED.",
)

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# Drawn landscape and turned a quarter onto the panel at each update
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height

probe = image(round(TERM_FONT.height * CELL_SCALE) * 3, round(TERM_FONT.height * CELL_SCALE) * 3)
probe.font = TERM_FONT


def lettering_rows(letters):
    """Measure which rows these characters fill from y zero, as the face's height carries blank rows."""
    probe.pen = BACKGROUND
    probe.clear()
    probe.pen = color.white
    for letter in letters:
        probe.text(letter, 0, 0, CELL_SCALE)

    raw, stride = probe.raw, probe.stride
    drawn = [y for y in range(probe.height)
             if any(raw[y * stride + x * 4] > 100 for x in range(probe.width))]
    return drawn[0], drawn[-1]


LETTERING_TOP, LETTERING_END = lettering_rows("HWgjy0")     # Everything a cell has to hold, a descender included
CAP_TOP, CAP_END = lettering_rows("HW0")                    # And a capital alone, which is the cursor's own height

CELL_W = round(probe.measure_text("M", font_size=CELL_SCALE)[0])
CELL_H = LETTERING_END - LETTERING_TOP + 1
PITCH = CELL_H + LEADING * CELL_SCALE   # One line of characters to the next
INSET = BORDER + PAD                    # The least the lettering is kept from the panel's edge
COLUMNS = (WIDTH - INSET * 2) // CELL_W
ROWS = (HEIGHT - INSET * 2) // PITCH

# The page centred on what whole cells leave over, measured to the last row's lettering
TEXT_X = (WIDTH - COLUMNS * CELL_W) // 2
TEXT_Y = (HEIGHT - ((ROWS - 1) * PITCH + CELL_H)) // 2
FACE = rect(BORDER, BORDER, WIDTH - BORDER * 2, HEIGHT - BORDER * 2)
CURSOR_UP = CAP_TOP - LETTERING_TOP           # Where a capital sits inside its cell, so the block sits there
CURSOR_H = CAP_END - CAP_TOP + 1

# The character ROM, each character the session uses centred in a cell once. A space needs none
CHARSET = "".join(sorted({letter for line in SESSION for letter in line} - {" "}))
glyphs = image(CELL_W * len(CHARSET), CELL_H)
glyphs.font = TERM_FONT
glyphs.pen = color.transparent
glyphs.clear()
glyphs.pen = TINT
for index, letter in enumerate(CHARSET):
    wide = glyphs.measure_text(letter, font_size=CELL_SCALE)[0]
    glyphs.text(letter, index * CELL_W + round((CELL_W - wide) / 2), -LETTERING_TOP, CELL_SCALE)

# Where each character sits in the strip, looked up as the page is drawn
CELL_AT = {letter: index * CELL_W for index, letter in enumerate(CHARSET)}

print(f"{COLUMNS} columns by {ROWS} rows, in cells of {CELL_W}x{CELL_H} on a pitch of {PITCH}")
print(f"{len(CHARSET)} characters baked, {glyphs.width}x{glyphs.height}")

# Two rects moved and never made, so a page of cells allocates nothing a frame
source = rect(0, 0, CELL_W, CELL_H)
target = rect(0, 0, CELL_W, CELL_H)

# The finished lines and the one the cursor is on, with no memory of what scrolled off
lines = []
writing = ""


def newline():
    """End the line being written, and scroll where that fills the page."""
    global writing
    lines.append(writing)
    writing = ""
    while len(lines) >= ROWS:
        lines.pop(0)


def print_line(text):
    """Print a whole line from the machine, broken where it is longer than the tube is wide."""
    global writing
    # One pass at least, so an empty line still prints as a blank one
    for at in range(0, max(len(text), 1), COLUMNS):
        writing = text[at:at + COLUMNS]
        newline()


def put(text, row):
    """Put one line of characters on the page, each blitted into its own cell on the pitch."""
    target.y = TEXT_Y + row * PITCH
    for column, letter in enumerate(text):
        at = CELL_AT.get(letter)
        if at is None:
            continue

        source.x = at
        target.x = TEXT_X + column * CELL_W
        canvas.blit(glyphs, source, target)


def draw(cursor_on):
    """Draw one frame, the page and cursor, then the tube's filters, which reach nothing drawn after."""
    canvas.pen = SURROUND
    canvas.clear()
    canvas.pen = BACKGROUND
    canvas.shape(shape.rounded_rectangle(FACE, CORNER))
    if EDGE:
        canvas.pen = EDGE_COLOUR
        canvas.shape(shape.rounded_rectangle(FACE, CORNER).stroke(EDGE, shape.ALIGN_INNER))

    for row, line in enumerate(lines):
        put(line, row)

    # The line being written goes under the finished ones, the cursor after its last character
    row = len(lines)
    put(writing, row)
    if cursor_on:
        canvas.pen = TINT
        canvas.rectangle(rect(TEXT_X + len(writing) * CELL_W,
                              TEXT_Y + row * PITCH + CURSOR_UP, CELL_W, CURSOR_H))

    canvas.crt(SPACING, SCANLINE, TUBE)
    canvas.bloom(GLOW_FROM, GLOW, GLOW_SPREAD)
    if GRAIN:
        canvas.noise(GRAIN, 0)


entry = 0                   # Which line of the session is being written
typed = 0                   # And how much of it has arrived, where the operator is typing it
served = 0                  # Counts what has reached the tube, so a redraw is never missed
held = Roller()             # When the terminal is next free to write, at once to begin with
pacer = Pacer(0.01)
shown = None

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if held.is_due():
            if entry >= len(SESSION):
                # The session is over, so the operator turns the tube out and it starts again
                del lines[:]
                writing = ""
                entry, typed, served = 0, 0, served + 1
            elif SESSION[entry].startswith(PROMPT):
                # The operator's typing a character at a time, with a beat at the end of the line
                line = SESSION[entry]
                typed = min(typed + CPS, len(line))
                writing = line[:typed]
                served += 1
                if typed == len(line):
                    newline()
                    entry, typed = entry + 1, 0
                    held.restart(THINK_MS / 1000)
            else:
                # The machine's answer, a line to a frame, which makes it faster than the typing
                print_line(SESSION[entry])
                entry, served = entry + 1, served + 1
                if entry >= len(SESSION):
                    held.restart(END_MS / 1000)
                elif SESSION[entry].startswith(PROMPT):
                    held.restart(READ_MS / 1000)

        # A frame is the whole page drawn again, so one is only worth drawing where something changed
        elapsed = pacer.elapsed
        frame = (served, bool(elapsed // CURSOR_MS % 2))
        if frame != shown:
            draw(frame[1])
            screen.update(canvas, rotation=90)
            shown = frame

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
