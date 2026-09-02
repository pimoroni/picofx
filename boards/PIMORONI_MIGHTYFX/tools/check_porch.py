# Is the ST7789 porch a runtime rate trim? PORCTRL (0xB2) sets the back and front
# porch, so it sets how many scan slots a refresh spends, and one porch line should
# buy one line time against FRCTRL2's 8.5. setup() writes it once before DISPON, so
# whether a panel honours a later change, latches it at a frame boundary and does it
# without a visible glitch is what this answers. A ScreenGroup's alignment rests on
# the answer, since it trims and dithers a member's rate in porch lines.
#
# Experiments, all on the one panel named by UNDER_TEST:
#   1  Sweep: the achieved period and TE pulse at each porch against the one-line
#      claim, the line time the sweep's own slope measures, and each row's tear
#      margin. Splitting a step between the two porches says whether they are
#      interchangeable, and the rows below the default say whether a trim can speed
#      a panel up as well as slow it, which decides whether a group's reference has
#      to be its slowest member.
#   2  Latch: consecutive TE periods across a write. 2a writes just after a fall,
#      320 scan lines before the blanking it changes. 2b writes at three points
#      inside a long blanking and asks for a much shorter one, which is the only
#      way a frame could come out malformed and is a phase a free-running dither
#      reaches. A spanning period matching neither steady value is the fault.
#   3  Glitch, eyes on the panel: the porch alternated under a still image and then
#      under a v_sync stream, by one line as the hold would dither it and by 32 as
#      an acquisition would step it. The mean period over the alternation says
#      whether every frame took the value in force.
#
# Every panel on the harness is built, so each is sent TEOFF at bringup, and TEON
# then goes to the one under test alone. A panel nobody built keeps whatever TE
# state it was left in and would drive the shared line, and an unclaimed CS floats
# low so it would take the frames as well. On a lone panel, leave HARNESS at one
# entry. Diodes are what make the shared line readable at all.
#
# The short porches are the one part that could misbehave, a refresh below what the
# panel's drive expects. The default is written back whatever happens.
#
# Lengthening the porch lowers the refresh rate, which matters on the 1.54": it ships
# at 53fps and (28, 28) takes it to about 48.5, under the roughly 50fps at which that
# panel is known to pulse. So the sweep prints the achieved rate per row and names any
# row that crosses PULSE_FPS, since a pulse there belongs to the rate and not to the
# porch. A group's own trims are five or six lines, nowhere near it.
#
# A diagnostic, not an example, so it is not copied to the board. Run it with
# mpremote, with eyes on the panel under test for experiment 3.

import time

import screens
import st7789
from machine import Pin
from mighty_fx import SPCE, MightyFX
from picovector import color, image

# The harness as it is wired. SP/CE A's own CS comes first: that
# screen takes the port's own DC, and every later one shares it by name.
HARNESS = (
    (33, screens.Screen280),
    (24, screens.Screen154),
    (25, screens.Screen280),
    (26, screens.Screen280),
    (27, screens.Screen154),
    (37, screens.Screen280),
)
UNDER_TEST = 27             # run both panel types: the 1.54 is the margin table's thin case
BAUDRATE = 24_000_000

TEM_VBLANK = b"\x00"
PORCH_TAIL = b"\x00\x33\x33"        # PSEN off, then the idle and partial porches
DEFAULT_PORCH = (12, 12)            # what setup() writes: 320 rows plus these is LINE_SLOTS

PORCHES = (
    (12, 12),   # the default, and the row every other is read against
    (12, 13),   # one line, on the front porch alone
    (13, 12),   # one line, on the back porch alone
    (13, 13),
    (14, 14),
    (16, 16),
    (12, 24),   # twelve lines, all on the front
    (24, 12),   # the same twelve, all on the back
    (20, 20),
    (28, 28),
    (6, 6),     # below the default: a trim that speeds a panel up
    (2, 2),
    (12, 12),   # back to the default, which the period must return to
)

