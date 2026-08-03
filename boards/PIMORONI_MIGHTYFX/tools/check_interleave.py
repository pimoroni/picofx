# Exercises the interleaver against sequential updates on two live screens,
# reporting worst-case stats per phase while showing the check_tearing.py grid,
# so one run serves the numbers and the eyes together.
#
# Reports, per phase: worst frame time against the wire-bound expectation (a
# stretched frame means the wire starved), write-start skew, TE waits and
# te_timeouts. Acceptance for the interleaved phases is frames still wire-bound,
# zero TE timeouts, and skew collapsed from a frame time to the TE phase offset.
# On the glass, a torn frame shows as a horizontal band of the previous
# background colour across the grid, and out-of-step panels show different
# colours outright.
#
# The PSRAM phases run first, on screens staged as deep as each rotation
# measures wire-bound needing: 80 rows for rotation 0, and 160 rows with
# 12-column cache windows for rotation 90, whose conversion runs ~106us/row
# against the 131.3us wire row. Neither claim can coexist with a full SRAM
# canvas, so the screens are rebuilt unstaged before the canvas is created,
# keeping the screens-before-canvas claim order.
#
# A diagnostic, not an example, so it is not copied to the board. Run it with
# mpremote against a board carrying the update_all firmware.

import gc
import time

import spidisplay
from mighty_fx import SPCE, MightyFX
from picovector import color, image
from screens import Screen280

PHASE_MS = 15_000
GRID_PITCH = 20
BACKGROUNDS = (color.rgb(127, 127, 127), color.rgb(34, 177, 76))
PSRAM_STAGE_LINES = 80
R90_STAGE_LINES = 160
R90_CACHE_COLUMNS = 12
UINT32 = 0xFFFFFFFF


def draw(canvas, background):
    canvas.pen = background
    canvas.clear()
    canvas.pen = color.rgb(0, 0, 0)
    for x in range(0, canvas.width, GRID_PITCH):
        canvas.rectangle(x, 0, 1, canvas.height)
    for y in range(0, canvas.height, GRID_PITCH):
        canvas.rectangle(0, y, canvas.width, 1)


def skew_us(a, b):
    d = (b - a) & UINT32
    return min(d, UINT32 + 1 - d)


def build(stage_lines, cache_columns=None):
    mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
    screens = (Screen280(mighty.spce_a, stage_lines=stage_lines,
                         cache_columns=cache_columns),
               Screen280(mighty.spce_b, stage_lines=stage_lines,
                         cache_columns=cache_columns))
    return mighty, screens


def run_phase(label, screens, step_fn):
    displays = [s.display for s in screens]
    print(label)
    timeouts0 = [d.te_timeouts() for d in displays]
    worst = [{"convert": 0, "stall": 0, "frame": 0, "te": 0} for _ in displays]
    worst_skew = 0
    frames = 0
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < PHASE_MS:
        step_fn(frames)
        frames += 1
        stats = [d.stats() for d in displays]
        for i, s in enumerate(stats):
            w = worst[i]
            w["convert"] = max(w["convert"], s.convert_total_us)
            w["stall"] = max(w["stall"], s.stall_us)
            w["frame"] = max(w["frame"], s.frame_us)
            w["te"] = max(w["te"], s.te_wait_us)
        worst_skew = max(worst_skew, skew_us(stats[0].write_start_us,
                                             stats[1].write_start_us))
    pair_ms = time.ticks_diff(time.ticks_ms(), t0) // frames
    for i, w in enumerate(worst):
        print("  screen {}: frame {}us  convert {}us  stall {}us  te_wait {}us".format(
            i, w["frame"], w["convert"], w["stall"], w["te"]))
    print("  worst skew {}us  pair {}ms/frame  te_timeouts {}".format(
        worst_skew, pair_ms,
        [d.te_timeouts() - t for d, t in zip(displays, timeouts0)]))
    print()


