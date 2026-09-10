# Visual gamma check for the 1.54" panel. st7789.setup() writes pimoroni-pico's
# 320x240 tuning to every panel, so this one has never had that driver's own 240x240
# values. Gamma changes light output and not any pixel value, so nothing can be read
# back and the comparison has to be two panels side by side.
#
# Stage 0 writes a third real curve, to prove a gamma write after DISPON reaches the
# panel at all. Stages 1 to 4 then compare, swapping the tuning between the panels so
# a difference following the tuning is told apart from one following the panel or the
# port. Each panel counts its own tuning in white squares, so the console is never
# needed to tell them apart: one for shipped, two for square, three for the probe.
#
# The boot button advances a stage, and the legend prints at the end. A diagnostic,
# not an example, so it is not copied to the board. Copy it across to run it. Wiring:
# a 1.54" on each SP/CE port.

import machine
import time

import st7789
from mighty_fx import SPCE, MightyFX
from picovector import color, image
from screens import Screen154

# 16-bit, RGB444 holding sixteen levels a channel where gamma moves the panel in steps
# finer than that
BAUDRATE = 37_500_000
BITDEPTH = 16

RAMP_STEPS = 24
LOW_CEILING = 48        # Where the low ramps stop, the curve being steepest near black
MARKER_SIZE = 10

# What st7789.setup() writes today, being pimoroni-pico's 320x240 set
SHIPPED = ((st7789.REG_GCTRL, b"\x35"),
           (st7789.REG_VCOMS, b"\x1f"),
           (st7789.REG_GMCTRP1, b"\xD0\x08\x11\x08\x0C\x15\x39\x33\x50\x36\x13\x14\x29\x2D"),
           (st7789.REG_GMCTRN1, b"\xD0\x08\x10\x08\x06\x06\x39\x44\x51\x0B\x16\x14\x2F\x31"))

# The same driver's 240x240 set, which this panel never receives today
SQUARE = ((st7789.REG_GCTRL, b"\x14"),
          (st7789.REG_VCOMS, b"\x37"),
          (st7789.REG_GMCTRP1, b"\xD0\x04\x0D\x11\x13\x2B\x3F\x54\x4C\x18\x0D\x0B\x1F\x23"),
          (st7789.REG_GMCTRN1, b"\xD0\x04\x0C\x11\x13\x2C\x3F\x44\x51\x2F\x1F\x1F\x20\x23"))

# The 240x135 set, a real curve for a panel this is not, so stage 0's write shows
# without sending a value no driver ships
PROBE = ((st7789.REG_VRHS, b"\x00"),
         (st7789.REG_GCTRL, b"\x75"),
         (st7789.REG_VCOMS, b"\x3D"),
         (st7789.REG_GMCTRP1, b"\x70\x04\x08\x09\x09\x05\x2A\x33\x41\x07\x13\x13\x29\x2f"),
         (st7789.REG_GMCTRN1, b"\x70\x03\x09\x0A\x09\x06\x2B\x34\x41\x07\x12\x14\x28\x2E"))

MARKERS = {SHIPPED: 1, SQUARE: 2, PROBE: 3}
NAMES = {SHIPPED: "shipped", SQUARE: "square", PROBE: "probe"}

# Stage 0 first, then the four that compare. The last two are what separate a tuning
# from a panel, since two units differ from each other whatever the curve
STAGES = ((PROBE, SHIPPED),
          (SHIPPED, SHIPPED),
          (SQUARE, SQUARE),
          (SHIPPED, SQUARE),
          (SQUARE, SHIPPED))


def write_tuning(screen, tuning):
    for register, payload in tuning:
        screen.__command(register, payload)


def draw(canvas, width, height, markers):
    # A black reference field carrying the markers, then the full range, then the
    # bottom of it in grey and in green, where the banding this tuning was chosen
    # against shows
    canvas.pen = color.rgb(0, 0, 0)
    canvas.clear()

    band = height // 4
    step = width // RAMP_STEPS
    for index in range(RAMP_STEPS):
        x = index * step
        full = index * 255 // (RAMP_STEPS - 1)
        low = index * LOW_CEILING // (RAMP_STEPS - 1)
        canvas.pen = color.rgb(full, full, full)
        canvas.rectangle(x, band, step, band)
        canvas.pen = color.rgb(low, low, low)
        canvas.rectangle(x, band * 2, step, band)
        canvas.pen = color.rgb(0, low, 0)
        canvas.rectangle(x, band * 3, step, band)

    # Counted rather than coloured, so the marker reads the same under either curve
    canvas.pen = color.rgb(255, 255, 255)
    for marker in range(markers):
        canvas.rectangle(4 + marker * (MARKER_SIZE + 6), 4, MARKER_SIZE, MARKER_SIZE)


def wait_for_press():
    # Both edges, so one press advances one stage
    while not mighty.boot_pressed():
        time.sleep_ms(20)
    while mighty.boot_pressed():
        time.sleep_ms(20)


machine.freq(150_000_000, 150_000_000)
time.sleep(0.02)

mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
screens = (Screen154(mighty.spce_a, baudrate=BAUDRATE, bitdepth=BITDEPTH),
           Screen154(mighty.spce_b, baudrate=BAUDRATE, bitdepth=BITDEPTH))

# One canvas redrawn per panel, two full-size claims not fitting the region together.
# Nothing here is timed, so the redraw costs nothing that matters
try:
    canvas = screens[0].canvas()
except ValueError:
    canvas = image(screens[0].width, screens[0].height)

for tunings in STAGES:
    for screen, tuning in zip(screens, tunings):
        write_tuning(screen, tuning)
        draw(canvas, screen.width, screen.height, MARKERS[tuning])
        screen.update(canvas)
    wait_for_press()

mighty.shutdown()

print("Stages shown, SP/CE A then B:")
for index, tunings in enumerate(STAGES):
    print(f"  {index}  A {NAMES[tunings[0]]:<8} B {NAMES[tunings[1]]}")
print("One white square is the shipped tuning, two is square, three is the probe.")
print("Stage 0 tells you whether a gamma write after DISPON lands at all. If A looked")
print("no different from B there, the registers are reset-only and stages 1 to 4 mean")
print("nothing, so they have to be run by rebuilding each panel instead.")
