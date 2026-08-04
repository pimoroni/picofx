# Measures whether a pair whose TE phases drifted apart during a pause can be
# brought back together inside a sacrificed frame, by spending the whole FRCTRL2
# range while both panels still show stale content.
#
# Nothing is visible during a pause, so neither cap on the actuators applies: the
# 14-to-20-line tear margin exists because a write is in flight, and the one-code
# FRCTRL2 pull check_te_align.py holds to exists to stay glitch-free mid-run.
# Moving both panels also makes the correction signed, so an error either way has
# an actuator instead of waiting on the pair's own drift.
#
# A panel latches its frame length at a frame boundary, so phase moves a whole frame
# at a time and a rate held for less than a period moves nothing. Excursions are
# therefore counted in frames, not timed: each panel's code goes on just after one of
# its own TE falls and comes off after a counted number of later ones. Both panels
# run their own count at once, so a correction costs the longer of the two.
#
# Phases:
#   0  Calibration: settled period per code, then the phase each panel actually
#      moves for one and two of its own frames at each code, measured.
#   1  Cross-check: skew from a dual-pin TE capture against the same skew from
#      write_start_us, corrected for the drift between the two measurements.
#   2  Visibility: the deepest excursions applied to stale content, eyes on the
#      glass for a luminance step, flicker or dither crawl.
#   3  Closure trials: align, pause, resync, then resume real frames under the fine
#      TESCAN loop, so the settled skew and te_timeouts say whether resumption is
#      clean. A resync is one measurement and one scheduled excursion, the cost an
#      application would pay; the capture after it only reports where it landed.
#
# Both halves of a resync sit between frames. A staged frame owns DC, so command()
# refuses while one is staged and the capture cannot read the TE lines either.
#
# A diagnostic, not an example, so it is not copied to the board. Run it with
# mpremote, with eyes on both panels for phases 2 and 3.

import time

import st7789
from machine import Pin
from mighty_fx import SPCE, MightyFX
from picovector import color
from screens import Screen280, update_pair

LINE_SLOTS = 344            # scanned lines per refresh including porches
DEPTHS = (1, 2, 4, 6)       # FRCTRL2 steps a panel moves from its nominal rate
MAX_FRAMES = 3              # frames of excursion a plan may spend on one panel
ACCURACY_LINES = 5          # close enough to hand over, so a plan stops paying for better
PROBE_MS = 250              # settled period probe
QUICK_MS = 70               # about three periods, for the settling question
CROSS_CHECK_SAMPLES = 40
PAUSES_MS = (300, 500, 700, 1000, 1400, 2000)
TRIAL_REPEATS = 3           # passes over PAUSES_MS, to sample more entry errors
ALIGN_FRAMES = 15           # fine-loop frames before a trial's pause
RESUME_FRAMES = 20          # fine-loop frames after a resync
CAPTURE_EDGES = 2           # TE falls per panel per capture, so about two periods
SCHEDULE_TIMEOUT_MS = 250   # a schedule spans at most MAX_FRAMES + 1 periods

# The fine loop, as check_te_align.py measured it
DEADBAND_LINES = 2
KP = 1.0
MAX_STEP = 8
SLIP_FRACTION = 0.6
DITHER_FRACTION = 0.4
ASSIST_LINES = 4

GRID_PITCH = 20
BACKGROUNDS = (color.rgb(127, 127, 127), color.rgb(34, 177, 76))
UINT32 = 0xFFFFFFFF
TICKS_MASK = 0x3FFFFFFF     # ticks_us range, for comparing against the stats clock

mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
screens = (Screen280(mighty.spce_a), Screen280(mighty.spce_b))
dc_pins = (Pin(MightyFX.SPCE_A_DC_PIN), Pin(MightyFX.SPCE_B_DC_PIN))
labels = ("SP/CE A", "SP/CE B")
for dc in dc_pins:
    dc.init(pull=Pin.PULL_DOWN)     # persists through the C module's direction flips

WIDTH, HEIGHT = screens[0].width, screens[0].height
# One canvas for both screens, so a pair frame writes each panel the same pixels
# and a measurement frame changes nothing on the glass.
canvas = screens[0].canvas(HEIGHT, WIDTH)
RATES = sorted(st7789.FRAME_RATE_CONTROL)


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


