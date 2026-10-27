from mighty_fx import MightyFX, SPCE
from timing import Pacer
from screens import Screen280
from picovector import color, font, image, rect, shape

"""
Draw a roadworks sign, the kind towed to the side of a road, its amber lamps behind a dark
face holding a message, not scrolling it.

Each character has its own matrix module with a bezel all round, on a fixed pitch whatever
its width. The corner beacons are single large lamps drawn over the face.

Press "Boot" to exit the program.

Section: Transport signs
"""

# Constants for drawing
LAMP = 4                            # Panel pixels across one lamp
APERTURE = 0.6                      # The lit hole, as a fraction of a lamp's width
SOFTEN = 0.8                        # Panel pixels the aperture's edge fades over
SIGN_FONT = font.sins               # A narrow face whose pixels are lamps, so its width sets the message
BEZEL = 1                           # Lamps of plain face between one character's module and the next
LINE_BEZEL = 3                      # And between one row of modules and the next, which a sign leaves wider
LIT = color.rgb(255, 170, 0)        # A lit lamp. Amber is the only colour these signs use

# A module's face against the sign's, and an unlit lamp against its module
MODULE = color.rgb(17, 17, 17)      # A module's face, between its lamps
FACE = color.black                  # And the sign's own face, which the modules are set into
UNLIT = color.rgb(68, 34, 0)        # An unlit lamp is brighter than the module behind it,
                                    # as at this size the eye reads brightness

HOLD = 8.0                          # How long a page of the message stands, in seconds
BEACON_R = 12                       # A corner beacon's radius in panel pixels, it being a lamp of its own
BEACON_MS = 500                     # How long each side's pair stays on for
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

# Drawn landscape and turned a quarter onto the panel at each update
canvas = screen.canvas(screen.height, screen.width)
WIDTH, HEIGHT = canvas.width, canvas.height

# The lamp grid the bands are drawn on, one pixel to a lamp
COLUMNS = WIDTH // LAMP
ROWS = HEIGHT // LAMP

lamps = image(COLUMNS, ROWS)
lamps.font = SIGN_FONT
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def lettering_extent(letters):
    """Measure which rows and columns these letters fill. A face's metrics are not where they land."""
    span = SIGN_FONT.height * 2
    probe = image(span, span)
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = SIGN_FONT
    for letter in letters:
        probe.text(letter, 0, 0, 1)

    raw, stride = probe.raw, probe.stride
    rows = [y for y in range(span) if any(raw[y * stride + x * 4] > 60 for x in range(span))]
    columns = [x for x in range(span) if any(raw[y * stride + x * 4] > 60 for y in range(span))]
    return rows, columns


# A module is sized to the drawn lettering, as the font's pixels are lamps
LETTERING_ROWS, LETTERING_COLUMNS = lettering_extent(ALPHABET)
CELL_W = LETTERING_COLUMNS[-1] + 1
CELL_H = LETTERING_ROWS[-1] - LETTERING_ROWS[0] + 1
LETTERING_TOP = LETTERING_ROWS[0]

# What the face leaves right of a character, so a narrow one centres in its module from its advance
BEARING = max(int(lamps.measure_text(letter, font_size=1)[0]) for letter in ALPHABET) - CELL_W

# The beacons sit on the face above and below the bands, so their diameter is kept clear at each end
MARGIN = (BEACON_R * 2 + LAMP - 1) // LAMP
PITCH_W = CELL_W + BEZEL
PITCH_H = CELL_H + LINE_BEZEL
LINES = (ROWS - MARGIN * 2 + LINE_BEZEL) // PITCH_H
ACROSS = (COLUMNS + BEZEL) // PITCH_W

# The block of modules centred in what is left, so the sign sits square on its own face
LEFT = (COLUMNS - (ACROSS * PITCH_W - BEZEL)) // 2
TOP = (ROWS - (LINES * PITCH_H - LINE_BEZEL)) // 2

print(f"Roadworks sign of {ACROSS}x{LINES} modules, {CELL_W}x{CELL_H} lamps each at {LAMP}px,"
      f" so {ACROSS} characters over {LINES} lines."
      f" Its face declares {SIGN_FONT.height} rows and fills {CELL_H} of them")
for page, lines in enumerate(PAGES):
    # Warn of any page with more lines than the sign holds, or a line longer than it
    over = [line for line in lines if len(line) > ACROSS]
    if over or len(lines) > LINES:
        print(f"  page {page + 1} does not fit: {over or ''}{len(lines)} lines of {LINES}")


def bake_module():
    """Bake one module's mask, apertures over its lamps and the rest of its pitch opaque, a pixel at a time."""
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
    """
    Bake the sign's face, clear to begin with, the modules laid a row at a time, then its margins filled.

    It starts clear, as a transparent pen cannot clear an opaque background back.
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

# Every rect the frame needs, built once so a frame allocates nothing
SCALE_FROM = rect(0, 0, COLUMNS, ROWS)
SCALE_TO = rect(0, 0, COLUMNS * LAMP, ROWS * LAMP)

# The four beacons, a pair to a side, in panel pixels as lamps of their own
BEACONS = [shape.circle(x, y, BEACON_R)
           for x, y in ((BEACON_R, BEACON_R), (BEACON_R, HEIGHT - BEACON_R),
                        (WIDTH - BEACON_R, BEACON_R), (WIDTH - BEACON_R, HEIGHT - BEACON_R))]


def draw_lamps(page):
    """Draw the message a character to a module, so a narrow letter sits in a wider gap as on the road."""
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
            # lettering lands at the module's top, not the empty rows above it
            wide = int(lamps.measure_text(letter, font_size=1)[0]) - BEARING
            lamps.text(letter, start + column * PITCH_W + (CELL_W - wide) // 2, y - LETTERING_TOP, 1)


def draw(page, on_the_left):
    """Draw one frame of the sign, the message lit up behind its face, and the beacons on the face itself."""
    draw_lamps(page)
    canvas.blit(lamps, SCALE_FROM, SCALE_TO, image.NEAREST)
    canvas.blit(mask, 0, 0)

    # Beacons go over the mask, bolted to the face. The first two are the left pair
    for index, beacon in enumerate(BEACONS):
        canvas.pen = LIT if (index < 2) == on_the_left else BEACON_OFF
        canvas.shape(beacon)


pacer = Pacer(0.02)                 # The sign's clock, looking for a change every 20ms
shown = None

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The page showing and which pair of beacons is lit, all a frame depends on
        elapsed = pacer.elapsed
        frame = (int(elapsed / (HOLD * 1000)) % len(PAGES), bool(elapsed // BEACON_MS % 2))

        # Nothing on the sign moves, so it is only drawn again when the page or the beacons change
        if frame != shown:
            draw(*frame)
            screen.update(canvas, rotation=90)
            shown = frame

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
