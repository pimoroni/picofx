import time
from mighty_fx import MightyFX, SPCE
from screens import Screen280
from picovector import color, font, image, rect, shape

"""
Draw a roadworks sign, the kind towed to the side of a road: amber lamps behind a dark
face, holding a message, not scrolling it.

Two things make it this sign and not a video wall. Every character has its own small
matrix module with a bezel all round it, so the lamps exist in a grid of cells and the
face is plain between them. And a character sits on a fixed pitch whatever its width. The
corner beacons are neither: they are single large lamps on the face itself, so they are
drawn over the top rather than through any matrix.

Press "Boot" to exit the program.
"""

# Constants for drawing
LAMP = 4                        # Panel pixels across one lamp
APERTURE = 0.6                  # The lit hole, as a fraction of a lamp's width
SOFTEN = 0.8                    # Panel pixels the aperture's edge fades over
SIGN_FONT = "sins"              # A narrow face: its own pixels are lamps, so its width sets the message
BEZEL = 1                       # Lamps of plain face between one character's module and the next
LINE_BEZEL = 3                  # And between one row of modules and the next, which a sign leaves wider
LIT = color.rgb(255, 170, 0)    # A lit lamp. Amber is the only colour these signs use

# These three make the sign read as an object rather than text on nothing: a module's face against the
# sign's, and a lamp that is not lit against the module behind it
MODULE = color.rgb(17, 17, 17)  # A module's face, between its lamps
FACE = color.black              # And the sign's own face, which the modules are set into
# An unlit lamp. It has to be brighter than the band behind it, not a different hue. At 12 bits
# rgb(34, 17, 0) and rgb(17, 17, 17) come to the same total, and at this size the eye reads brightness, not
# colour
UNLIT = color.rgb(68, 34, 0)

HOLD = 4.0                      # How long a page of the message stands, in seconds
BEACON_R = 12                   # A corner beacon's radius in panel pixels, it being a lamp of its own
BEACON_MS = 500                 # How long each side's pair stays on for
BEACON_OFF = color.rgb(51, 17, 0)   # A beacon between flashes, which stays visibly amber, not dark

# What the sign says, a page at a time and a line to a row of modules. Lines are centred by whole
# modules, a module being the smallest thing the sign can move text by
PAGES = (
    ("ROADWORKS", "AHEAD", "EXPECT", "DELAYS"),
    ("LANE", "CLOSURE", "AHEAD", "MERGE LEFT"),
    ("QUEUE AHEAD", "SLOW DOWN", "20 MPH", "MAX"),
)

# Create a MightyFX object with SP/CE A set up for a screen
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# A sign is wider than it is tall, so the canvas is drawn landscape and every update turns it a quarter
# onto the panel. From the screen, not image(), which puts it in SRAM and halves both the mask
# read and the frame written
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height

# The lamp grid the bands are drawn on, one pixel to a lamp
COLUMNS = WIDTH // LAMP
ROWS = HEIGHT // LAMP

sign_font = getattr(font, SIGN_FONT)
sizer = image(COLUMNS, ROWS)
sizer.font = sign_font
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def ink_extent(letters):
    """Which rows and columns these letters' ink covers, drawn from a common origin.

    Read off a drawing, because neither number the font reports is the character's own size: its height
    carries ascender and descender space no capital reaches, and its advance carries the spacing to the next
    character. A module sized to either is bigger than the character needs, and the slack multiplies by
    every module on the sign.
    """
    span = sign_font.height * 2
    probe = image(span, span)
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = sign_font
    for letter in letters:
        probe.text(letter, 0, 0, 1)

    raw, stride = probe.raw, probe.stride
    rows = [y for y in range(span) if any(raw[y * stride + x * 4] > 60 for x in range(span))]
    columns = [x for x in range(span) if any(raw[y * stride + x * 4] > 60 for y in range(span))]
    return rows, columns


# A module is sized to the lettering it has to hold: the font's own pixels are lamps, so its ink decides
# how many characters fit across the sign and how many lines fit down it
INK_ROWS, INK_COLUMNS = ink_extent(ALPHABET)
CELL_W = INK_COLUMNS[-1] + 1
CELL_H = INK_ROWS[-1] - INK_ROWS[0] + 1
INK_TOP = INK_ROWS[0]

# What the font puts to the right of a character, so a narrow one can be centred in its module from its
# advance without measuring each one again
BEARING = max(int(sizer.measure_text(letter, font_size=1)[0]) for letter in ALPHABET) - CELL_W

# The beacons sit on the face above and below the bands, so their diameter is kept clear at each end
MARGIN = (BEACON_R * 2 + LAMP - 1) // LAMP
PITCH_W = CELL_W + BEZEL
PITCH_H = CELL_H + LINE_BEZEL
LINES = (ROWS - MARGIN * 2 + LINE_BEZEL) // PITCH_H
ACROSS = (COLUMNS + BEZEL) // PITCH_W

# The block of modules centred in what is left, so the sign sits square on its own face
LEFT = (COLUMNS - (ACROSS * PITCH_W - BEZEL)) // 2
TOP = (ROWS - (LINES * PITCH_H - LINE_BEZEL)) // 2

lamps = image(COLUMNS, ROWS)
lamps.font = sign_font

print(f"Roadworks sign of {ACROSS}x{LINES} modules, {CELL_W}x{CELL_H} lamps each at {LAMP}px,"
      f" so {ACROSS} characters over {LINES} lines."
      f" {SIGN_FONT} declares {sign_font.height} rows and inks {CELL_H} of them")
