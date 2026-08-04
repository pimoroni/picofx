# Checks that a ScreenPair with align on reaches the skew the diagnostic loop
# reaches (tools/check_te_align.py), and that an application pausing and resuming
# shows no visible stagger, the pair spending a resync on the drift the pause left
# (tools/check_te_resync.py measured both).
#
# Phases: placement resolution asserted against the documented table, since wrong
# disambiguation is silent; an aligned run reporting steady skew against the pair's
# own predicted floor; a cadence run asserting normal animation never reaches the
# resync trigger; pause-and-resume trials with eyes on the resume instant; and solo
# updates on each screen, which must hand back the follower's panel state.
#
# Set SCREEN to the panel type on the ports. A diagnostic, not an example, so it is
# not copied to the board. Run it with mpremote, with eyes on both panels.

import time

import screens
from mighty_fx import SPCE, MightyFX
from picovector import color
from screens import Screen154, Screen280, ScreenPair

SCREEN = Screen154          # or Screen280: the panel type on the ports
ALIGN_MS = 30_000           # the aligned run; raise for an acceptance soak
CADENCE_FRAMES = 200
PAUSES_MS = (300, 500, 700, 1000, 1400, 2000)
RESUME_FRAMES = 20
# An update this late must have spent a resync. Measured on both pair types: the
# worst normal update is 75ms on the 154 and 88ms on the 280, where the cheapest
# resync frame is 133ms, the capture and excursion coming on top of the frame.
RESYNC_MIN_MS = 120
GRID_PITCH = 20
BACKGROUNDS = (color.rgb(127, 127, 127), color.rgb(34, 177, 76))

assert SCREEN in (Screen154, Screen280)


def check_resolution():
    """Every row of the offset table, and the shapes that must reject."""
    values = screens.__pair_values
    assert values(90, "rotation") == (90, 90)
    assert values((90, 270), "rotation") == (90, 270)
    assert values(False, "mirror") == (False, False)
    for bad in ((90,), (0, 90, 180)):
        try:
            values(bad, "rotation")
            raise AssertionError(f"{bad} resolved instead of rejecting")
        except ValueError:
            pass

    offsets = screens.__pair_offsets
    assert offsets(None) == (None, None)
    assert offsets((5, 10)) == ((5, 10), (5, 10))
    assert offsets((5, None)) == ((5, None), (5, None))     # shared: 5 is no (x, y)
    assert offsets((None, None)) in (((None, None), (None, None)), (None, None))
    assert offsets((None, (5, 10))) == (None, (5, 10))
    assert offsets(((0, 0), (5, 10))) == ((0, 0), (5, 10))
    for bad in (((0, 0), 5), (5, (0, 0)), ((0, 0, 0), (1, 2)), ((1, 2), (0,)),
                (1, 2, 3), 5):
        try:
            offsets(bad)
            raise AssertionError(f"{bad} resolved instead of rejecting")
        except ValueError:
            pass
    print("placement resolution: every table row and rejection holds")


def draw(background):
    canvas.pen = background
    canvas.clear()
    canvas.pen = color.rgb(0, 0, 0)
    for x in range(0, canvas.width, GRID_PITCH):
        canvas.rectangle(x, 0, 1, canvas.height)
    for y in range(0, canvas.height, GRID_PITCH):
        canvas.rectangle(0, y, canvas.width, 1)


def pair_frame(index):
    draw(BACKGROUNDS[index % 2])
    started = time.ticks_us()
    pair.update(canvas, rotation=90)
    return time.ticks_diff(time.ticks_us(), started)


def skew_us():
    """The last pair frame's write-start skew, as the fine loop sees it."""
    err = screens.__signed_mod(pair.__f_disp.stats().write_start_us
                               - pair.__l_disp.stats().write_start_us,
                               pair.__period_f)
    return abs(err)


def timeouts():
    return sum(screen.display.te_timeouts() for screen in pair.screens)


def report_skews(label, skews, timeouts_before):
    steady = sorted(skews[len(skews) // 2:])
    print("  {}: {} frames, steady skew median {}us  p95 {}us  worst {}us,"
          " te_timeouts {}".format(
              label, len(skews), steady[len(steady) // 2],
              steady[(len(steady) * 95) // 100], max(skews),
              timeouts() - timeouts_before))


def aligned_run():
    print("aligned run, target is the pair's own floor of {:.0f}us".format(
        pair.align_floor_us))
    timeouts0 = timeouts()
    skews = []
    frame = 0
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < ALIGN_MS:
        pair_frame(frame)
        skews.append(skew_us())
        frame += 1
    report_skews("aligned", skews, timeouts0)
    print()


def cadence_run():
    """Normal animation must never reach the resync trigger."""
    print("cadence run: {} frames back to back, no update may spend a resync".format(
        CADENCE_FRAMES))
    worst_ms = 0
    for frame in range(CADENCE_FRAMES):
        worst_ms = max(worst_ms, pair_frame(frame) // 1000)
    assert worst_ms < RESYNC_MIN_MS, f"a frame took {worst_ms}ms, so a resync fired mid-animation"
    print("  worst frame {}ms, no resync".format(worst_ms))
    print()


def pause_trials():
    print("pause and resume trials. Watch the resume instant for a stagger")
    frame = 0
    for pause_ms in PAUSES_MS:
        for _ in range(10):     # settle before the pause
            pair_frame(frame)
            frame += 1
        timeouts0 = timeouts()
        time.sleep_ms(pause_ms)

        resume_ms = pair_frame(frame) // 1000
        frame += 1
        skews = []
        for _ in range(RESUME_FRAMES):
            pair_frame(frame)
            skews.append(skew_us())
            frame += 1
        print("  pause {:>5}ms: resume frame {}ms{}".format(
            pause_ms, resume_ms,
            ", resync spent" if resume_ms >= RESYNC_MIN_MS else ""))
        report_skews("resumed", skews, timeouts0)
    print()


def solo_updates():
    """A screen updated outside its pair hands the follower's panel state back."""
    print("solo updates on both screens, then the pair resumes")
    timeouts0 = timeouts()
    for _ in range(5):
        for screen in pair.screens:
            screen.update(canvas, rotation=90)
    skews = []
    for frame in range(RESUME_FRAMES):
        pair_frame(frame)
        skews.append(skew_us())
    report_skews("resumed", skews, timeouts0)
    print()


mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
built = (SCREEN(mighty.spce_a), SCREEN(mighty.spce_b))
pair = None

try:
    try:
        ScreenPair(built[0], built[0])
        raise AssertionError("a pair of one screen constructed instead of rejecting")
    except ValueError:
        pass

    t0 = time.ticks_ms()
    pair = ScreenPair(*built)
    print("calibrated in {}ms, predicted floor {:.0f}us".format(
        time.ticks_diff(time.ticks_ms(), t0), pair.align_floor_us))

    check_resolution()
    try:
        pair.update()
        raise AssertionError("update() without an image ran instead of raising")
    except TypeError:
        pass

    WIDTH, HEIGHT = built[0].width, built[0].height
    canvas = built[0].canvas(HEIGHT, WIDTH)

    aligned_run()
    cadence_run()
    pause_trials()
    solo_updates()
    print("done")
finally:
    if pair is not None:
        pair.align = False
    mighty.shutdown()