# Experiment 3 writes frames, so both ends of a step want tear margin and a rate above
# PULSE_FPS, or the stream tears or pulses on its own account and the porch is blamed.
# The 2.80 has room at its default porch. A 1.54 whose oscillator runs fast has none
# there, 31,506us of frame against 584 lines of budget, so its steps sit on a longer
# porch, which is the thing the porch is for. Its step is also 8 lines and not 32,
# since 32 would take it under PULSE_FPS whatever it started from.
GLITCH_STEPS = {
    screens.Screen280: (((12, 12), (12, 13)), ((12, 12), (28, 28))),
    screens.Screen154: (((20, 20), (20, 21)), ((20, 20), (24, 24))),
}

PROBE_MS = 500
SETTLE_MS = 100
LATCH_PAIR = ((12, 12), (28, 28))       # the 32 lines an acquisition would step by
BLANK_PAIR = ((28, 28), (6, 6))         # the widest shortening the sweep covers
BLANK_PLACES = (0.05, 0.45, 0.85)       # of the blanking in force, past the TE rise
LATCH_EDGES = 12            # falls per latch run, the write landing halfway
LATCH_RUNS = 4
LATCH_TOLERANCE_US = 200    # about three lines, well inside the 2,000 the step moves
WRITE_US = 350              # what a PORCTRL write and the two DC flips cost
DITHER_FALLS = 60           # falls the alternating mean is taken over
GLITCH_SECONDS = 5
ALTERNATE_MS = 120          # about five frames a value under a still image
PULSE_FPS = 50              # the 1.54" pulses below about this, which the porch reaches
GRID_PITCH = 20
BACKGROUNDS = ((127, 127, 127), (34, 177, 76))

LINE_SLOTS = st7789.LINE_SLOTS
CONTROLLER_ROWS = LINE_SLOTS - sum(DEFAULT_PORCH)

mighty = MightyFX(spce_a=SPCE.SCREEN)
port = mighty.spce_a

panels = {}
for index, (cs, screen_class) in enumerate(HARNESS):
    panels[cs] = (screen_class(port, te=False, baudrate=BAUDRATE) if index == 0
                  else screen_class(port, cs=Pin(cs), dc=port.dc, te=False, baudrate=BAUDRATE))

panel = panels[UNDER_TEST]
display = panel.__display
panel.brightness(1.0)

dc = Pin(MightyFX.SPCE_A_DC_PIN)
dc.init(pull=Pin.PULL_DOWN)         # persists through the C module's direction flips

# Many band claims can leave the SRAM region too small for a canvas, in which case a
# PSRAM image still draws. Only frame_us is timed, and it costs about twice as much
# per pixel to convert from PSRAM, so the sweep's margin column reads pessimistically
# on the fallback. Nothing else here turns on it.
try:
    canvas = panel.canvas()
except ValueError:
    canvas = image(panel.width, panel.height)
    print("SRAM canvas did not fit; using a PSRAM image, so the margin column is pessimistic")


def set_porch(porch):
    panel.__command(st7789.REG_PORCTRL, bytes(porch) + PORCH_TAIL)


def read_te():
    """Hand DC back to the panel as a TE input, from a genuine low.

    A released line decaying through the pull-down otherwise reads as a blanking
    that has already finished, which is why arm() and te_probe() both do this.
    """
    dc.value(0)
    dc.init(Pin.IN, pull=Pin.PULL_DOWN)


def capture_falls(count, timeout_ms=2000, on_fall=None):
    """Falling-edge timestamps, unbroken across any register write on_fall makes.

    on_fall(n) takes the count of falls so far and returns whether it wrote, since
    a write takes DC back as an output. It costs no edge: it follows a fall that
    has just happened, so the next one is a whole period away.
    """
    read_te()
    falls = []
    started = time.ticks_ms()
    level = dc.value()
    while len(falls) < count:
        if time.ticks_diff(time.ticks_ms(), started) >= timeout_ms:
            break
        value = dc.value()
        if value != level:
            level = value
            if not value:
                falls.append(time.ticks_us())
                if on_fall is not None and on_fall(len(falls)):
                    read_te()
                    level = dc.value()
    return falls


