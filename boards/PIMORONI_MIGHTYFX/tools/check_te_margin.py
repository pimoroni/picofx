# Measures each panel's real refresh period from its TE line and reports the
# tear margin left over a measured frame, per panel. The FRCTRL2 setting picks
# a divider of the panel's internal oscillator, and oscillators vary per unit,
# so two panels at one setting can hold different margins: a small or negative
# one shows as a marginal tear wobbling in and out on that panel alone.
#
# A diagnostic, not an example, so it is not copied to the board. Run it with
# mpremote.

import spidisplay
import st7789
from mighty_fx import SPCE, MightyFX
from picovector import image
from screens import Screen280

PROBE_MS = 1000

# v_sync off so frame_us is the pure pipeline; te stays on for the probe.
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
screens = (Screen280(mighty.spce_a, v_sync=False),
           Screen280(mighty.spce_b, v_sync=False))
labels = ("SP/CE A", "SP/CE B")

WIDTH, HEIGHT = screens[0].width, screens[0].height
canvas = image(HEIGHT, WIDTH, spidisplay.buffer(HEIGHT * WIDTH * 4))

nominal = screens[0].framerate if hasattr(screens[0], "framerate") else 46
print("FRCTRL2 steps:", sorted(st7789.FRAME_RATE_CONTROL))
print("nominal rate: {}fps, nominal two-refresh budget: {}us".format(
    nominal, 2_000_000 // nominal))
print()

for label, screen in zip(labels, screens):
    display = screen.display
    screen.update(canvas, rotation=90)   # warm
    screen.update(canvas, rotation=90)
    frame_us = display.stats().frame_us

    probe = display.te_probe(PROBE_MS)
    period_us, high_us, edges = probe
    if edges < 2:
        print("{}: TE silent ({} edges)".format(label, edges))
        continue

    actual_fps = 1_000_000 / period_us
    budget_us = 2 * period_us     # the 240x320 shows every scanned line
    margin_us = budget_us - frame_us
    print("{}: TE period {}us ({:.2f}fps actual), high {}us, {} edges".format(
        label, period_us, actual_fps, high_us, edges))
    print("   frame {}us against budget {}us: margin {}us ({:.1f}% of budget)".format(
        frame_us, budget_us, margin_us, 100 * margin_us / budget_us))
    print()
