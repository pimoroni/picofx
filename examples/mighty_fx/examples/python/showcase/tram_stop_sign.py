from mighty_fx import MightyFX, SPCE
from timing import Pacer, Roller
from screens import Reserve, Screen280, ScreenPair
from picovector import color, font, image, rect

"""
Draw a tram stop sign across two screens, amber lamps behind a dark face in a contiguous
band per line, with the next tram pinned and the ones after it cycling underneath.

The rows scroll vertically, so two service rows list five trams while always showing the
next. The notice is longer than the sign, so it scrolls horizontally.

Each band is drawn into its own pane, which clips a sliding row and lets one band redraw alone.

Press "Boot" to exit the program.

Section: Transport signs
"""

# Constants for drawing
LAMP = 4                        # Panel pixels across one lamp
APERTURE = 0.6                  # The lit hole, as a fraction of a lamp's width
SOFTEN = 0.8                    # Panel pixels the aperture's edge fades over
SIGN_FONT = font.sins           # A narrow face whose pixels are lamps, so its width sets the message
CLOCK_SCALE = 2                 # Pixel fonts scale by whole numbers, and the clock is the biggest thing
BAND_GAP = 3                    # Lamps of plain face between one band and the next
MARGIN = 2                      # Lamps of face down either side of a band

LIT = color.rgb(255, 170, 0)    # A lit lamp. Amber is the only colour these signs use
BAND = color.rgb(17, 17, 17)    # The recessed strip a band's lamps sit in
FACE = color.black              # And the sign's own face, above, below and between the bands
UNLIT = color.rgb(68, 34, 0)    # An unlit lamp is brighter than the band behind it,
                                # as at this size the eye reads brightness

TURNED = 0                      # One panel of a pair is mounted turned round, so their narrowest bezels meet.
                                # 0 for SP/CE A, 1 for B, or None

CLOCK_START = (11, 30, 40)      # The time the sign counts on from, Mighty FX having no clock to read
DWELL = 4.0                     # How long a cycling row stands before the next tram slides up, in seconds

# Lamps a scroll moves a frame, since whole lamps are the only even step.
# The notice takes two and a sliding row one
NOTICE_LAMPS = 2
SLIDE_LAMPS = 1

# The trams due, soonest first. The first is pinned to the top row and the rest cycle underneath, which is
# how a sign with two rows lists five trams without ever hiding the next one
TRAMS = (
    ("2", "BLUE", "Halfway", "11:34"),
    ("1", "YELL", "Middlewood", "11:37"),
    ("2", "TT", "Parkgate", "11:41"),
    ("1", "BLUE", "Malin Bridge", "11:45"),
    ("2", "PURP", "Herdings Park", "11:52"),
)
NOTICE = ("Please let passengers off before boarding."
          " Tickets can be bought from the conductor on board.")

# Create a MightyFX object with both SP/CE ports set up for screens, and a 2.8" screen on each
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# A pair writes both panels together, so the notice is in step across them. Working out how takes a few
# seconds, and the reserve lets it convert from the heap
pair = ScreenPair(Screen280(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES),
                  Screen280(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES))

# Each panel is turned a quarter, so the canvas's x runs along the sign and its y down it. The panels sit
# side by side, the second showing the canvas from where the first left off
TURNS = tuple(90 + 180 * (port == TURNED) for port in range(2))
PANEL_W = pair.screens[0].height
HEIGHT = pair.screens[0].width

# The bezels where the panels meet hide a gap, set by eye.
# The canvas carries it so content crosses the seam as on one sign
SEAM = 16
WIDTH = PANEL_W * 2 + SEAM
canvas = image(WIDTH, HEIGHT)

# The lamp grid the bands are laid out on, one pixel to a lamp
COLUMNS = WIDTH // LAMP
ROWS = HEIGHT // LAMP
BAND_W = COLUMNS - MARGIN * 2

sizer = image(COLUMNS, 1)
sizer.font = SIGN_FONT
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:."


def lettering_extent(letters, scale):
    """Measure which rows these letters fill. A face's metrics are not where they land."""
    span = SIGN_FONT.height * scale * 2
    probe = image(span, span)
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = SIGN_FONT
    for letter in letters:
        probe.text(letter, 0, 0, scale)

    raw, stride = probe.raw, probe.stride
    rows = [y for y in range(span) if any(raw[y * stride + x * 4] > 60 for x in range(span))]
    return rows[0], rows[-1] - rows[0] + 1