def intervals(falls):
    return [time.ticks_diff(falls[i + 1], falls[i]) for i in range(len(falls) - 1)]


def steady_period(porch):
    set_porch(porch)
    time.sleep_ms(SETTLE_MS)
    return display.te_probe(PROBE_MS)[0]


def draw(rgb):
    canvas.pen = color.rgb(*rgb)
    canvas.clear()
    canvas.pen = color.rgb(0, 0, 0)
    for x in range(0, canvas.width, GRID_PITCH):
        canvas.rectangle(x, 0, 1, canvas.height)
    for y in range(0, canvas.height, GRID_PITCH):
        canvas.rectangle(0, y, canvas.width, 1)


def line_time(rows):
    """Microseconds a scan slot costs, least squares over the sweep's own rows."""
    count = len(rows)
    mean_slots = sum(slots for slots, _ in rows) / count
    mean_period = sum(period for _, period in rows) / count
    covariance = sum((s - mean_slots) * (p - mean_period) for s, p in rows)
    variance = sum((s - mean_slots) ** 2 for s, _ in rows)
    return covariance / variance if variance else 0.0


def measured(results, porch):
    for got, period, high in results:
        if got == porch:
            return period, high
    return None, None


def sweep(s_line, frame_us):
    print("\n1 sweep: does a porch line buy a line time?")
    print("   bpa  fpa  slots   period    fps  err(lines)   high  blank(lines)   margin")
    results = []
    rows = []
    slow = []
    for porch in PORCHES:
        set_porch(porch)
        time.sleep_ms(SETTLE_MS)
        period_us, high_us, edges = display.te_probe(PROBE_MS)
        if edges < 2:
            print(f"   {porch[0]:>3}  {porch[1]:>3}   TE silent, {edges} edges")
            continue

        slots = CONTROLLER_ROWS + porch[0] + porch[1]
        fps = 1_000_000 / period_us
        error_lines = (period_us - s_line * slots) / s_line
        blank_lines = high_us / s_line
        margin_us = (slots + panel.height - frame_us / s_line) * s_line
        print(f"   {porch[0]:>3}  {porch[1]:>3}  {slots:>5}  {period_us:>7}  {fps:>5.1f}"
              f"  {error_lines:>+10.2f}  {high_us:>5}  {blank_lines:>12.2f}"
              f"  {margin_us:>6.0f}us")
        results.append((porch, period_us, high_us))
        rows.append((slots, period_us))
        if fps < PULSE_FPS:
            slow.append(porch)

    if len(rows) > 1:
        slope = line_time(rows)
        print(f"   the sweep's own slope: {slope:.3f}us a porch line, against the"
              f" baseline's {s_line:.3f}us line time ({100 * (slope - s_line) / s_line:+.1f}%)")

    for label, first, second in (("one line", (12, 13), (13, 12)),
                                 ("twelve lines", (12, 24), (24, 12))):
        front, front_high = measured(results, first)
        back, back_high = measured(results, second)
        if front is not None and back is not None:
            print(f"   {label} on the front against the back: {front}us / {back}us,"
                  f" TE high {front_high}us / {back_high}us")

    highs = [high for _, _, high in results]
    if highs:
        print(f"   TE high ran {min(highs)}us to {max(highs)}us over the sweep, against"
              f" the 1,000 to 3,000us a healthy shared line reads")
    if slow:
        print(f"   {slow} took the panel under {PULSE_FPS}fps, where a 1.54 pulses on"
              f" its own account. Read a flicker at those rows as the rate")
    return results


def reads_as(spanning, was, becomes):
    if abs(spanning - was) <= LATCH_TOLERANCE_US:
        return "the old period, so the change waited for the frame after"
    if abs(spanning - becomes) <= LATCH_TOLERANCE_US:
        return "the new period, so the change was in force for this one"
    return "neither period, so the blanking was cut from where it already stood"


