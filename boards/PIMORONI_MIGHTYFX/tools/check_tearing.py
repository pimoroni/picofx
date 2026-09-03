# Visual tearing check for every profile row, at the worst case the profiles were
# chosen against: rotation 90 from a PSRAM source, v_sync on. Backgrounds alternate,
# so a torn frame shows as a horizontal band of the previous colour across the grid.
# The printed margin is what the two-refresh budget holds beyond the measured frame.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across
# to run it. Wiring: a 2.8" on SP/CE A and a 1.54" on SP/CE B.

import gc
import machine
import time

import spidisplay
import st7789
from mighty_fx import SPCE, MightyFX
from picovector import color, image
from screens import Screen154, Screen280

# Added to each profile's frame rate, then snapped to the controller's nearest
# step (printed per case). Positive offsets shrink the margin, so raising this
# until a band appears finds each panel's real tearing onset; 0 checks the
# profiles as shipped.
FPS_OFFSET = 1

SECONDS_PER_CASE = 5
FRAMES_PER_BACKGROUND = 1
BACKGROUNDS = (color.rgb(127, 127, 127), color.rgb(34, 177, 76))
GRID_PITCH = 20

CLOCKS = {
    24_000_000: (150_000_000, 48_000_000),
    37_500_000: (150_000_000, 150_000_000),
    75_000_000: (150_000_000, 150_000_000),
}

# No (75MHz, 12bpp): that wire outruns the panel's scan whatever the band and cache choice
CASES = ((24_000_000, 12), (37_500_000, 16), (37_500_000, 12),
         (75_000_000, 16))

STATS = ("convert_us", "te_wait_us", "frame_us")


def offset_rate(screen_class, baud, depth):
    # The profile's rate plus FPS_OFFSET, snapped to a controller step, read through
    # the row's dual-core replacement where this firmware has one
    row = screen_class.PROFILES[(baud, depth)]
    if spidisplay.dual_convert() and "dual" in row:
        row = row["dual"]
    wanted = row["framerate"] + FPS_OFFSET
    return min(st7789.FRAME_RATE_CONTROL, key=lambda step: abs(step - wanted))


def draw(canvas, width, height, background):
    canvas.pen = background
    canvas.clear()
    canvas.pen = color.rgb(0, 0, 0)
    for x in range(0, width, GRID_PITCH):
        canvas.rectangle(x, 0, 1, height)
    for y in range(0, height, GRID_PITCH):
        canvas.rectangle(0, y, width, 1)


def sources(screen):
    # Rotation 90 swaps the axes, so the source fills the turned panel
    width, height = screen.height, screen.width
    canvases = []
    for background in BACKGROUNDS:
        canvas = image(width, height)
        draw(canvas, width, height, background)
        canvases.append(canvas)
    return canvases


for baud, depth in CASES:
    sys_hz, peri_hz = CLOCKS[baud]
    machine.freq(sys_hz, peri_hz)
    time.sleep(0.02)

    mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
    screens = (Screen280(mighty.spce_a, baudrate=baud, bitdepth=depth,
                         framerate=offset_rate(Screen280, baud, depth)),
               Screen154(mighty.spce_b, baudrate=baud, bitdepth=depth,
                         framerate=offset_rate(Screen154, baud, depth)))
    canvases = [sources(screen) for screen in screens]

    print(f"\n{baud // 1_000_000}MHz {depth}bpp, offset {FPS_OFFSET:+}:"
          f" 280 at {screens[0].framerate}fps band {screens[0].__display.band_rows()}"
          f" | 154 at {screens[1].framerate}fps band {screens[1].__display.band_rows()},"
          f" v_sync on, rotation 90")

    totals = [dict.fromkeys(STATS, 0) for _ in screens]
    frames = 0
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < SECONDS_PER_CASE * 1000:
        if mighty.boot_pressed():
            raise KeyboardInterrupt
        which = (frames // FRAMES_PER_BACKGROUND) % 2
        for screen, pair, total in zip(screens, canvases, totals):
            screen.update(pair[which], rotation=90)
            stats = screen.__display.stats()
            for field in STATS:
                total[field] += getattr(stats, field)
        frames += 1
    elapsed_ms = time.ticks_diff(time.ticks_ms(), t0)

    print(f"  {frames} frame pairs in {elapsed_ms}ms,"
          f" {frames * 1000 / elapsed_ms:.1f} pair-updates/s")
    for screen, total in zip(screens, totals):
        budget = 2_000_000 // screen.framerate
        frame = total["frame_us"] // frames
        first = total["convert_us"] // frames
        margin = budget - first - frame
        print(f"  {screen.width}x{screen.height}: first {first}us"
              f" + frame {frame}us against the {budget}us two-refresh budget,"
              f" margin {margin}us, te_wait {total['te_wait_us'] // frames}us")

    mighty.shutdown()
    gc.collect()

machine.freq(150_000_000, 48_000_000)
print("\ndone: panels off. Any horizontal band of the previous colour was a tear.")