for page, lines in enumerate(PAGES):
    over = [line for line in lines if len(line) > ACROSS]
    if over or len(lines) > LINES:
        print(f"  page {page + 1} does not fit: {over or ''}{len(lines)} lines of {LINES}")


def bake_module():
    """One module's mask: an aperture over each of its lamps, and opaque over the rest of its pitch.

    A pixel at a time, which covers the aperture, the module's face between lamps and the bezel beyond
    them in one rule, and lets the module and the sign be different shades. Opaque is what the tile
    carries and clear is what it leaves: a hole cannot be punched by drawing, since drawing composites, so
    the mask is built around its holes.
    """
    tile = image(PITCH_W * LAMP, PITCH_H * LAMP)
    tile.pen = color.transparent
    tile.clear()

    middle = (LAMP - 1) / 2
    radius = LAMP * APERTURE / 2
    for y in range(tile.height):
        for x in range(tile.width):
            if x // LAMP >= CELL_W or y // LAMP >= CELL_H:
                over, shade = SOFTEN, FACE              # On the bezel, where there is no lamp at all
            else:
                away = (((x % LAMP) - middle) ** 2 + ((y % LAMP) - middle) ** 2) ** 0.5
                over, shade = away - radius, MODULE

            if over > 0:
                tile.pen = shade.with_alpha(min(255, round(over / SOFTEN * 255)))
                tile.rectangle(rect(x, y, 1, 1))

    return tile


def bake_mask():
    """The sign's face: clear to begin with, the modules laid into it, then its margins filled.

    Baked once. A module per cell every frame is hundreds of blits; a row of them costs one blit a module,
    and the face then costs one a row.

    It has to be built this way round. Drawing composites, so a transparent pen cannot take an opaque ground
    back to clear: filling the face first and clearing under the modules leaves every aperture shut. A
    module tile covers its whole pitch, bezel included, so tiling reaches everything but the margins around
    the block, and those are filled opaque afterwards.
    """
    face = image(WIDTH, HEIGHT)
    face.pen = color.transparent
    face.clear()

    module = bake_module()
    strip = image(WIDTH, module.height)
    strip.pen = color.transparent
    strip.clear()
    for column in range(ACROSS):
        strip.blit(module, (LEFT + column * PITCH_W) * LAMP, 0)

    for line in range(LINES):
        face.blit(strip, 0, (TOP + line * PITCH_H) * LAMP)

    # The margins the modules never reach, opaque so no lamp shows through them
    top = TOP * LAMP
    bottom = (TOP + LINES * PITCH_H) * LAMP
    right = (LEFT + ACROSS * PITCH_W) * LAMP
    face.pen = FACE
    face.rectangle(rect(0, 0, WIDTH, top))
    face.rectangle(rect(0, bottom, WIDTH, HEIGHT - bottom))
    face.rectangle(rect(0, top, LEFT * LAMP, bottom - top))
    face.rectangle(rect(right, top, WIDTH - right, bottom - top))

    return face


mask = bake_mask()

# Every rect the frame needs, built once: a rect is an object, and making them per frame allocates enough
# to bring a collection round mid-animation
SCALE_FROM = rect(0, 0, COLUMNS, ROWS)
SCALE_TO = rect(0, 0, COLUMNS * LAMP, ROWS * LAMP)

# The four beacons, a pair to a side so they alternate left against right. In panel pixels, not lamps,
# these being lamps of their own, not part of any matrix
BEACON_AT = ((BEACON_R, BEACON_R), (BEACON_R, HEIGHT - BEACON_R),
             (WIDTH - BEACON_R, BEACON_R), (WIDTH - BEACON_R, HEIGHT - BEACON_R))


def draw_lamps(page):
    """The message on the lamp grid, a character to a module.

    Drawn a character at a time rather than as a string, which fixes the pitch. A module holds one
    character whatever its width, so a narrow letter sits in a wider gap exactly as it does on the road.
    """
    lamps.pen = UNLIT
    lamps.clear()
    lamps.pen = LIT

    lines = PAGES[page][:LINES]
    first = TOP + (LINES - len(lines)) // 2 * PITCH_H
    for line, text in enumerate(lines):
        text = text[:ACROSS]
        start = LEFT + (ACROSS - len(text)) // 2 * PITCH_W
        y = first + line * PITCH_H
        for column, letter in enumerate(text):
            # Centred in its module, the font being proportional where the pitch is not, and lifted so the
            # ink lands at the module's top, not the empty rows above it
            wide = int(lamps.measure_text(letter, font_size=1)[0]) - BEARING
            lamps.text(letter, start + column * PITCH_W + (CELL_W - wide) // 2, y - INK_TOP, 1)


def draw(page, on_the_left):
    """One frame of the sign: the message lit up behind its face, and the beacons on the face itself."""
    draw_lamps(page)
    canvas.blit(lamps, SCALE_FROM, SCALE_TO, image.NEAREST)
    canvas.blit(mask, 0, 0)

    # Over the mask, not through it: a beacon is a lamp bolted to the face, so nothing masks it. The first
    # two of BEACON_AT are the left pair, so the index says which side one is on
    for index, (x, y) in enumerate(BEACON_AT):
        canvas.pen = LIT if (index < 2) == on_the_left else BEACON_OFF
        canvas.shape(shape.circle(x, y, BEACON_R))


started = time.ticks_ms()
shown = None

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = time.ticks_diff(time.ticks_ms(), started)
        frame = (int(elapsed / (HOLD * 1000)) % len(PAGES), bool(elapsed // BEACON_MS % 2))

        # Nothing on the sign moves, so it is only drawn again when the page or the beacons change
        if frame != shown:
            draw(*frame)
            screen.update(canvas, rotation=90)
            shown = frame

        time.sleep_ms(20)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