def latch(pair, steady, place, runs, s_line):
    """Periods across a porch write, placed by `place`.

    None writes just after a fall, at the start of the visible scan. A fraction
    waits out the visible scan and then that much of the blanking in force, less
    what the write itself costs, so the write completes before the blanking ends.
    """
    placed = []
    half = LATCH_EDGES // 2
    for run in range(runs):
        forward = run % 2 == 0
        start, target = pair if forward else (pair[1], pair[0])
        was, becomes = (steady[0], steady[1]) if forward else (steady[1], steady[0])
        delay_us = 0 if place is None else max(0, int(place * (sum(start) * s_line - WRITE_US)))

        set_porch(start)
        time.sleep_ms(SETTLE_MS)

        def switch(n, target=target, at=half, wait=place is not None, delay=delay_us):
            if n != at:
                return False
            if wait:
                spun = time.ticks_ms()
                while not dc.value():       # out through the visible scan to the rise
                    if time.ticks_diff(time.ticks_ms(), spun) > 100:
                        break
                rose = time.ticks_us()
                while time.ticks_diff(time.ticks_us(), rose) < delay:
                    pass
                set_porch(target)
                placed.append(time.ticks_diff(time.ticks_us(), rose))
            else:
                set_porch(target)
            return True

        gaps = intervals(capture_falls(LATCH_EDGES, 2000, switch))
        if len(gaps) < half + 1:
            print(f"   {start} to {target}: only {len(gaps) + 1} falls captured")
            continue

        marked = [f"[{gap}]" if index == half - 1 else str(gap)
                  for index, gap in enumerate(gaps)]
        print(f"   {start} to {target}: {' '.join(marked)}")
        if placed:
            print(f"     written by {placed[-1]}us into a blanking of"
                  f" {sum(start) * s_line:.0f}us, asking for {sum(target) * s_line:.0f}us")
        print(f"     the bracketed period spans the write and reads"
              f" {reads_as(gaps[half - 1], was, becomes)}")


def dither_mean(pair, steady):
    def swap(n, values=pair):
        set_porch(values[n % 2])
        return True

    set_porch(pair[0])
    time.sleep_ms(SETTLE_MS)
    falls = capture_falls(DITHER_FALLS, 4000, swap)
    if len(falls) < 3:
        print(f"     only {len(falls)} falls captured, no mean")
        return

    mean = time.ticks_diff(falls[-1], falls[0]) / (len(falls) - 1)
    print(f"     alternating every frame: mean {mean:.0f}us over {len(falls)} falls,"
          f" against the two steady periods averaging {(steady[0] + steady[1]) / 2:.0f}us")


def write_frame(index):
    """One v_sync frame, so the porch is the only thing that can disturb the glass.

    The panel is built te=False, a shared DC line permitting nothing else, so this
    goes through the display to reach v_sync. Unsynced, a 42ms write against a 22ms
    period tears every time and would read as a porch fault.
    """
    draw(BACKGROUNDS[index % 2])
    dc.value(0)                     # pre-discharge; group one does this in C
    display.update(canvas, v_sync=True)


def glitch_still(pair, label):
    write_frame(0)
    print(f"   still image, {label}: {GLITCH_SECONDS}s at {ALTERNATE_MS}ms a value."
          f" Watch for a flicker, a roll or a brightness step")
    deadline = time.ticks_add(time.ticks_ms(), GLITCH_SECONDS * 1000)
    index = 0
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        set_porch(pair[index % 2])
        index += 1
        time.sleep_ms(ALTERNATE_MS)
    print(f"     {index} changes, no frame written through any of them")


