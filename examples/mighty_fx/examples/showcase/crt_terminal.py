import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import color, font, image, rect, shape

"""
Draw a green screen terminal, of the kind wheeled up to a minicomputer: an operator typing
a command a character at a time and the machine answering a line at a time, on a tube that
glows.

The tube is three filters over a page of plain lettering: scanlines with a falloff into
the corners, a bloom so a lit character spills into the dark around it, and a grain.
phosphor() does all three in one call and tints the page as well, which is the shorter
route; they are run separately here so the tube's curve is a setting, its full strength
taking a corner down to a sixth.

The filters rewrite the pixels they cover, so nothing can be added to a page already
filtered. That is what shapes the code: the page is held as text and drawn again in full
every frame, then filtered once. Drawing it is under 30ms of a 150ms frame, so the scroll
comes for nothing, a line leaving the top of the tube being a line dropped from a list.

No CRT reaches its own edge, so the face is a rounded rectangle of dark green on a black
surround, which keeps the lettering out of the corners the curve darkens most and gives
that curve something to darken.

A terminal is fixed pitch and none of the ROM faces is: their capitals share a width but a
space and a comma do not, so the character set is baked once into a strip of cells and the
page blits cells onto the pitch.

Press "Boot" to exit the program.
"""

# Constants for drawing
TINT = color.rgb(51, 255, 51)   # The phosphor. P1 green here; rgb(255, 187, 0) is the amber tube
TERM_FONT = "ark"               # The character ROM. The narrowest ROM face with a lowercase
# Whole steps. 2 gives a bolder page of 20 columns by 10 rows, and is the setting whose scanlines are
# unmistakable, a scan row modulating a two pixel stroke where it swallows a one pixel one. The session
# below outgrows it, though: its listing wraps, so a page that size wants its own shorter lines
CELL_SCALE = 1
LEADING = 4                     # Blank rows between one line of characters and the next

# The tube's face, which no CRT fills to its own edge. BORDER is the surround outside it and PAD the
# unused face inside, between the two keeping the lettering out of the corners the curve darkens most
BORDER = 6
PAD = 12
CORNER = 20                     # How far the face is rounded off, a tube having no square corner
EDGE = 1                        # A line at the face's edge, the glass catching light. 0 leaves it off
GROUND = color.rgb(0, 34, 17)   # An unlit tube, dark green rather than black so the curve has a ground
SURROUND = color.black          # Outside the face
EDGE_INK = color.rgb(0, 119, 68)  # The face's edge, well clear of the ground so the glow leaves it

# The tube's curve and scanlines. SCANLINE is how far a scan row is darkened and SPACING how many panel
# pixels apart those rows are; TUBE is how much of the curve to keep, and scales both the corners and the
# scanlines. At 1.0 a corner is a sixth as bright as the middle, which is why the lettering is inset
SPACING = 3
SCANLINE = 160
TUBE = 0.7
GLOW_FROM = 35                  # The brightness a pixel glows from, low enough that all lit type does
GLOW = 500                      # How much of the halo is added back, 255 being all of it
GLOW_SPREAD = 14                # How far it reaches, in panel pixels
# The glow is a smooth ramp and the panel has 16 levels a channel to hold it in, so it lands as patches
# with hard edges. A signed grain scatters those edges and reads as the tube's own noise, kept under half
# a level since the ground sits a level above black and has room to move both ways. 0 turns it off
GRAIN = 5

CPS = 1                         # Characters the operator types a frame, a frame being about 150ms
CURSOR_MS = 500                 # How long the block cursor stays on, and off
THINK_MS = 500                  # After a typed command, before the machine answers
READ_MS = 1500                  # After an answer, so it can be read before the next command
END_MS = 3000                   # At the end of the session, before the tube clears and it runs again
PROMPT = "> "                   # A line the operator types rather than the machine printing it

# The session, an entry to a line. A line opening with PROMPT is typed a character at a time; every
# other line is the machine's and arrives whole. Replace these and the terminal says something else:
# a console session is all this file is under the tube
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

# A terminal is wider than it is tall, so the canvas is drawn landscape and every update turns it a
# quarter onto the panel. From the screen, not image(), which puts it in SRAM: the whole page is
# drawn and filtered every frame, and the heap is PSRAM
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height

term_font = getattr(font, TERM_FONT)
probe = image(round(term_font.height * CELL_SCALE) * 3, round(term_font.height * CELL_SCALE) * 3)
probe.font = term_font


def ink_rows(letters):
    """Which rows these characters' ink covers, drawn from a y of zero.

    Read off a drawing, because the face's own height carries blank rows above the characters and below
    them, where it is the ink that has to sit in a cell.
    """
    probe.pen = GROUND
    probe.clear()
    probe.pen = color.white
    for letter in letters:
        probe.text(letter, 0, 0, CELL_SCALE)

    raw, stride = probe.raw, probe.stride
    inked = [y for y in range(probe.height)
             if any(raw[y * stride + x * 4] > 100 for x in range(probe.width))]
    return inked[0], inked[-1]


INK_TOP, INK_END = ink_rows("HWgjy0")   # Everything a cell has to hold, a descender included
CAP_TOP, CAP_END = ink_rows("HW0")      # And a capital alone, which is the cursor's own height