TEXT_TOP, TEXT_H = lettering_extent(ALPHABET, 1)
CLOCK_TOP, CLOCK_H = lettering_extent("0123456789:", CLOCK_SCALE)

# Four bands, the pinned tram, the cycling one, the notice and the clock. Their heights come from the
# lettering each carries, and what is left over becomes an even margin above and below
PINNED, CYCLING, NOTICE_BAND, CLOCK = 0, 1, 2, 3
BAND_H = (TEXT_H, TEXT_H, TEXT_H, CLOCK_H)
TOP = (ROWS - sum(BAND_H) - BAND_GAP * (len(BAND_H) - 1)) // 2
BAND_Y = []
at = TOP
for height in BAND_H:
    BAND_Y.append(at)
    at += height + BAND_GAP

BOTTOM = BAND_Y[-1] + BAND_H[-1]

# A pane per band, whose edges clip whatever slides past them
panes = [image(BAND_W, height) for height in BAND_H]
for pane in panes:
    pane.font = SIGN_FONT

# Where each pane goes and the mask over it, built once so a frame allocates nothing
PANE_FROM = [rect(0, 0, BAND_W, height) for height in BAND_H]
PANE_TO = [rect(MARGIN * LAMP, y * LAMP, BAND_W * LAMP, height * LAMP)
           for y, height in zip(BAND_Y, BAND_H)]

print(f"Tram sign turned {TURNS}, {COLUMNS}x{ROWS} lamps at {LAMP}px, bands of {BAND_H} at {BAND_Y}")

# Warn of any tram or clock wider than its band, as the pane would cut it short
for stand, line, towards, when in TRAMS:
    needs = int(sizer.measure_text(f"{stand}. {line} {towards} {when}", font_size=1)[0])
    if needs > BAND_W:
        print(f"  {towards} needs {needs} lamps of {BAND_W}: shorten its destination")

CLOCK_W = int(sizer.measure_text("00:00:00", font_size=CLOCK_SCALE)[0])
if CLOCK_W > BAND_W:
    print(f"  the clock needs {CLOCK_W} lamps of {BAND_W} at scale {CLOCK_SCALE}")


def bake_band(height):
    """Bake one band's mask, an aperture over every lamp and the band's face between, a pixel at a time."""
    tile = image(BAND_W * LAMP, height * LAMP)
    tile.pen = color.transparent
    tile.clear()

    middle = (LAMP - 1) / 2
    radius = LAMP * APERTURE / 2
    for y in range(tile.height):
        for x in range(tile.width):
            away = (((x % LAMP) - middle) ** 2 + ((y % LAMP) - middle) ** 2) ** 0.5
            over = away - radius
            if over > 0:
                tile.pen = BAND.with_alpha(min(255, round(over / SOFTEN * 255)))
                tile.rectangle(rect(x, y, 1, 1))

    return tile


def bake_mask():
    """
    Bake the sign's face, clear to begin with, a band laid in per line, then the rest filled.

    It starts clear, as a transparent pen cannot clear an opaque background back.
    """
    face = image(WIDTH, HEIGHT)
    face.pen = color.transparent
    face.clear()

    for height, y in zip(BAND_H, BAND_Y):
        face.blit(bake_band(height), MARGIN * LAMP, y * LAMP)

    # Everything no band reaches, opaque so nothing shows through it
    face.pen = FACE
    face.rectangle(rect(0, 0, WIDTH, TOP * LAMP))
    face.rectangle(rect(0, BOTTOM * LAMP, WIDTH, HEIGHT - BOTTOM * LAMP))
    face.rectangle(rect(0, TOP * LAMP, MARGIN * LAMP, (BOTTOM - TOP) * LAMP))
    face.rectangle(rect((MARGIN + BAND_W) * LAMP, TOP * LAMP,
                        WIDTH - (MARGIN + BAND_W) * LAMP, (BOTTOM - TOP) * LAMP))
    for index in range(len(BAND_H) - 1):
        gap = BAND_Y[index] + BAND_H[index]
        face.rectangle(rect(0, gap * LAMP, WIDTH, BAND_GAP * LAMP))

    return face