def glitch_stream(pair, steady, label):
    print(f"   v_sync stream, {label}: {GLITCH_SECONDS}s alternating every frame."
          f" Watch for a tear band, a roll or a dropped frame")
    timeouts = display.te_timeouts()
    deadline = time.ticks_add(time.ticks_ms(), GLITCH_SECONDS * 1000)
    frames = 0
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        set_porch(pair[frames % 2])
        write_frame(frames)
        frames += 1
    print(f"     {frames} frames, {display.te_timeouts() - timeouts} te timeouts,"
          f" last frame {display.stats().frame_us}us")

    # Nothing writes PORCTRL between the last frame and this probe, so a period
    # matching the porch last set is what says a written frame leaves it alone.
    last = (frames - 1) % 2
    print(f"     period after the stream {display.te_probe(PROBE_MS)[0]}us,"
          f" against {steady[last]}us steady at {pair[last]}")


try:
    others = len(HARNESS) - 1
    print(f"check_porch: {type(panel).__name__} on CS {UNDER_TEST},"
          f" {panel.width}x{panel.height}, {panel.framerate}fps at {BAUDRATE} baud")
    print(f"  {others} other panels built and left at TEOFF on the shared DC line")

    panel.update(canvas)                # warm, then measure the write this panel costs
    panel.update(canvas)
    frame_us = display.stats().frame_us

    panel.__command(st7789.REG_TEON, TEM_VBLANK)
    base_period, base_high, base_edges = display.te_probe(PROBE_MS)
    if base_edges < 2:
        raise ValueError(f"TE is silent on CS {UNDER_TEST}: {base_edges} edges."
                         f" Check the diode on that breakout and the HARNESS wiring")

    s_line = base_period / LINE_SLOTS
    print(f"  baseline: TE period {base_period}us, high {base_high}us,"
          f" {base_edges} edges")
    print(f"  {s_line:.3f}us a line over LINE_SLOTS {LINE_SLOTS}, and the blanking"
          f" reads {base_high / s_line:.2f} lines against the {sum(DEFAULT_PORCH)} set")
    print(f"  frame {frame_us}us unsynced, which the margin column is against")

    sweep(s_line, frame_us)

    steady = [steady_period(porch) for porch in LATCH_PAIR]
    print(f"\n2a latch: the write placed at the start of the visible scan,"
          f" steady {LATCH_PAIR[0]} {steady[0]}us, {LATCH_PAIR[1]} {steady[1]}us")
    latch(LATCH_PAIR, steady, None, LATCH_RUNS, s_line)

    steady = [steady_period(porch) for porch in BLANK_PAIR]
    print(f"\n2b latch: the write placed inside the blanking it changes,"
          f" steady {BLANK_PAIR[0]} {steady[0]}us, {BLANK_PAIR[1]} {steady[1]}us")
    for place in BLANK_PLACES:
        print(f"   {place:.0%} of the way through the blanking in force")
        latch(BLANK_PAIR, steady, place, 2, s_line)

    dither_step, acquire_step = GLITCH_STEPS[type(panel)]
    acquire_lines = sum(acquire_step[1]) - sum(acquire_step[0])
    print("\n3 glitch: eyes on the panel under test")
    for step, label in ((dither_step, "one line, as the hold dithers"),
                        (acquire_step, f"{acquire_lines} lines, as an acquisition steps")):
        steady = [steady_period(porch) for porch in step]
        rates = [1_000_000 / period for period in steady]
        margins = [(CONTROLLER_ROWS + sum(porch) + panel.height - frame_us / s_line) * s_line
                   for porch in step]
        print(f"  {label}:")
        for index, porch in enumerate(step):
            print(f"    {porch} {steady[index]}us at {rates[index]:.1f}fps,"
                  f" tear margin {margins[index]:.0f}us")
        if min(rates) < PULSE_FPS:
            print(f"    under {PULSE_FPS}fps: read a flicker as the rate before the porch")
        if min(margins) < 0:
            print("    negative margin: the stream tears on its own account here."
                  " Sit this step on a longer porch")
        glitch_still(step, label)
        glitch_stream(step, steady, label)
        dither_mean(step, steady)

    print("\ndone. The porch is usable if the sweep tracked the one-line claim, the"
          " latch runs read old, and nothing showed on the glass.")

finally:
    set_porch(DEFAULT_PORCH)
    panel.__command(st7789.REG_TEOFF)
    mighty.shutdown()