CELL_W = round(probe.measure_text("M", font_size=CELL_SCALE)[0])
CELL_H = INK_END - INK_TOP + 1
PITCH = CELL_H + LEADING * CELL_SCALE   # One line of characters to the next
INSET = BORDER + PAD                    # The least the lettering is kept from the panel's edge
COLUMNS = (WIDTH - INSET * 2) // CELL_W
ROWS = (HEIGHT - INSET * 2) // PITCH
# Whole cells rarely divide the face evenly, so the page is centred on what is left over and not
# laid from the inset, which would collect the remainder down one side. Measured to the ink: the last
# row's leading is not part of the page, and counting it would push everything up
TEXT_X = (WIDTH - COLUMNS * CELL_W) // 2
TEXT_Y = (HEIGHT - ((ROWS - 1) * PITCH + CELL_H)) // 2
FACE = rect(BORDER, BORDER, WIDTH - BORDER * 2, HEIGHT - BORDER * 2)
CURSOR_UP = CAP_TOP - INK_TOP           # Where a capital sits inside its cell, so the block sits there
CURSOR_H = CAP_END - CAP_TOP + 1

# The character ROM: every character the session uses, once, each centred in a cell of the pitch. A
# space is left out, an unlit cell needing nothing drawn in it
CHARSET = "".join(sorted({letter for line in SESSION for letter in line} - {" "}))
glyphs = image(CELL_W * len(CHARSET), CELL_H)
glyphs.font = term_font
glyphs.pen = color.transparent
glyphs.clear()
glyphs.pen = TINT
for index, letter in enumerate(CHARSET):
    wide = glyphs.measure_text(letter, font_size=CELL_SCALE)[0]
    glyphs.text(letter, index * CELL_W + round((CELL_W - wide) / 2), -INK_TOP, CELL_SCALE)

# Where each character sits in the strip, looked up as the page is drawn
CELL_AT = {letter: index * CELL_W for index, letter in enumerate(CHARSET)}

print(f"{COLUMNS} columns by {ROWS} rows, in cells of {CELL_W}x{CELL_H} on a pitch of {PITCH}")
print(f"{len(CHARSET)} characters baked, {glyphs.width}x{glyphs.height}")

# Two rects, moved and not made: a page is up to a thousand cells and a rect apiece every frame is
# what makes an animation judder, the heap moving faster than the collector likes
source = rect(0, 0, CELL_W, CELL_H)
target = rect(0, 0, CELL_W, CELL_H)

# What the tube shows: the lines already finished, and the one the cursor is on. A terminal has no
# memory of what scrolled off the top, and neither has this
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
    """A whole line from the machine, broken where it is longer than the tube is wide."""
    global writing
    for at in range(0, max(len(text), 1), COLUMNS):
        writing = text[at:at + COLUMNS]
        newline()


def put(text, row):
    """One line of characters, each blitted into its own cell on the pitch."""
    target.y = TEXT_Y + row * PITCH
    for column, letter in enumerate(text):
        at = CELL_AT.get(letter)
        if at is None:
            continue

        source.x = at
        target.x = TEXT_X + column * CELL_W
        canvas.blit(glyphs, source, target)


def draw(cursor_on):
    """One frame: the page, the cursor over it, and the tube over both.

    The order matters. Everything lit has to be down before the filters run, or it comes out flat: a
    cursor drawn after them carries no glow, and one drawn after the scanlines is not cut by them.
    """
    canvas.pen = SURROUND
    canvas.clear()
    canvas.pen = GROUND
    canvas.shape(shape.rounded_rectangle(FACE, CORNER))
    if EDGE:
        canvas.pen = EDGE_INK
        canvas.shape(shape.rounded_rectangle(FACE, CORNER).stroke(EDGE, shape.ALIGN_INNER))

    for row, line in enumerate(lines):
        put(line, row)

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
held_to = time.ticks_ms()   # When the terminal is next free to write, a pause sitting further off
started = time.ticks_ms()
shown = None

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if time.ticks_diff(time.ticks_ms(), held_to) >= 0:
            if entry >= len(SESSION):
                # The session is over, so the operator turns the tube out and it starts again
                del lines[:]
                writing = ""
                entry, typed, served = 0, 0, served + 1
            elif SESSION[entry].startswith(PROMPT):
                # The operator's own typing, so it arrives a character at a time, and the machine waits
                # a beat at the end of the line as though reading it
                line = SESSION[entry]
                typed = min(typed + CPS, len(line))
                writing = line[:typed]
                served += 1
                if typed == len(line):
                    newline()
                    entry, typed = entry + 1, 0
                    held_to = time.ticks_add(time.ticks_ms(), THINK_MS)
            else:
                # The machine's answer, a line to a frame, which makes it faster than the typing
                print_line(SESSION[entry])
                entry, served = entry + 1, served + 1
                if entry >= len(SESSION):
                    held_to = time.ticks_add(time.ticks_ms(), END_MS)
                elif SESSION[entry].startswith(PROMPT):
                    held_to = time.ticks_add(time.ticks_ms(), READ_MS)

        # A frame is the whole page drawn again, so one is only worth drawing where something changed
        elapsed = time.ticks_diff(time.ticks_ms(), started)
        frame = (served, bool(elapsed // CURSOR_MS % 2))
        if frame != shown:
            draw(frame[1])
            screen.update(canvas, rotation=90)
            shown = frame

        time.sleep_ms(10)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