# PSRAM phases: staged screens, no SRAM canvas.
mighty, screens = build(PSRAM_STAGE_LINES)
displays = [s.display for s in screens]

WIDTH, HEIGHT = screens[0].width, screens[0].height
ROW_BYTES = WIDTH * 3 // 2 if screens[0].bitdepth == 12 else WIDTH * 2
print("panels: {}x{} at {}bpp, band {} rows, baud {}".format(
    WIDTH, HEIGHT, screens[0].bitdepth, displays[0].band_rows(),
    displays[0].baudrate()))
print("wire-bound frame: {}us".format(
    HEIGHT * ROW_BYTES * 8 * 1_000_000 // displays[0].baudrate()))
print()

psram_canvases = []
for bg in BACKGROUNDS:
    c = image(WIDTH, HEIGHT)
    draw(c, bg)
    psram_canvases.append(c)


psram_wide = []
for bg in BACKGROUNDS:
    c = image(HEIGHT, WIDTH)
    draw(c, bg)
    psram_wide.append(c)


def sequential_psram(t):
    canvas = psram_canvases[t % 2]
    for screen in screens:
        screen.update(canvas, rotation=0)


def sequential_psram_r90(t):
    canvas = psram_wide[t % 2]
    for screen in screens:
        screen.update(canvas, rotation=90)


def interleaved_psram_r90(t):
    canvas = psram_wide[t % 2]
    for d in displays:
        d.prepare(canvas, rotation=90)
    spidisplay.update_all(displays[0], displays[1], v_sync=True)
    for s in screens:
        s.drawn()


def interleaved_psram(t):
    canvas = psram_canvases[t % 2]
    for d in displays:
        d.prepare(canvas, rotation=0)
    spidisplay.update_all(displays[0], displays[1], v_sync=True)
    # update_all() bypasses ScreenBase.update(), whose drawn() is what lets
    # the backlight turn on once real content is up.
    for s in screens:
        s.drawn()


run_phase("sequential PSRAM rot0: panels flip colours out of step (the fault)",
          screens, sequential_psram)
run_phase("interleaved PSRAM rot0, staged {}: panels flip together; expect no"
          " tear band".format(PSRAM_STAGE_LINES), screens, interleaved_psram)

# Rotation 90 needs the deeper recipe: rebuild before its phases.
mighty.shutdown()
del mighty, screens, displays
gc.collect()
mighty, screens = build(R90_STAGE_LINES, R90_CACHE_COLUMNS)
displays = [s.display for s in screens]

run_phase("sequential PSRAM rot90: tear-free reference, pronounced ping-pong",
          screens, sequential_psram_r90)
run_phase("interleaved PSRAM rot90, staged {} cache {}: panels flip together;"
          " expect no tear band".format(R90_STAGE_LINES, R90_CACHE_COLUMNS),
          screens, interleaved_psram_r90)

# SRAM phase: unstaged screens rebuilt first, then the canvas, so the canvas
# sits below the workspace claims.
mighty.shutdown()
del mighty, screens, displays
gc.collect()
mighty, screens = build(0)
displays = [s.display for s in screens]
sram_canvas = image(HEIGHT, WIDTH, spidisplay.buffer(HEIGHT * WIDTH * 4))


def interleaved_sram(t):
    draw(sram_canvas, BACKGROUNDS[t % 2])
    for d in displays:
        d.prepare(sram_canvas, rotation=90)
    spidisplay.update_all(displays[0], displays[1], v_sync=True)
    for s in screens:
        s.drawn()


run_phase("interleaved SRAM rot90: panels flip together; expect no tear band",
          screens, interleaved_sram)

# command() refusal and abort_frame() recovery.
displays[0].prepare(sram_canvas, rotation=90)
try:
    displays[0].command(0x2C)
    print("command on staged frame: NOT refused (wrong)")
except ValueError as e:
    print("command on staged frame refused:", e)
displays[0].abort_frame()
screens[0].update(sram_canvas, rotation=90)
print("abort_frame then update: ok")
print("done")
