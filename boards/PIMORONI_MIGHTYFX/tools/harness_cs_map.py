# Maps a hub or harness: which panel sits on which chip select, and which type each
# one is. Every candidate CS is painted its own colour with its own count of black
# bars and left lit, so the whole harness reads off the glass in one look.
#
# Run once as Screen280 to find which lines are populated: a 2.8" fills, and a 1.54"
# takes the top 240 rows and drops the rest. Run again as Screen154 to sort the
# types, a 2.8" leaving its bottom 80 rows unwritten where a 1.54" fills cleanly.
#
# Needs no diodes and no TE, every panel coming up te=False. Boot button exits.
# A diagnostic, not an example, so it is not copied to the board.

import time
from machine import Pin
import screens
from mighty_fx import MightyFX, SPCE
from picovector import color, image

EXTRA_CS = (24, 25, 26, 27, 37)         # Every CS beyond SP/CE A's own; an empty line stays dark
SCREEN_CLASS = screens.Screen280        # Run once as each
BAUDRATE = 24_000_000
BAR_PITCH = 26

PALETTE = (("red", (255, 0, 0)),
           ("green", (0, 220, 0)),
           ("blue", (60, 110, 255)),
           ("yellow", (255, 200, 0)),
           ("magenta", (255, 0, 190)),
           ("cyan", (0, 220, 220)))

mighty = MightyFX(spce_a=SPCE.SCREEN)
port = mighty.spce_a

# A panel not yet built reads its floating CS as asserted and takes another panel's
# bringup, so every candidate is driven high first. Only a run from reset tests this.
for candidate in (33,) + EXTRA_CS:
    Pin(candidate, Pin.OUT, value=1)

panels = [SCREEN_CLASS(port, te=False, baudrate=BAUDRATE)]
panels += [SCREEN_CLASS(port, cs=Pin(n), dc=port.dc, te=False, baudrate=BAUDRATE)
           for n in EXTRA_CS]
labels = (33,) + EXTRA_CS
panels[0].brightness(1.0)
# Many band claims can leave no room for an SRAM canvas; nothing here is timed
try:
    canvas = panels[0].canvas()
except ValueError:
    canvas = image(panels[0].width, panels[0].height)
    print("SRAM canvas did not fit; using a PSRAM image")

try:
    print(f"{len(panels)} candidate CS lines as {SCREEN_CLASS.__name__}"
          f" ({panels[0].width}x{panels[0].height}), painted one identity each.\n")
    print("  CS   colour    bars")
    for index, screen in enumerate(panels):
        name, rgb = PALETTE[index % len(PALETTE)]
        canvas.pen = color.rgb(*rgb)
        canvas.clear()
        canvas.pen = color.rgb(0, 0, 0)
        for bar in range(index + 1):
            canvas.rectangle(10 + bar * BAR_PITCH, 10, 14, 44)
        screen.update(canvas)
        print(f"  {labels[index]:<4} {name:<9} {index + 1}")

    print("\nEvery panel matching this geometry is now lit and stays lit.")
    print("Filled cleanly = this geometry. Fragment or noise = the other pass.")
    print("A candidate with no panel on it stays dark. Boot button exits.")

    while not mighty.boot_pressed():
        time.sleep_ms(100)

finally:
    mighty.shutdown()
