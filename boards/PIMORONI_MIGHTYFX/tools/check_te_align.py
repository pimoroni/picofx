# Aligns the two panels' TE phases while interleaving, so both writes start
# together instead of up to a TE period apart. The faster panel follows: its
# edge is delayed with TESCAN (0x44) inside the measured tear margin, and its
# rate is pulled with FRCTRL2 when TESCAN cannot absorb the error, both from a
# per-frame proportional loop fed by the write_start_us skew.
#
# check_tescan.py measured the constraints this loop lives by: TESCAN tracks
# its scanline within a line but narrows the TE pulse to ~47us, the tear
# margin at the shipped rate is only 14 to 20 lines, and a panel accepts
# per-frame FRCTRL2 flips whose mean period lands between the two codes.
#
# Phases: baseline (no correction), TESCAN with slips (rate only acquires, the
# walk resets when the margin is spent), TESCAN with rate dither (the slower
# code also cancels the drift, so slips should vanish). Acceptance is steady
# skew under ~1ms with zero te_timeouts and wire-bound frames; raise PHASE_MS
# to 120_000 for an acceptance run.
#
# Set SCREEN to the panel type on the ports. A diagnostic, not an example, so it
# is not copied to the board. Run it with mpremote against a board carrying the
# update_all firmware.

import time

import spidisplay
import st7789
from mighty_fx import SPCE, MightyFX
from picovector import color, image
from screens import Screen154, Screen280

SCREEN = Screen280           # or Screen154: the panel type on the ports
PHASE_MS = 30_000
LINE_SLOTS = 344
DEADBAND_LINES = 2
KP = 1.0
MAX_STEP = 8
ASSIST_LINES = 4        # slower-code assist when the need exceeds the walk room
SLIP_FRACTION = 0.6     # of the measured margin; the walk resets above this
DITHER_FRACTION = 0.4   # of the margin; steady dither pulls the walk back here
GRID_PITCH = 20
BACKGROUNDS = (color.rgb(127, 127, 127), color.rgb(34, 177, 76))
UINT32 = 0xFFFFFFFF

assert SCREEN in (Screen154, Screen280)

mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
screens = (SCREEN(mighty.spce_a), SCREEN(mighty.spce_b))
labels = ("SP/CE A", "SP/CE B")

WIDTH, HEIGHT = screens[0].width, screens[0].height
canvas = image(HEIGHT, WIDTH, spidisplay.buffer(HEIGHT * WIDTH * 4))


def draw(background):
    canvas.pen = background
    canvas.clear()
    canvas.pen = color.rgb(0, 0, 0)
    for x in range(0, canvas.width, GRID_PITCH):
        canvas.rectangle(x, 0, 1, canvas.height)
    for y in range(0, canvas.height, GRID_PITCH):
        canvas.rectangle(0, y, canvas.width, 1)


def tescan(screen, n):
    screen.command(st7789.REG_TESCAN, bytes((n >> 8, n & 0xFF)))


def restore_te(screen):
    screen.command(st7789.REG_TEON, b"\x00")
    tescan(screen, 0)


def signed_mod(delta, period):
    # The difference folds to signed 32 bits before the period reduction: 2**32 is
    # not a multiple of a TE period, so reducing an unsigned wrap biases every
    # negative skew by (2**32 % period), 130-odd lines at these rates.
    d = ((delta + 0x80000000) & UINT32) - 0x80000000
    d %= period
    if d > period // 2:
        d -= period
    return d


# Bringup: measure each panel's period and write time, pick the follower.
for screen in screens:
    restore_te(screen)
    screen.update(canvas, rotation=90, v_sync=False)
    screen.update(canvas, rotation=90, v_sync=False)
    screen.drawn()

displays = [s.display for s in screens]
periods = [d.te_probe(500)[0] for d in displays]
frames_us = [d.stats().frame_us for d in displays]
fi = 0 if periods[0] <= periods[1] else 1      # the faster panel follows
li = 1 - fi
f_screen, l_screen = screens[fi], screens[li]
f_disp, l_disp = displays[fi], displays[li]
s_line = periods[fi] / LINE_SLOTS
margin = LINE_SLOTS + HEIGHT - frames_us[fi] / s_line
n_hi = max(4, int(margin * SLIP_FRACTION))
dither_hi = max(2, int(margin * DITHER_FRACTION))
code_norm = st7789.FRAME_RATE_CONTROL[f_screen.framerate]
code_slow = st7789.FRAME_RATE_CONTROL[f_screen.framerate - 1]