def rate(panel, rate_index):
    """Set one panel's frame rate, and hand its DC line back to the capture."""
    screens[panel].command(st7789.REG_FRCTRL2,
                           st7789.FRAME_RATE_CONTROL[RATES[rate_index]])
    dc_pins[panel].init(Pin.IN, pull=Pin.PULL_DOWN)


def fold(delta, period):
    """Signed fold of a difference into half a period."""
    d = delta % period
    if d > period // 2:
        d -= period
    return d


def signed_mod(delta, period):
    """Signed difference between two of the C module's 32-bit microsecond stamps.

    The difference folds to signed 32 bits before the period reduction: 2**32 is not
    a multiple of a TE period, so reducing an unsigned wrap biases every negative
    skew by (2**32 % period), which is 130-odd lines at these rates.
    """
    return fold(((delta + 0x80000000) & UINT32) - 0x80000000, period)


def capture_pair_falls(count, timeout_ms=500):
    """Falls on both TE lines from one loop, so the two edge sets share a clock.

    The lines are left as inputs, the C module setting DC's direction itself on the
    next transfer.
    """
    for dc in dc_pins:
        dc.init(Pin.IN, pull=Pin.PULL_DOWN)
    falls = ([], [])
    levels = [dc.value() for dc in dc_pins]
    t0 = time.ticks_ms()
    while len(falls[0]) < count or len(falls[1]) < count:
        if time.ticks_diff(time.ticks_ms(), t0) >= timeout_ms:
            break
        for i in range(2):
            value = dc_pins[i].value()
            if value != levels[i]:
                levels[i] = value
                if not value:
                    falls[i].append(time.ticks_us())
    return falls


def draw_pair(index):
    draw(BACKGROUNDS[index % 2])
    for screen in screens:
        screen.prepare(canvas, rotation=90)
    update_pair(*screens, v_sync=True)


def static_pair():
    """A pair frame of the pixels already on the panels, so the write is invisible."""
    for screen in screens:
        screen.prepare(canvas, rotation=90)
    update_pair(*screens, v_sync=True)


# Bringup: settle both panels on real content, measure their periods, pick the
# follower.
draw(BACKGROUNDS[0])
for screen in screens:
    restore_te(screen)
    screen.update(canvas, rotation=90, v_sync=False)
    screen.update(canvas, rotation=90, v_sync=False)

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
nominal = RATES.index(f_screen.framerate)
target_lines = n_hi // 2        # land inside the walk, so the fine loop has room either way
deepest = min(max(DEPTHS), nominal, len(RATES) - 1 - nominal)
depths = tuple(d for d in DEPTHS if d <= deepest)

print("leader {} period {}us, follower {} period {}us".format(
    labels[li], periods[li], labels[fi], periods[fi]))
print("follower margin {:.1f} lines: walk resets at {}, resync targets {}".format(
    margin, n_hi, target_lines))
print("nominal rate {}fps, {} steps slower and {} faster available, testing depths {}".format(
    RATES[nominal], nominal, len(RATES) - 1 - nominal, depths))
print()


def need_rate(p_follower, p_leader):
    """Lines the need changes by per microsecond, at these two panel periods."""
    return LINE_SLOTS * (1.0 / p_follower - 1.0 / p_leader)


def absorbable(need):
    """Can the fine loop take it from here?

    TESCAN only delays, so the error has to be positive. The walk holds n_hi lines
    and moves by MAX_STEP a frame, so anything inside their sum is gone in a frame
    or two, which is where check_te_align.py's own corrected worst case sits.
    """
    return 1 <= need <= n_hi + MAX_STEP


