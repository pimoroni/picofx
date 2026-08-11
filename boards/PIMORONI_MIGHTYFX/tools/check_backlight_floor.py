# Measures where the backlight stops holding a steady level, and prices what that
# floor costs each candidate curve. The floor is a property of the driver circuit, so
# it decides how much of a curve's control range is usable and no amount of arithmetic
# answers it.
#
# **The panel flickers before it goes dark**, measured on six 2.8" units where the
# weakest was unsteady at 1.72% duty and only extinguished at 1.50%. A minimum has to
# stay above the flicker, an unsteady panel being as unusable as a dark one, so the
# judgement asked for here is steadiness rather than visibility.
#
# The floor is a duty, so this tool steps duties and sets the backlight's own curve
# aside for the run. Phase 1 descends a coarse table until a panel stops being steady
# and phase 2 subdivides whatever bracket that left, so the figure is not held to the
# table's spacing. Every step waits on the user switch, a tap stepping down and a hold
# saying a panel has gone, so nothing is timed against a guess at how long a judgement
# takes.
#
# Which gamma to ship is a different question and check_backlight_gamma_ab.py is the
# tool for it, ramping two curves side by side on two panels instead of asking an eye
# to compare one against its memory of the last.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across
# to run it. Wiring: a 2.8" on SP/CE A, the same panel Tufty carries, or a hub of
# them with HUB set below. Every panel on a port shares its one BL line, so a hub
# sweeps that many units at once and the binding floor is the first to go: a shipped
# minimum has to keep the worst unit steady.

import time

from mighty_fx import SPCE, Backlight, MightyFX
from picovector import color
from screens import Screen280

# What a screen sets is a perceived brightness, raised to Backlight.GAMMA and then
# mapped above MINIMUM_DUTY before it reaches the pin. This tool is measuring where
# that floor belongs, so it takes both out and puts the numbers below straight on the
# pin, keeping the shipped gamma for the report. Set before the first screen, which is
# what builds the backlight.
SHIPPED_GAMMA = Backlight.GAMMA
Backlight.GAMMA = 1.0
Backlight.MINIMUM_DUTY = 0.0

# Whether SP/CE B gives its pins over as chip selects for a hub of panels on A, so
# every unit on it is swept together
HUB = True

# Descending duties for the floor hunt. Roughly logarithmic, and the range
# covers what the candidate gammas map their lower half onto: gamma 2.8 puts
# control 0.5 at 0.144 and control 0.1 at 0.0016.
DUTIES = (0.500, 0.300, 0.200, 0.144, 0.100, 0.070, 0.050, 0.035, 0.021,
          0.015, 0.010, 0.007, 0.005, 0.0035, 0.0021, 0.0016, 0.0010,
          0.0007, 0.0005, 0.0003, 0.0002, 0.0001)

# Steps phase 2 puts inside the coarse bracket, spaced geometrically as the coarse
# table is. Ten over one of its intervals resolves the floor to a few parts in a
# thousand of duty, which is finer than the eye's own hysteresis on the judgement.
REFINE_STEPS = 10

# Priced against the floor in the report. 1.0 is no curve at all, 2.2 is RGB_GAMMA,
# 2.8 is what Backlight ships and TinyFX's OUTPUT_GAMMA, 3.0 is the cube root that
# matches perceived lightness exactly.
GAMMAS = (1.0, 2.2, 2.8, 3.0)

# A press shorter than this is a bounce; a held switch repeats no faster
DEBOUNCE_MS = 200

# A press at least this long says the panel reads as off, where a tap moves on. Well
# clear of DEBOUNCE_MS, which every press already spends
LONG_PRESS_MS = 700


def wait_for_press(mighty, prompt):
    """Block until the user switch goes down, then comes back up."""
    print(prompt)

    while not mighty.boot_pressed():
        time.sleep_ms(10)

    time.sleep_ms(DEBOUNCE_MS)

    while mighty.boot_pressed():
        time.sleep_ms(10)

    time.sleep_ms(DEBOUNCE_MS)


def held_press(mighty):
    """Block until the switch is pressed, and say whether it was held.

    A tap steps on and a hold says this one reads as off, so every step waits for a
    judgement instead of a judgement racing a step.
    """
    while not mighty.boot_pressed():
        time.sleep_ms(10)

    down = time.ticks_ms()
    time.sleep_ms(DEBOUNCE_MS)

    while mighty.boot_pressed():
        time.sleep_ms(10)

    duration = time.ticks_diff(time.ticks_ms(), down)
    time.sleep_ms(DEBOUNCE_MS)

    return duration >= LONG_PRESS_MS