# The rate quantum sets the steady skew floor. A panel latches its frame length at
# a frame boundary, so one slow-code frame retards the follower by the whole extra
# period it ran for, and nothing finer is available to the loop.
f_screen.command(st7789.REG_FRCTRL2, code_slow)
time.sleep_ms(100)
period_slow = f_disp.te_probe(500)[0]
f_screen.command(st7789.REG_FRCTRL2, code_norm)
quantum_lines = (period_slow - periods[fi]) / s_line

print("leader {} period {}us, follower {} period {}us".format(
    labels[li], periods[li], labels[fi], periods[fi]))
print("follower margin {:.1f} lines: walk resets at {}, steady dither above {}".format(
    margin, n_hi, dither_hi))
print("drift {:.1f} lines per period, rate step {} -> {}, quantum {:.1f} lines"
      " per slow frame".format((periods[li] - periods[fi]) / s_line, code_norm,
                               code_slow, quantum_lines))
print()


def run_phase(label, correct, dither):
    n = 0
    n_sent = 0
    slow_on = False
    slips = 0
    slow_frames = 0
    skipped = 0
    skews = []
    worst_frame = 0
    timeouts0 = [d.te_timeouts() for d in displays]
    timeouts_seen = sum(timeouts0)
    n_lo_seen, n_hi_seen = n_hi, 0

    restore_te(f_screen)
    f_screen.command(st7789.REG_FRCTRL2, code_norm)
    print(label)
    frames = 0
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < PHASE_MS:
        draw(BACKGROUNDS[frames % 2])
        for d in displays:
            d.prepare(canvas, rotation=90)
        spidisplay.update_all(displays[0], displays[1], v_sync=True)
        for s in screens:
            s.drawn()
        frames += 1

        worst_frame = max(worst_frame, l_disp.stats().frame_us,
                          f_disp.stats().frame_us)
        err_us = signed_mod(f_disp.stats().write_start_us -
                            l_disp.stats().write_start_us, periods[fi])
        skews.append(abs(err_us))

        if not correct:
            continue
        timeouts_now = sum(d.te_timeouts() for d in displays)
        if timeouts_now != timeouts_seen:
            timeouts_seen = timeouts_now
            skipped += 1        # a timeout fired, so the skew is not a phase
            continue
        need = -err_us / s_line        # positive: the follower must be delayed
        if abs(need) >= DEADBAND_LINES:
            step = round(KP * need)
            step = max(-MAX_STEP, min(MAX_STEP, step))
            n = max(0, min(n_hi, n + step))
        assist = need > (n_hi - n) + ASSIST_LINES
        if not assist and not dither and n >= n_hi:
            n = 0
            slips += 1
        want_slow = assist or (dither and n > dither_hi)
        if n != n_sent:
            tescan(f_screen, n)
            n_sent = n
        if want_slow != slow_on:
            f_screen.command(st7789.REG_FRCTRL2,
                             code_slow if want_slow else code_norm)
            slow_on = want_slow
        if want_slow:
            slow_frames += 1
        n_lo_seen = min(n_lo_seen, n)
        n_hi_seen = max(n_hi_seen, n)

    steady = sorted(skews[len(skews) // 2:])
    print("  {} frames: steady skew median {}us  p95 {}us  worst {}us".format(
        frames, steady[len(steady) // 2], steady[(len(steady) * 95) // 100],
        max(skews)))
    if correct:
        print("  slips {}  slow-code duty {:.0%}  n range {}..{}  skipped {}".format(
            slips, slow_frames / frames, n_lo_seen, n_hi_seen, skipped))
    print("  worst frame {}us  te_timeouts {}".format(
        worst_frame, [d.te_timeouts() - t for d, t in zip(displays, timeouts0)]))
    print()


try:
    run_phase("baseline: no correction", correct=False, dither=False)
    run_phase("correction, slips allowed: rate assist acquires, TESCAN holds",
              correct=True, dither=False)
    run_phase("correction with rate dither: slips should vanish",
              correct=True, dither=True)
    print("done")
finally:
    restore_te(f_screen)
    f_screen.command(st7789.REG_FRCTRL2, code_norm)
    mighty.shutdown()