def measure_need_pins():
    """The follower's phase error in lines, from the TE lines alone. No write."""
    falls = capture_pair_falls(CAPTURE_EDGES)
    if len(falls[fi]) < 2 or len(falls[li]) < 2:
        return None, None
    ref = falls[fi][0]
    offsets = []
    for i in (fi, li):
        values = sorted(time.ticks_diff(t, ref) % periods[fi] for t in falls[i])
        offsets.append(values[len(values) // 2])
    return -fold(offsets[0] - offsets[1], periods[fi]) / s_line, \
        max(falls[fi][-1], falls[li][-1])


def measure_need_stats():
    """The same error from the last pair frame's write starts."""
    err_us = signed_mod(f_disp.stats().write_start_us - l_disp.stats().write_start_us,
                        periods[fi])
    return -err_us / s_line


def run_schedule(schedule):
    """Hold each panel's code across a counted number of that panel's own frames.

    schedule[panel] is (rate_index, frames); frames of 0 leaves that panel alone.
    Each panel's code goes on just after one of its falls and comes off after the
    counted number of later ones, so the frames it spans are whole ones.
    """
    for dc in dc_pins:
        dc.init(Pin.IN, pull=Pin.PULL_DOWN)
    waiting, counting, done = 0, 1, 2
    state = [done if schedule[i][1] <= 0 else waiting for i in range(2)]
    counts = [0, 0]
    levels = [dc.value() for dc in dc_pins]
    t0 = time.ticks_ms()
    while state[0] != done or state[1] != done:
        if time.ticks_diff(time.ticks_ms(), t0) >= SCHEDULE_TIMEOUT_MS:
            break
        for i in range(2):
            if state[i] == done:
                continue
            value = dc_pins[i].value()
            if value == levels[i]:
                continue
            levels[i] = value
            if value:
                continue                # only the falls bound a frame
            if state[i] == waiting:
                rate(i, schedule[i][0])
                state[i] = counting
            else:
                counts[i] += 1
                if counts[i] >= schedule[i][1]:
                    rate(i, nominal)
                    state[i] = done
            levels[i] = dc_pins[i].value()      # the command drove DC, so resync

    for i in range(2):
        if state[i] != done:
            rate(i, nominal)


def move_and_measure(schedule, natural):
    """Phase the schedule moved, with the pair's own drift over the window removed."""
    before, at_before = measure_need_pins()
    if before is None:
        return None
    run_schedule(schedule)
    after, at_after = measure_need_pins()
    if after is None:
        return None
    elapsed = time.ticks_diff(at_after, at_before)
    return fold(after - before, LINE_SLOTS) - natural * elapsed


def calibrate_periods():
    """Settled period per code on each panel, and whether a change lands promptly."""
    lo, hi = nominal - deepest, nominal + deepest
    settled = [{}, {}]
    for i in range(2):
        for rate_index in range(lo, hi + 1):
            rate(i, rate_index)
            quick = displays[i].te_probe(QUICK_MS)[0]
            time.sleep_ms(100)
            settled[i][rate_index] = displays[i].te_probe(PROBE_MS)[0]
            if rate_index in (lo, nominal, hi):
                print("  {} {}fps: settled {}us, first three periods {}us".format(
                    labels[i], RATES[rate_index], settled[i][rate_index], quick))
        rate(i, nominal)
    return settled


def calibrate_shifts(natural):
    """Phase each panel moves for one and two of its own frames at each code.

    Both directions on both panels, since a pause leaves the error either sign and
    a slower panel only ever retards. Returns options[panel] as a list of
    (rate_index, frames, lines), the no-op included, ready for plan_excursion.
    Measured rather than derived: the frame a code is written in may or may not be
    one of the long ones, which the fitted offset absorbs.
    """
    options = [[(nominal, 0, 0.0)], [(nominal, 0, 0.0)]]
    print("  panel    code   1 frame   2 frames   per frame")
    for i in range(2):
        for depth in depths:
            for rate_index in (nominal - depth, nominal + depth):
                schedule = [(nominal, 0), (nominal, 0)]
                moved = []
                for frames in (1, 2):
                    schedule[i] = (rate_index, frames)
                    result = move_and_measure(schedule, natural)
                    if result is None:
                        break
                    moved.append(result)
                if len(moved) < 2:
                    continue
                slope = moved[1] - moved[0]
                offset = moved[0] - slope
                for frames in range(1, MAX_FRAMES + 1):
                    options[i].append((rate_index, frames, offset + slope * frames))
                print("  {}  {:>4}fps  {:>+8.1f}  {:>+9.1f}  {:>+8.1f} lines".format(
                    labels[i], RATES[rate_index], moved[0], moved[1], slope))
    return options


def plan_excursion(error, options):
    """Frames of each panel's code to spend cancelling the error.

    Both panels count at once, so a plan costs the longer of the two. The cheapest
    plan landing within ACCURACY_LINES wins: the fine loop absorbs that much in a
    frame, so buying a closer landing with another period of held rate is waste.
    Failing that, the closest landing at any cost.
    """
    # Only codes pushing the way the error needs are worth pairing, which quarters
    # the search: it runs inside the resync, so its own cost is part of the answer.
    want_negative = error > 0
    usable = [[option for option in options[i]
               if option[1] == 0 or (option[2] < 0) == want_negative]
              for i in range(2)]

    cheapest = None
    closest = (abs(error), 0, [(nominal, 0), (nominal, 0)])
    for f_index, f_frames, f_lines in usable[fi]:
        for l_index, l_frames, l_lines in usable[li]:
            left = abs(error + f_lines + l_lines)
            cost = max(f_frames, l_frames)
            schedule = [None, None]
            schedule[fi] = (f_index, f_frames)
            schedule[li] = (l_index, l_frames)
            if left < closest[0]:
                closest = (left, cost, schedule)
            if left > ACCURACY_LINES:
                continue
            if cheapest is None or (cost, left) < (cheapest[1], cheapest[0]):
                cheapest = (left, cost, schedule)

    best = cheapest if cheapest is not None else closest
    return best[2], best[1]


def cross_check(natural):
    """Does the writeless pin capture agree with the pair frame's write starts?"""
    print("phase 1: cross-check, {} samples over the free-running drift".format(
        CROSS_CHECK_SAMPLES))
    raw, corrected = [], []
    for _ in range(CROSS_CHECK_SAMPLES):
        need_pins, captured_at = measure_need_pins()
        if need_pins is None:
            continue
        static_pair()
        need_stats = measure_need_stats()
        # The two cannot be taken at once, a staged frame owning the DC lines, so
        # the drift over the gap is predicted out before the comparison.
        gap_us = time.ticks_diff(f_disp.stats().write_start_us & TICKS_MASK,
                                 captured_at & TICKS_MASK)
        raw.append(fold(need_stats - need_pins, LINE_SLOTS))
        corrected.append(fold(need_stats - (need_pins + natural * gap_us), LINE_SLOTS))

    if not raw:
        print("  no samples: too few edges captured, so the TE pulse may be narrowed")
        print()
        return
    for name, residuals in (("raw", raw), ("drift-corrected", corrected)):
        spread = sorted(abs(r) for r in residuals)
        print("  {}: median {:.1f} lines, worst {:.1f} lines".format(
            name, spread[len(spread) // 2], spread[-1]))
    print("  {} samples of {} kept".format(len(raw), CROSS_CHECK_SAMPLES))
    print()


def visibility(options):
    """The deepest excursion each panel has, against stale content, for the eyes."""
    print("phase 2: visibility. Both panels hold a still grid; watch for a"
          " luminance step, flicker or dither crawl")
    draw_pair(0)
    draw_pair(0)        # a second frame, so the backlights are latched on real content
    calibrated = [{option[0] for option in options[i]} for i in range(2)]
    for depth in depths:
        f_index, l_index = nominal - depth, nominal + depth
        if f_index not in calibrated[fi] or l_index not in calibrated[li]:
            continue
        print("  depth {}: {}fps and {}fps for {} frames each".format(
            depth, RATES[f_index], RATES[l_index], MAX_FRAMES))
        schedule = [None, None]
        schedule[fi] = (f_index, MAX_FRAMES)
        schedule[li] = (l_index, MAX_FRAMES)
        run_schedule(schedule)
        time.sleep_ms(1000)
    print()


def fine_frames(count, walk):
    """Real pair frames under the TESCAN loop. Returns the walk and the skews."""
    slow_on = False
    skews = []
    for frame in range(count):
        draw_pair(frame)
        need = measure_need_stats()
        skews.append(abs(need) * s_line)
        if abs(need) >= DEADBAND_LINES:
            step = max(-MAX_STEP, min(MAX_STEP, round(KP * need)))
            walk = max(0, min(n_hi, walk + step))
        tescan(f_screen, walk)
        want_slow = need > (n_hi - walk) + ASSIST_LINES or walk > dither_hi
        if want_slow != slow_on:
            rate(fi, nominal - 1 if want_slow else nominal)
            slow_on = want_slow
    if slow_on:
        rate(fi, nominal)
    return walk, skews


def resync(options, natural):
    """One measurement and one scheduled excursion, which is all an application pays.

    The verification capture afterwards is instrumentation. Its cost is reported
    apart from the resync's own, and the error it reads is aged back to the handover,
    the pair having drifted over the two periods the capture spans.
    """
    t0 = time.ticks_us()
    entry, captured_at = measure_need_pins()
    if entry is None:
        return None, None, 0, 0, 0, 0
    capture_us = time.ticks_diff(time.ticks_us(), t0)
    frames, plan_us = 0, 0
    if not absorbable(entry):
        # The capture spans two periods, so the error is aged forward to now.
        aged = entry + natural * time.ticks_diff(time.ticks_us(), captured_at)
        t_plan = time.ticks_us()
        schedule, frames = plan_excursion(aged - target_lines, options)
        plan_us = time.ticks_diff(time.ticks_us(), t_plan)
        run_schedule(schedule)
    handover = time.ticks_us()
    cost_us = time.ticks_diff(handover, t0)

    left, left_at = measure_need_pins()
    if left is not None:
        left -= natural * time.ticks_diff(left_at, handover)
    return entry, left, cost_us, capture_us, plan_us, frames


def closure_trials(options, natural):
    """Align, pause, resync, resume. The headline measurement."""
    print("phase 3: closure trials. Watch the resume instant for a stagger or a tear")
    absorbed = 0
    trials = 0
    worst_cost = 0
    for repeat in range(TRIAL_REPEATS):
        print("  pass {} of {}".format(repeat + 1, TRIAL_REPEATS))
        for pause_ms in PAUSES_MS:
            walk, _ = fine_frames(ALIGN_FRAMES, 0)
            tescan(f_screen, 0)     # the capture needs the wide V-porch pulse
            timeouts0 = [d.te_timeouts() for d in displays]

            time.sleep_ms(pause_ms)
            entry, left, cost_us, capture_us, plan_us, frames = resync(options, natural)

            walk, skews = fine_frames(RESUME_FRAMES, walk)
            steady = sorted(skews[len(skews) // 2:])
            timeouts = [d.te_timeouts() - t for d, t in zip(displays, timeouts0)]
            trials += 1
            worst_cost = max(worst_cost, cost_us)
            if left is not None and absorbable(left):
                absorbed += 1
            print("    pause {:>5}ms: entered {:>+6.1f}, left {:>+5.1f} lines in"
                  " {} frame(s), {}".format(
                      pause_ms, entry if entry is not None else 0.0,
                      left if left is not None else 0.0, frames,
                      "absorbed" if left is not None and absorbable(left)
                      else "outside the walk"))
            print("      resync {:.0f}us ({:.1f} periods): {:.0f}us measuring,"
                  " {:.0f}us planning, {:.0f}us moving".format(
                      cost_us, cost_us / periods[fi], capture_us, plan_us,
                      cost_us - capture_us - plan_us))
            print("      resumed: settled skew median {:.0f}us, worst {:.0f}us,"
                  " te_timeouts {}".format(
                      steady[len(steady) // 2], max(skews), timeouts))
    print()
    print("  {} of {} trials landed inside the walk; worst resync {:.0f}us"
          " ({:.1f} periods)".format(
              absorbed, trials, worst_cost, worst_cost / periods[fi]))
    print()


try:
    print("phase 0: calibration")
    settled_periods = calibrate_periods()
    natural_drift = need_rate(settled_periods[fi][nominal], settled_periods[li][nominal])
    print("  natural drift {:+.2f} lines a period".format(
        natural_drift * settled_periods[fi][nominal]))
    plan_options = calibrate_shifts(natural_drift)
    print()

    cross_check(natural_drift)
    visibility(plan_options)
    closure_trials(plan_options, natural_drift)
    print("done")
finally:
    restore_te(f_screen)
    rate(fi, nominal)
    rate(li, nominal)
    mighty.shutdown()
