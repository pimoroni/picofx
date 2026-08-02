# Measures where the backlight stops responding, and compares gamma curves on
# the panel. The floor is a property of the driver circuit, so it decides how
# much of a curve's control range is usable and no amount of arithmetic answers
# it.
#
# brightness is a linear duty today, so phase 1 sets it directly and descends
# until the panel reads as off. Phase 2 replays equal control steps under each
# candidate gamma, which only an eye can judge.
#
# Both phases advance on the user switch, so nothing is timed against a guess at
# how long a judgement takes.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across
# to run it. Wiring: a 2.8" on SP/CE A, the same panel Tufty carries.

import time

from mighty_fx import SPCE, MightyFX
from picovector import color
from screens import Screen280

# Descending duties for the floor hunt. Roughly logarithmic, and the range
# covers what the candidate gammas map their lower half onto: gamma 2.8 puts
# control 0.5 at 0.144 and control 0.1 at 0.0016.
DUTIES = (0.500, 0.300, 0.200, 0.144, 0.100, 0.070, 0.050, 0.035, 0.021,
          0.015, 0.010, 0.007, 0.005, 0.0035, 0.0021, 0.0016, 0.0010,
          0.0007, 0.0005, 0.0003, 0.0002, 0.0001)

# Compared in phase 2, against the equal control steps in STEPS. 1.0 is the
# shipped behaviour, 2.2 is RGB_GAMMA, 2.8 is TinyFX's OUTPUT_GAMMA, 3.0 is the
# cube root that matches perceived lightness exactly.
GAMMAS = (1.0, 2.2, 2.8, 3.0)
STEPS = (0.2, 0.4, 0.6, 0.8, 1.0)

# A press shorter than this is a bounce; a held switch repeats no faster
DEBOUNCE_MS = 200


def wait_for_press(mighty, prompt):
    """Block until the user switch goes down, then comes back up."""
    print(prompt)

    while not mighty.boot_pressed():
        time.sleep_ms(10)

    time.sleep_ms(DEBOUNCE_MS)

    while mighty.boot_pressed():
        time.sleep_ms(10)

    time.sleep_ms(DEBOUNCE_MS)


def pressed_since(mighty, ms):
    """Whether the switch was pressed at any point in the next ms milliseconds."""
    deadline = time.ticks_add(time.ticks_ms(), ms)
    seen = False

    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if mighty.boot_pressed():
            seen = True
        time.sleep_ms(10)

    if seen:
        while mighty.boot_pressed():
            time.sleep_ms(10)
        time.sleep_ms(DEBOUNCE_MS)

    return seen


def find_floor(mighty, screen):
    """Descend the duty until the panel reads as off, returning the last two."""
    print()
    print("Phase 1: the duty floor")
    print("Watch the panel. Press the user switch as soon as it reads as off.")
    print("Every step is held until you press or 3 seconds pass.")
    wait_for_press(mighty, "Press to start.")

    previous = None

    for duty in DUTIES:
        screen.brightness = duty
        print(f"  duty {duty * 100:7.3f}%  ({int(duty * 65535 + 0.5):5d} / 65535)")

        if pressed_since(mighty, 3000):
            return duty, previous

        previous = duty

    return None, DUTIES[-1]


def compare_gammas(mighty, screen):
    """Show equal control steps under each candidate gamma, for a judgement on
    whether the steps look evenly spaced."""
    print()
    print("Phase 2: do equal control steps look evenly spaced?")

    for gamma in GAMMAS:
        print()
        print(f"  gamma {gamma}")
        wait_for_press(mighty, "  Press to run this curve.")

        for control in STEPS:
            duty = pow(control, gamma)
            screen.brightness = duty
            print(f"    control {control:.1f} -> duty {duty * 100:7.3f}%")
            time.sleep_ms(1200)


def report(floor, last_visible):
    """What each candidate gamma does with a control range bounded by the floor."""
    print()
    print("Result")

    if floor is None:
        print(f"  The panel was still visible at {last_visible * 100:.4f}% duty,")
        print("  the lowest step. The floor is below the range swept.")
        bound = last_visible
    else:
        print(f"  Reads as off at   {floor * 100:.4f}% duty")
        print(f"  Last visible at   {last_visible * 100:.4f}% duty")
        bound = last_visible

    print()
    print("  What that costs each curve, as the control value reaching the")
    print("  lowest visible duty. Everything below it is wasted travel.")
    print()
    print("  gamma   control at floor   usable range")

    for gamma in GAMMAS:
        control = pow(bound, 1.0 / gamma)
        print(f"  {gamma:5.1f}   {control:16.3f}   {(1.0 - control) * 100:5.1f}%")


mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# A white frame, so the backlight is the only thing being judged
canvas = screen.canvas()
canvas.pen = color.white
canvas.clear()
screen.update(canvas)

try:
    floor, last_visible = find_floor(mighty, screen)
    compare_gammas(mighty, screen)
    report(floor, last_visible)

finally:
    screen.brightness = 1.0
    mighty.shutdown()