def find_floor(mighty, screen):
    """Descend the duty until a panel stops being steady, returning the last two."""
    print()
    print("Phase 1: the duty floor")
    print("Watch the panels. Tap the user switch to step down; hold it when the first")
    print("panel stops holding a steady level, flickering counting as gone. That unit")
    print("is the one a shipped minimum has to stay above. Every step waits for you.")
    wait_for_press(mighty, "Press to start.")

    previous = None

    for duty in DUTIES:
        screen.brightness(duty)
        print(f"  duty {duty * 100:7.3f}%  ({int(duty * 65535 + 0.5):5d} / 65535)")

        if held_press(mighty):
            return duty, previous

        previous = duty

    return None, DUTIES[-1]


def refine_floor(mighty, screen, floor, last_steady):
    """Subdivide the bracket the coarse sweep left, returning the closer pair."""
    if floor is None:
        print()
        print("Phase 2 skipped: every panel held steady to the bottom of the coarse")
        print("sweep, so there is no bracket to subdivide.")
        return floor, last_steady

    print()
    print("Phase 2: the same judgement, inside the coarse bracket")
    print(f"Between {last_steady * 100:.4f}% and {floor * 100:.4f}%, in {REFINE_STEPS} steps.")
    print("Tap to step down, hold again when the first panel stops being steady.")
    wait_for_press(mighty, "Press to start.")

    ratio = pow(floor / last_steady, 1.0 / REFINE_STEPS)
    previous = last_steady

    for step in range(1, REFINE_STEPS + 1):
        duty = last_steady * pow(ratio, step)
        screen.brightness(duty)
        print(f"  duty {duty * 100:7.4f}%  ({int(duty * 65535 + 0.5):5d} / 65535)")

        if held_press(mighty):
            return duty, previous

        previous = duty

    return floor, previous


def report(floor, last_steady):
    """What the floor costs each candidate curve, and what a minimum would reclaim."""
    print()
    print("Result")

    if floor is None:
        print(f"  Every panel held steady at {last_steady * 100:.4f}% duty, the lowest")
        print("  step. The floor is below the range swept.")
    else:
        print(f"  First unsteady at  {floor * 100:.4f}% duty")

    print(f"  Last steady at     {last_steady * 100:.4f}% duty"
          f"  ({int(last_steady * 65535 + 0.5)} / 65535)")

    print()
    print("  What that costs each curve, as the control value reaching the")
    print("  lowest steady duty. Everything below it is wasted travel.")
    print()
    print("  gamma   control at floor   usable range")

    for gamma in GAMMAS:
        control = pow(last_steady, 1.0 / gamma)
        print(f"  {gamma:5.1f}   {control:16.3f}   {(1.0 - control) * 100:5.1f}%")

    # The reason the floor is worth measuring: it is the constant a minimum setting
    # would map onto, which turns the wasted travel above back into control range
    low = pow(last_steady, 1.0 / SHIPPED_GAMMA)
    print()
    print(f"  A minimum putting control 0.0 at {last_steady * 100:.4f}% reclaims that")
    print(f"  travel. At the shipped gamma {SHIPPED_GAMMA}, the range would then read:")
    print()
    print("  control   duty")

    for control in (0.0, 0.25, 0.5, 0.75, 1.0):
        duty = pow(low + control * (1.0 - low), SHIPPED_GAMMA)
        print(f"  {control:7.2f}   {duty * 100:8.4f}%  ({int(duty * 65535 + 0.5):5d} / 65535)")


mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_LINES if HUB else None)
if HUB:
    screens = [Screen280(port) for port in mighty.hub_ports]
else:
    screens = [Screen280(mighty.spce_a)]

screen = screens[0]
print(f"sweeping {len(screens)} panel(s) on one BL line")

# A white frame on every panel, so the backlight is the only thing being judged. The
# background fills what the source does not cover, so a small canvas paints the lot
# and no panel-sized one is claimed
patch = screen.canvas(8, 8)
patch.pen = color.white
patch.clear()
for panel in screens:
    panel.update(patch, bg_color=color.white)

try:
    floor, last_steady = find_floor(mighty, screen)
    floor, last_steady = refine_floor(mighty, screen, floor, last_steady)
    report(floor, last_steady)

finally:
    screen.brightness(1.0)
    mighty.shutdown()
