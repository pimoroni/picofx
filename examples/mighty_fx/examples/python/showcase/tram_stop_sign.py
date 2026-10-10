import time
from mighty_fx import MightyFX, SPCE
from screens import Reserve, Screen280, ScreenPair
from picovector import color, font, image, rect

"""
Draw a tram stop sign across two screens: amber lamps behind a dark face, in a contiguous
band per line, with the next tram pinned and the ones after it cycling underneath.

Two things here are in no other example. The rows scroll vertically, so a sign with two
service rows can list five trams while always showing the next one. And the notice scrolls
horizontally, because it is longer than the sign, which is the sign's own answer to being
narrower than what it has to say.

Each band is drawn into a pane of its own, so a band really is a window: anything reaching
past its edges is outside the image and simply not there. That is what lets a row slide
without being clipped by hand, and it is what lets one band be redrawn without the others,
which is what makes the scroll affordable.

Press "Boot" to exit the program.

Section: Transport signs
"""

# Constants for drawing
LAMP = 4                        # Panel pixels across one lamp
APERTURE = 0.6                  # The lit hole, as a fraction of a lamp's width
SOFTEN = 0.8                    # Panel pixels the aperture's edge fades over
SIGN_FONT = "sins"              # A narrow face: its own pixels are lamps, so its width sets the message
CLOCK_SCALE = 2                 # Pixel fonts scale by whole numbers, and the clock is the biggest thing
BAND_GAP = 3                    # Lamps of plain face between one band and the next
MARGIN = 2                      # Lamps of face down either side of a band

LIT = color.rgb(255, 170, 0)    # A lit lamp. Amber is the only colour these signs use
BAND = color.rgb(17, 17, 17)    # The recessed strip a band's lamps sit in
FACE = color.black              # And the sign's own face, above, below and between the bands
# An unlit lamp. It has to be brighter than the band behind it, not merely a different hue: at 12 bits
# rgb(34, 17, 0) and rgb(17, 17, 17) both come to the same total, so the lamps were there and
# invisible, the eye reading brightness rather than colour at this size
UNLIT = color.rgb(68, 34, 0)

# A panel's bezel is not the same on every edge, so a pair reads as one sign with its two narrowest edges
# together, which means mounting one of them turned round. This is which: 0 for the panel on SP/CE A, 1 for
# the one on B, or None where both are the same way up. The frame turns with the panel
TURNED = 0

CLOCK_START = (11, 30, 40)      # The time the sign counts on from, MightyFX having no clock to read
DWELL = 4.0                     # How long a cycling row stands before the next tram slides up, in seconds
# How far each scroll travels a frame. A whole lamp is the only even step a matrix can make, so both are
# counted in frames rather than timed: timed, they move by whatever the frame rate leaves them and land
# unevenly. The notice can take two, being read across the sign; a row sliding through its band wants
# one, the slide itself being the thing on show
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

# The two panels are one sign, so both have to carry the same frame of a scroll. A pair holds them to one
# refresh rate and writes them together, where two screens written one after the other would leave the
# notice a step further along on one than the other. Working out how takes a few seconds. The reserve is
# what a pair needs to convert an image out of the heap, which is where a sign wider than a panel has to live
pair = ScreenPair(Screen280(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES),
                  Screen280(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES))

# Each panel is turned a quarter, so the canvas's x runs along the sign and its y down it. The panels sit
# side by side, the second showing the canvas from where the first left off
TURNS = tuple(90 + 180 * (port == TURNED) for port in range(2))
PANEL_W = pair.screens[0].height
HEIGHT = pair.screens[0].width

# Where the panels meet, their two bezels hold the active areas apart. The canvas carries that gap so
# that neither panel shows it: content crossing the seam then lands where it would on one long sign
# rather than being pulled apart by the bezels. Tune it by eye, the notice crossing the join being the
# pattern that shows it: 16 came off the glass, from evenly spaced dots drawn a row per candidate
SEAM = 16
WIDTH = PANEL_W * 2 + SEAM
canvas = image(WIDTH, HEIGHT)

# The lamp grid the bands are laid out on, one pixel to a lamp
COLUMNS = WIDTH // LAMP
ROWS = HEIGHT // LAMP
BAND_W = COLUMNS - MARGIN * 2

sign_font = getattr(font, SIGN_FONT)
sizer = image(COLUMNS, 1)
sizer.font = sign_font
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:."


def ink_extent(letters, scale):
    """Which rows these letters' ink covers, drawn from a common origin.

    Read off a drawing, because the height a pixel font reports is its declared box: it carries ascender
    and descender space no character reaches, and a band sized to it is taller than the lettering needs.
    """
    span = sign_font.height * scale * 2
    probe = image(span, span)
    probe.pen = color.black
    probe.clear()
    probe.pen = color.white
    probe.font = sign_font
    for letter in letters:
        probe.text(letter, 0, 0, scale)

    raw, stride = probe.raw, probe.stride
    rows = [y for y in range(span) if any(raw[y * stride + x * 4] > 60 for x in range(span))]
    return rows[0], rows[-1] - rows[0] + 1


TEXT_TOP, TEXT_H = ink_extent(ALPHABET, 1)
CLOCK_TOP, CLOCK_H = ink_extent("0123456789:", CLOCK_SCALE)

# Four bands: the pinned tram, the cycling one, the notice and the clock. Their heights come from the
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

# A pane per band, which is where its own lamps are drawn. Its edges are the window: a row sliding through
# it reaches past them and is simply not in the image, so nothing has to be clipped and no band can draw
# into its neighbour
panes = [image(BAND_W, height) for height in BAND_H]
for pane in panes:
    pane.font = sign_font

