# Probes the ST7789 TESCAN (0x44) tear-scanline command and related panel
# behaviour, deciding whether TE phase alignment between the two panels is
# possible. TESCAN moves the scanline TE asserts on, which would let a tracking
# loop delay the faster panel's edge to meet the slower one's.
#
# Experiments, per panel unless noted:
#   1a  TESCAN sweep under each TEON mode: does the falling edge move by N line
#       times, and how wide is the shifted pulse? poll_te() needs a settled
#       high before the fall, so the pulse must stay wider than the
#       interleaver's worst poll gap (about 700us).
#   1c  Beam-overtake sweep: v_sync off, each write started k line times after
#       the TE edge, eyes on where tearing begins against the predicted onset.
#       This is the data behind restoring the fast 12-bit profiles.
#   1d  FRCTRL2 alternated between adjacent codes every frame: eyes on the
#       glass for glitches, and the mean period against the two steady periods.
#       Decides whether rate dithering is available to the tracking loop.
#   1b  (both panels, last) 200 interleaved frames with a static TESCAN of 48
#       on the faster panel: te_timeouts must stay zero and frames wire-bound,
#       which is what proves the narrowed pulse survives the interleaver. 48
#       lines is past the tear margin, so that panel tears by design; the
#       tracking loop in check_te_align.py is what stays inside it.
#
# A diagnostic, not an example, so it is not copied to the board. Run it with
# mpremote against a board carrying the update_all firmware, with eyes on both
# panels for 1c, 1d and 1b.

import time

import spidisplay
import st7789
from machine import Pin
from mighty_fx import SPCE, MightyFX
from picovector import color, image
from screens import Screen280

LINE_SLOTS = 344            # scanned lines per refresh including porches
TEON_MODES = (None, b"\x00", b"\x01")
N_SWEEP = (0, 32, 64, 128, 192, 256, 320, 336)
K_SWEEP = (0, 16, 32, 48, 56, 64, 72, 96, 160, 240, 320)
FRAMES_PER_K = 40
DITHER_FRAMES = 100
INTERLEAVED_FRAMES = 200
STATIC_N = 48
GRID_PITCH = 20
BACKGROUNDS = (color.rgb(127, 127, 127), color.rgb(34, 177, 76))

mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
screens = (Screen280(mighty.spce_a), Screen280(mighty.spce_b))
dc_pins = (Pin(MightyFX.SPCE_A_DC_PIN), Pin(MightyFX.SPCE_B_DC_PIN))
labels = ("SP/CE A", "SP/CE B")
for dc in dc_pins:
    dc.init(pull=Pin.PULL_DOWN)     # persists through the C module's direction flips

WIDTH, HEIGHT = screens[0].width, screens[0].height
canvas = image(HEIGHT, WIDTH, spidisplay.buffer(HEIGHT * WIDTH * 4))
FR_CODES = st7789.FRAME_RATE_CONTROL


def draw(background):
    canvas.pen = background
    canvas.clear()
    canvas.pen = color.rgb(0, 0, 0)
    for x in range(0, canvas.width, GRID_PITCH):
        canvas.rectangle(x, 0, 1, canvas.height)
    for y in range(0, canvas.height, GRID_PITCH):
        canvas.rectangle(0, y, canvas.width, 1)


def tescan(screen, n):
    screen.__command(st7789.REG_TESCAN, bytes((n >> 8, n & 0xFF)))


def teon(screen, mode):
    if mode is None:
        screen.__command(st7789.REG_TEON)
    else:
        screen.__command(st7789.REG_TEON, mode)


def restore_te(screen):
    # TEON without its parameter leaves the mode bit as it was, so the restore
    # must send the V-blank mode byte explicitly.
    teon(screen, b"\x00")
    tescan(screen, 0)


def capture_falls(dc, count, timeout_ms=500):
    """Timestamps of falling edges on a TE line, observed from Python."""
    dc.init(Pin.IN, pull=Pin.PULL_DOWN)
    falls = []
    t0 = time.ticks_ms()
    level = dc.value()
    while len(falls) < count:
        if time.ticks_diff(time.ticks_ms(), t0) >= timeout_ms:
            break
        value = dc.value()
        if value != level:
            level = value
            if not value:
                falls.append(time.ticks_us())
    return falls


