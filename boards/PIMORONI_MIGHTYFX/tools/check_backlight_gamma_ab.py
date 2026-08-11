# Compares backlight gamma curves side by side, two panels ramping together
# from one control value.
#
# A continuous rise and fall, not steps: a curve that is wrong shows as a rush
# at one end and a crawl at the other, which stepping hides by asking the eye to
# compare against memory.
#
# Each panel prints the curve it is running, so the comparison needs no console.
# The first pair runs the same gamma on both, which is the null test: any
# difference there is the two units, not the curves. Close pairs then run twice
# with the sides swapped, so unit variation cancels instead of being mistaken
# for a result.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across
# to run it. Wiring: a 2.8" on SP/CE A and a second 2.8" on SP/CE B.

import time

from mighty_fx import SPCE, Backlight, MightyFX
from picovector import color, font
from screens import Screen280

# Each curve below is applied here, so the backlight must apply none of its own: both
# its gamma and the floor it maps a setting above come out for the run, leaving what
# this tool asks for on the pin. Set before the first screen, which is what builds the
# backlight.
Backlight.GAMMA = 1.0
Backlight.MINIMUM_DUTY = 0.0

# (gamma on A, gamma on B). 1.0 is no curve at all, 2.2 is RGB_GAMMA, 2.8 is what
# Backlight ships and TinyFX's OUTPUT_GAMMA, 3.0 is the cube root that matches
# perceived lightness. 3.0 is the reference every other curve is measured against.
PAIRS = ((3.0, 3.0),
         (1.0, 3.0),
         (2.2, 3.0),
         (3.0, 2.2),
         (2.8, 3.0),
         (3.0, 2.8))

# One full rise and fall. Slow enough that the shape of the curve is visible
# rather than a flicker, short enough to watch several without losing patience.
RAMP_PERIOD_MS = 8000

# How long the labels sit at full brightness before the ramp starts
LABEL_MS = 1500

LABEL_SCALE = 4
MARGIN = 12

DEBOUNCE_MS = 200


def await_release(mighty):
    """Swallow the press that ended a ramp, so it cannot end the next one."""
    time.sleep_ms(DEBOUNCE_MS)

    while mighty.boot_pressed():
        time.sleep_ms(10)

    time.sleep_ms(DEBOUNCE_MS)


def show_labels(screens, canvas, pair):
    """Name each panel and the curve it is about to run, on the panel itself."""
    for screen, gamma, name in zip(screens, pair, ("A", "B")):
        canvas.pen = color.white
        canvas.clear()
        canvas.pen = color.black
        canvas.font = font.ark
        canvas.text(name, MARGIN, MARGIN, LABEL_SCALE)
        canvas.text(f"gamma {gamma}", MARGIN, MARGIN + 60, LABEL_SCALE)
        screen.update(canvas)
        screen.brightness(1.0)

    time.sleep_ms(LABEL_MS)


def ramp_until_pressed(mighty, screens, pair):
    """Triangle-ramp one control value through both curves until the switch goes."""
    half = RAMP_PERIOD_MS // 2
    start = time.ticks_ms()

    while not mighty.boot_pressed():
        elapsed = time.ticks_diff(time.ticks_ms(), start) % RAMP_PERIOD_MS
        control = elapsed / half if elapsed < half else (RAMP_PERIOD_MS - elapsed) / half
        control = min(1.0, max(0.0, control))

        for screen, gamma in zip(screens, pair):
            screen.brightness(pow(control, gamma))

        time.sleep_ms(20)

    await_release(mighty)


mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
screens = (Screen280(mighty.spce_a), Screen280(mighty.spce_b))

# One canvas, redrawn per panel. Two full canvases do not fit alongside two
# screens, and the content is static once a pair has started
canvas = screens[0].canvas()

print("Watch both panels. Press the user switch to move to the next pair.")
print(f"{len(PAIRS)} pairs, each a continuous rise and fall over {RAMP_PERIOD_MS / 1000:.0f}s.")

try:
    for index, pair in enumerate(PAIRS, 1):
        label = "null test, both the same" if pair[0] == pair[1] else ""
        print(f"  {index}/{len(PAIRS)}  A gamma {pair[0]}   B gamma {pair[1]}   {label}")

        show_labels(screens, canvas, pair)
        ramp_until_pressed(mighty, screens, pair)

    print("Done.")

finally:
    for screen in screens:
        screen.brightness(1.0)
    mighty.shutdown()