# Where each pane goes on the canvas, and where the mask has to be laid over it again. Built once: a rect is
# an object, and making them per frame allocates enough to bring a collection round mid-scroll
PANE_FROM = [rect(0, 0, BAND_W, height) for height in BAND_H]
PANE_TO = [rect(MARGIN * LAMP, y * LAMP, BAND_W * LAMP, height * LAMP)
           for y, height in zip(BAND_Y, BAND_H)]

print(f"Tram sign turned {TURNS}, {COLUMNS}x{ROWS} lamps at {LAMP}px, bands of {BAND_H} at {BAND_Y}")

for stand, line, towards, when in TRAMS:
    needs = int(sizer.measure_text(f"{stand}. {line} {towards} {when}", font_size=1)[0])
    if needs > BAND_W:
        print(f"  {towards} needs {needs} lamps of {BAND_W}: shorten its destination")

CLOCK_W = int(sizer.measure_text("00:00:00", font_size=CLOCK_SCALE)[0])
if CLOCK_W > BAND_W:
    print(f"  the clock needs {CLOCK_W} lamps of {BAND_W} at scale {CLOCK_SCALE}")


def bake_band(height):
    """One band's mask: an aperture over every lamp across it, and the band's face between them.

    A pixel at a time, which covers the aperture and the face around it in one rule. Opaque is what the
    tile carries and clear is what it leaves.
    """
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
    """The sign's face: clear to begin with, a band laid in per line, then everything else filled.

    It has to be this way round. Drawing composites, so a transparent pen cannot take an opaque ground back
    to clear: filling the face first and clearing under the bands leaves every aperture shut. The bands
    carry every opaque pixel they cover, and the face around them is filled afterwards.
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
CYCLES = len(TRAMS) - 1


def show(index):
    """One band onto the canvas: its lamps scaled up, then the mask laid over them again.

    Only the band's own rows, which is the point of the panes. Both blits cost about 730ns a pixel on a
    canvas this size, the heap being some 2.4 times slower than the fast SRAM a smaller canvas would fit in,
    so covering the whole panel every frame costs 193ms where the notice's own band costs 27ms.
    """
    canvas.blit(panes[index], PANE_FROM[index], PANE_TO[index], image.NEAREST)
    canvas.blit(mask, PANE_TO[index], PANE_TO[index], image.NEAREST)


def clear(pane):
    """A pane back to unlit lamps, ready to be drawn on again."""
    pane.pen = UNLIT
    pane.clear()
    pane.pen = LIT


def draw_tram(pane, y, tram):
    """One tram on a pane: its stand and line to the left, its destination after them, time to the right."""
    stand, line, towards, when = tram
    pane.text(f"{stand}. {line} {towards}", 0, y - TEXT_TOP, 1)
    wide = int(sizer.measure_text(tram[3], font_size=1)[0])
    pane.text(when, BAND_W - wide, y - TEXT_TOP, 1)


def draw_pinned():
    """The next tram, which never cycles, so it is never the one that has scrolled away."""
    clear(panes[PINNED])
    draw_tram(panes[PINNED], 0, TRAMS[0])
    show(PINNED)


def draw_cycling(step, lift):
    """The trams after the next, in turn.

    During a slide both are drawn, one leaving upward and one arriving from below. The pane's own edges are
    what hide the parts of each that fall outside the band, so neither reaches the row above.
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
    """The notice, in from the right and out to the left, its own width plus the sign's being one pass."""
    pane = panes[NOTICE_BAND]
    clear(pane)
    pane.text(NOTICE, BAND_W - travelled % (NOTICE_W + BAND_W), -TEXT_TOP, 1)
    show(NOTICE_BAND)


def draw_clock(seconds):
    """The time, centred, and the biggest lettering on the sign. Counted on from CLOCK_START."""
    hours, minutes, start = CLOCK_START
    total = (hours * 3600 + minutes * 60 + start + seconds) % 86400
    reading = f"{total // 3600:02d}:{total // 60 % 60:02d}:{total % 60:02d}"

    pane = panes[CLOCK]
    clear(pane)
    wide = int(sizer.measure_text(reading, font_size=CLOCK_SCALE)[0])
    pane.text(reading, (BAND_W - wide) // 2, -CLOCK_TOP, CLOCK_SCALE)
    show(CLOCK)


def send():
    """The canvas to both panels, on the same frame."""
    # One canvas reaches both panels, the second showing it from where the first left off. A negative
    # offset places the source left of the panel and the converter clips to it, and it does so whichever
    # way the panel is turned: at 270 the source runs the other way across it, which is exactly what
    # turning it round asks for
    pair.update(canvas, rotation=TURNS, offset=((0, 0), (-(PANEL_W + SEAM), 0)))


# The face first, so the margins and the gaps between bands carry the sign's own colour: from here on the
# band blits only ever touch their own rows
canvas.pen = FACE
canvas.clear()
draw_pinned()

started = time.ticks_ms()
travelled = 0
step = 0
lift = None
stood_from = time.ticks_ms()
shown = (None, None, None)
draw_cycling(step, lift)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        elapsed = time.ticks_diff(time.ticks_ms(), started) / 1000
        second = int(elapsed)

        # A row stands for its dwell, then climbs out a lamp at a time and the next follows it up
        if lift is None:
            if time.ticks_diff(time.ticks_ms(), stood_from) >= int(DWELL * 1000):
                step += 1
                lift = 0
        else:
            lift += SLIDE_LAMPS
            if lift >= BAND_H[CYCLING]:
                lift = None
                stood_from = time.ticks_ms()

        # Only what changed is redrawn. The notice moves every frame; the cycling row moves during a slide,
        # and the clock when the second turns over
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