def offset_mod(falls, ref, period_us):
    """Median offset of the edges from ref, modulo the period."""
    offsets = sorted(time.ticks_diff(t, ref) % period_us for t in falls)
    return offsets[len(offsets) // 2]


def sweep_1a(label, screen, display, dc):
    print("1a {}: TESCAN sweep per TEON mode".format(label))
    for mode in TEON_MODES:
        mode_name = "none" if mode is None else "0x{:02x}".format(mode[0])
        teon(screen, mode)
        tescan(screen, 0)
        period_us, high_us, edges = display.te_probe(500)
        print("  TEON param {}: period {}us high {}us edges {}".format(
            mode_name, period_us, high_us, edges))
        if edges < 2 or period_us < 5000:
            print("    edge tracking skipped: no usable V-blank-style pulse")
            continue
        s_line = period_us / LINE_SLOTS

        # Baseline at N=0 absorbs the command latency between captures, so a
        # later N reports only the panel's own shift.
        pre = capture_falls(dc, 4)
        tescan(screen, 0)
        post = capture_falls(dc, 6)
        if len(pre) < 2 or len(post) < 2:
            print("    edge tracking skipped: too few edges captured")
            continue
        base = offset_mod(post, pre[-1], period_us)

        for n in N_SWEEP[1:]:
            pre = capture_falls(dc, 4)
            tescan(screen, n)
            post = capture_falls(dc, 6)
            shifted = display.te_probe(300)
            tescan(screen, 0)
            if len(pre) < 2 or len(post) < 2:
                print("    N {}: too few edges captured".format(n))
                continue
            shift = (offset_mod(post, pre[-1], period_us) - base) % period_us
            predicted = round(n * s_line) % period_us
            print("    N {}: shift {}us (predicted {}us, {:+.1f} lines off)"
                  " high {}us".format(n, shift, predicted,
                                      (shift - predicted) / s_line,
                                      shifted[1]))
    restore_te(screen)
    print()


def sweep_1c(label, screen, display, dc):
    restore_te(screen)
    screen.update(canvas, rotation=90, v_sync=False)    # warm, and measures the write
    frame_us = display.stats().frame_us
    probe = display.te_probe(500)
    period_us = probe[0]
    s_line = period_us / LINE_SLOTS
    onset = LINE_SLOTS + HEIGHT - 1 - frame_us / s_line
    print("1c {}: overtake sweep, write {}us, predicted onset k ~{:.0f}"
          " (plus Python start latency)".format(label, frame_us, onset))
    for k in K_SWEEP:
        delay_us = round(k * s_line)
        print("  k {} ({}us behind the edge): predicted {}".format(
            k, delay_us, "tear" if k > onset else "clean"))
        for frame in range(FRAMES_PER_K):
            draw(BACKGROUNDS[frame % 2])
            falls = capture_falls(dc, 1)
            if falls:
                t0 = falls[0]
                while time.ticks_diff(time.ticks_us(), t0) < delay_us:
                    pass
            screen.update(canvas, rotation=90, v_sync=False)
            if k == 0 and frame == 0 and falls:
                # ticks_us and the stats clock share the 1MHz timebase, so the
                # difference is valid modulo the ticks wrap.
                start = display.stats().write_start_us & 0x3FFFFFFF
                latency = time.ticks_diff(start, t0 & 0x3FFFFFFF)
                print("  write starts {}us (~{:.0f} lines) after the edge"
                      " before any k delay".format(latency, latency / s_line))
    print()


def sweep_1d(label, screen, display, dc):
    restore_te(screen)
    codes = (FR_CODES[46], FR_CODES[45])
    periods = []
    for code in codes:
        screen.__command(st7789.REG_FRCTRL2, code)
        time.sleep_ms(100)
        periods.append(display.te_probe(500)[0])
    print("1d {}: FRCTRL2 codes 0x{:02x}/0x{:02x} steady periods {}us / {}us".format(
        label, codes[0], codes[1], periods[0], periods[1]))

    print("  alternating per frame for {} frames: watch for glitches".format(
        DITHER_FRAMES))
    for frame in range(DITHER_FRAMES):
        screen.__command(st7789.REG_FRCTRL2, codes[frame % 2])
        draw(BACKGROUNDS[frame % 2])
        screen.update(canvas, rotation=90, v_sync=False)

    falls = []
    for cycle in range(40):
        screen.__command(st7789.REG_FRCTRL2, codes[cycle % 2])
        falls.extend(capture_falls(dc, 2))
    if len(falls) > 2:
        mean = time.ticks_diff(falls[-1], falls[0]) // (len(falls) - 1)
        print("  alternating mean period {}us against steady {}us / {}us".format(
            mean, periods[0], periods[1]))
    screen.__command(st7789.REG_FRCTRL2, FR_CODES[screen.framerate])
    print()


def run_1b():
    displays = [s.__display for s in screens]
    for screen in screens:
        restore_te(screen)
    periods = [d.te_probe(500)[0] for d in displays]
    faster = 0 if periods[0] <= periods[1] else 1
    print("1b: static TESCAN {} on the faster panel ({}, period {}us),"
          " {} interleaved frames".format(
              STATIC_N, labels[faster], periods[faster], INTERLEAVED_FRAMES))
    tescan(screens[faster], STATIC_N)
    timeouts0 = [d.te_timeouts() for d in displays]
    worst_frame = [0, 0]
    for frame in range(INTERLEAVED_FRAMES):
        draw(BACKGROUNDS[frame % 2])
        for d in displays:
            d.prepare(canvas, rotation=90)
        spidisplay.update_all(displays[0], displays[1], v_sync=True)
        for i, (s, d) in enumerate(zip(screens, displays)):
            s.__drawn()
            worst_frame[i] = max(worst_frame[i], d.stats().frame_us)
    tescan(screens[faster], 0)
    print("  worst frames {}us / {}us  te_timeouts {}".format(
        worst_frame[0], worst_frame[1],
        [d.te_timeouts() - t for d, t in zip(displays, timeouts0)]))
    print("  pass needs zero timeouts and wire-bound frames. {} carries a tear"
          " band here: 48 lines is past its margin".format(labels[faster]))
    print()


try:
    for label, screen, dc in zip(labels, screens, dc_pins):
        display = screen.__display
        screen.update(canvas, rotation=90)
        screen.__drawn()
        sweep_1a(label, screen, display, dc)
        sweep_1c(label, screen, display, dc)
        sweep_1d(label, screen, display, dc)
    run_1b()
    print("done")
finally:
    mighty.shutdown()