mask = bake_mask()
NOTICE_W = int(sizer.measure_text(NOTICE, font_size=1)[0])
CYCLES = len(TRAMS) - 1         # The trams that take turns on the cycling row


def show(index):
    """Draw one band onto the canvas, its lamps scaled up and the mask over them, touching only its rows."""
    canvas.blit(panes[index], PANE_FROM[index], PANE_TO[index], image.NEAREST)
    canvas.blit(mask, PANE_TO[index], PANE_TO[index], image.NEAREST)


def clear(pane):
    """Put a pane back to unlit lamps, ready to be drawn on again."""
    pane.pen = UNLIT
    pane.clear()
    pane.pen = LIT


def draw_tram(pane, y, tram):
    """Draw one tram on a pane, its stand, line and destination to the left and its time to the right."""
    stand, line, towards, when = tram
    pane.text(f"{stand}. {line} {towards}", 0, y - TEXT_TOP, 1)
    wide = int(sizer.measure_text(when, font_size=1)[0])
    pane.text(when, BAND_W - wide, y - TEXT_TOP, 1)


def draw_pinned():
    """Draw the next tram, which never cycles and so is never the one that has scrolled away."""
    clear(panes[PINNED])
    draw_tram(panes[PINNED], 0, TRAMS[0])
    show(PINNED)


def draw_cycling(step, lift):
    """
    Draw the trams after the next in turn.

    During a slide one leaves and one arrives, the pane's edges clipping both.
    """
    pane = panes[CYCLING]
    clear(pane)
    if lift is None:
        draw_tram(pane, 0, TRAMS[1 + step % CYCLES])
    else:
        draw_tram(pane, -lift, TRAMS[1 + (step - 1) % CYCLES])
        draw_tram(pane, BAND_H[CYCLING] - lift, TRAMS[1 + step % CYCLES])

    show(CYCLING)


def draw_notice(travelled):
    """Draw the notice, in from the right and out to the left, its width and the sign's being one pass."""
    pane = panes[NOTICE_BAND]
    clear(pane)
    pane.text(NOTICE, BAND_W - travelled % (NOTICE_W + BAND_W), -TEXT_TOP, 1)
    show(NOTICE_BAND)


def draw_clock(seconds):
    """Draw the time centred, the biggest lettering on the sign. Counted on from CLOCK_START."""
    hours, minutes, start = CLOCK_START
    total = (hours * 3600 + minutes * 60 + start + seconds) % 86400
    reading = f"{total // 3600:02d}:{total // 60 % 60:02d}:{total % 60:02d}"

    pane = panes[CLOCK]
    clear(pane)
    wide = int(sizer.measure_text(reading, font_size=CLOCK_SCALE)[0])
    pane.text(reading, (BAND_W - wide) // 2, -CLOCK_TOP, CLOCK_SCALE)
    show(CLOCK)


def send():
    """Send the canvas to both panels, on the same frame."""
    # The second panel shows the canvas from where the first left off, whichever way it is turned
    pair.update(canvas, rotation=TURNS, offset=((0, 0), (-(PANEL_W + SEAM), 0)))


# The face first, so the margins and gaps carry the sign's colour
canvas.pen = FACE
canvas.clear()
draw_pinned()

pacer = Pacer()                 # The sign's clock, with no rate, as every scroll is counted in frames
travelled = 0
step = 0                        # How many times the cycling row has moved on
lift = None                     # How far its row has climbed, or None while it stands
standing = Roller(DWELL)
shown = (None, None, None)
draw_cycling(step, lift)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = pacer.elapsed / 1000
        second = int(elapsed)

        # A row stands for its dwell, then climbs out a lamp at a time and the next follows it up
        if lift is None:
            if standing.is_due():
                step += 1
                lift = 0
        else:
            lift += SLIDE_LAMPS
            if lift >= BAND_H[CYCLING]:
                lift = None
                standing.restart()

        # Only what changed is redrawn, the notice every frame
        if (step, lift) != shown[:2]:
            draw_cycling(step, lift)

        if second != shown[2]:
            draw_clock(second)

        shown = (step, lift, second)
        draw_notice(travelled)
        send()
        travelled += NOTICE_LAMPS

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
