# Sweeps the screen settings that decide frame time and records every cell, which is
# how a panel's PROFILES rows are measured.
#
# Bit depth, frame rate, baud rate, band lines and cache columns are fixed when a
# Screen is built; rotation, mirror and pixel doubling change between frames. A new
# Screen needs a new MightyFX, so the sweep is ordered to rebuild as rarely as it can.
#
# A diagnostic, not an example, so it is not copied to the board. It appends one JSON
# object per cell to RESULTS_FILE, and CHECKPOINT_FILE resumes an interrupted run. A
# checkpoint indexes the settings matrix, so changing any axis mid-run is refused.
# Hold the boot button to stop.

import gc
import json
import machine
import time

import spidisplay
from mighty_fx import SPCE, MightyFX
from picovector import color, image
from screens import Screen154, Screen280

RESULTS_FILE = "/profile_rerun_results.jsonl"
CHECKPOINT_FILE = "/profile_rerun_checkpoint.json"

WARMUP_FRAMES = 2
MEASURE_FRAMES = 6

START_DELAY_S = 2       # Time to interrupt before the sweep takes the REPL

# A machine reset after this many groups, 0 for never. The fallback if a run still
# runs out of DMA channels despite collecting at every group; only resumes on its own
# if this is staged as main.py.
RESET_EVERY_GROUPS = 0
NOMINAL_FRAME_MS = 30   # Only to size the run up front, not used in any result
# One probe per group, for the panel's real refresh rate; a short window reads about 10% low
TE_PROBE_MS = 1000

# Each panel names the SP/CE port it is wired to, so two sizes sweep in one run
PANELS = (("240x240", Screen154, "b"), ("240x320", Screen280, "a"))
BITDEPTHS = (12, 16)
FRAMERATES = (None,)    # None takes the profile's rate for the wire under test
BAUDRATES = (24_000_000, 37_500_000, 75_000_000)
# Values that divide the panel heights and width, so no cell measures a ragged last
# band or window; 24 band lines is the ceiling despite not dividing 320. Each cell
# claims its band ring and cache from SRAM, so the ceilings are also a spend per cell.
BAND_LINES = (1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24)
CACHE_COLUMNS = (0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24)

# Changed between frames, so these sweep inside one construction. Rotation 0, 180 and
# 90 read rows forward, in reverse and by column, the three distinct costs; a mirror
# only swaps a frame between the first two.
ROTATIONS = (0, 90, 180)
MIRRORS = (False,)
SOURCES = ("psram",)# "sram")

PIXEL_DOUBLE = (False, True)

# clk_sys and clk_peri each baud rate needs; the PL022 divides clk_peri by at least two
CLOCKS = {
    24_000_000: (150_000_000, 48_000_000),
    37_500_000: (150_000_000, 150_000_000),
    75_000_000: (150_000_000, 150_000_000),
}

V_SYNC = False          # Off, so a pass times the conversion and the wire alone

# The source is drawn, not loaded, so a run cannot be skewed by whatever images are
# staged. Backgrounds cycle so a torn frame shows as a band of the previous colour,
# one canvas prebuilt per background since a draw costs about as much as a frame.
BACKGROUNDS = (color.rgb(127, 127, 127), color.rgb(34, 177, 76))
SRAM_BACKGROUND = (color.rgb(34, 76, 177))
FRAMES_PER_BACKGROUND = 2

GRID_PITCH = 20         # Hairline spacing, so a stride error tilts the verticals
CORNER_MARK = 20        # Chiral corner marks, naming the rotation and the mirror

STAT_FIELDS = ("pre_us", "convert_us", "te_wait_us", "frame_us",
               "convert_total_us", "stall_us", "write_start_us")

PANEL_CLASSES = {name: panel for name, panel, _ in PANELS}
PANEL_PORTS = {name: port for name, _, port in PANELS}


def load_checkpoint(shape):
    """Where to resume, refusing a checkpoint written against a different matrix.

    An index only means anything against the axes it was written for, so a changed
    axis silently moves every later cell. The recorded settings on each row stay
    truthful either way, but the sweep would skip and repeat cells at random.
    """
    try:
        with open(CHECKPOINT_FILE) as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return 0

    if saved.get("shape") != list(shape):
        raise SystemExit(
            f"{CHECKPOINT_FILE} was written for a matrix of {saved.get('shape')} and the"
            f" axes now give {list(shape)}. Delete it and {RESULTS_FILE} to start again,"
            f" or put the axes back to finish the run.")

    return saved.get("next_index", 0)


def save_checkpoint(index, shape):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"next_index": index, "shape": list(shape)}, f)


def append_result(row):
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(row))
        f.write("\n")


# The axes in nesting order, outermost first, so the construction-fixed settings
# change least often. The first GROUP_AXES of them are what a Screen is built with.
AXES = (
    tuple(name for name, _, _ in PANELS),
    BITDEPTHS,
    FRAMERATES,
    BAUDRATES,
    BAND_LINES,
    CACHE_COLUMNS,
    ROTATIONS,
    MIRRORS,
    SOURCES,
    PIXEL_DOUBLE,
)
GROUP_AXES = 6


def __extent(axes):
    total = 1
    for axis in axes:
        total *= len(axis)
    return total


CELLS = __extent(AXES)
CELLS_PER_GROUP = __extent(AXES[GROUP_AXES:])
GROUPS = __extent(AXES[:GROUP_AXES])

# The axis lengths a cell index is decoded against, stored with a checkpoint so a
# resume notices a changed matrix
MATRIX_SHAPE = tuple(len(axis) for axis in AXES)


def cell_at(index):
    """Decode a cell index into its settings, treating the axes as mixed radix.

    Nothing is materialised, so adding an axis costs no time or memory up front and
    a resume jumps straight to its cell. The last axis varies fastest, which is the
    ordering the nested loops this replaces produced.
    """
    values = [None] * len(AXES)
    for position in range(len(AXES) - 1, -1, -1):
        axis = AXES[position]
        values[position] = axis[index % len(axis)]
        index //= len(axis)

    group = tuple(values[:GROUP_AXES])
    rotation, mirror, source, pixel_double = values[GROUP_AXES:]
    return group, rotation, source, mirror, pixel_double


def unshippable(bitdepth, baudrate):
    # 16 bits at 24MHz puts a 240x320 frame under the ST7789's 39fps floor, so it cannot ship
    return bitdepth == 16 and baudrate == 24_000_000


def source_size(screen, rotation):
    """A source that fills the panel once turned, so no cell measures a letterbox."""
    if rotation in (90, 270):
        return screen.height, screen.width

    return screen.width, screen.height


def draw(canvas, width, height, background):
    """A deterministic pattern, so a cell's cost is the settings and not the source.

    Conversion is content independent, so the pattern is here to be read by eye
    while a sweep runs: the hairlines show skew, the diagonal shows a cumulative
    offset as a kink, and the corner marks name the rotation and mirror.
    """
    canvas.pen = background
    canvas.clear()

    canvas.pen = color.black
    for x in range(0, width, GRID_PITCH):
        canvas.rectangle(x, 0, 1, height)
    for y in range(0, height, GRID_PITCH):
        canvas.rectangle(0, y, width, 1)

    canvas.pen = color.yellow
    canvas.line(0, 0, width - 1, height - 1, 2)

    canvas.pen = color.red
    canvas.rectangle(0, 0, CORNER_MARK, CORNER_MARK)
    canvas.pen = color.green
    canvas.circle(width - CORNER_MARK // 2, CORNER_MARK // 2, CORNER_MARK // 2)


# Sources are built once per shape and kept: every SRAM canvas aliases the same
# address, so a fresh one per switch would leave the old ones pointing at its memory
__source_cache = {}


def make_sources(screen, rotation, where):
    """The canvases for one orientation, of the size that fills the panel.

    PSRAM gets one per background and they stay valid, so they are drawn once. SRAM
    holds a single full-size canvas whatever its shape, so every SRAM source is the
    same memory and only the last one drawn holds good: it keeps the tearing cue to
    one background and is redrawn on every switch.
    """
    width, height = source_size(screen, rotation)
    key = (where, width, height)

    canvases = __source_cache.get(key)
    if canvases is None:
        gc.collect()
        if where == "sram":
            canvases = [image(width, height, spidisplay.buffer(width * height * 4))]
        else:
            canvases = [image(width, height) for _ in BACKGROUNDS]
            for canvas, background in zip(canvases, BACKGROUNDS):
                draw(canvas, width, height, background)

        __source_cache[key] = canvases

    if where == "sram":
        draw(canvases[0], width, height, SRAM_BACKGROUND)

    return canvases


def measure(screen, display, canvases, rotation, mirror, pixel_double, frame_count):
    """One pass: warm up, then average MEASURE_FRAMES of stats().

    frame_count carries the background cadence across passes and cells, so the
    cycle stays even rather than restarting on every pass.
    """
    cycle = FRAMES_PER_BACKGROUND * len(canvases)

    for _ in range(WARMUP_FRAMES):
        screen.update(canvases[(frame_count % cycle) // FRAMES_PER_BACKGROUND],
                      rotation=rotation, mirror=mirror,
                      pixel_double=pixel_double, v_sync=V_SYNC)
        frame_count += 1

    totals = dict.fromkeys(STAT_FIELDS, 0)
    for _ in range(MEASURE_FRAMES):
        screen.update(canvases[(frame_count % cycle) // FRAMES_PER_BACKGROUND],
                      rotation=rotation, mirror=mirror,
                      pixel_double=pixel_double, v_sync=V_SYNC)
        frame_count += 1
        stats = display.stats()
        for field in STAT_FIELDS:
            totals[field] += getattr(stats, field)

    return {field: totals[field] // MEASURE_FRAMES for field in STAT_FIELDS}, frame_count


def sram_fits(largest_bytes):
    """Whether the SRAM region can hold the biggest source the matrix asks for."""
    return spidisplay.buffer_size() >= largest_bytes

start_index = load_checkpoint(MATRIX_SHAPE)

# Said up front if the SRAM region cannot hold a source, not one failing cell at a time
sources = SOURCES
if "sram" in sources:
    largest = max(panel.WIDTH * panel.HEIGHT for _, panel, _ in PANELS) * 4
    if not sram_fits(largest):
        sources = tuple(s for s in sources if s != "sram")
        print(f"SRAM holds {spidisplay.buffer_size()} bytes and the largest source needs"
              f" {largest}, so the sram cells are skipped")

# What the skips leave, so the count and the estimate describe the real run
cells_per_group = CELLS_PER_GROUP // len(SOURCES) * len(sources)
groups_run = GROUPS // (len(BITDEPTHS) * len(BAUDRATES)) * sum(
    1 for bitdepth in BITDEPTHS for baudrate in BAUDRATES
    if not unshippable(bitdepth, baudrate))

measured = groups_run * cells_per_group
frames = measured * (WARMUP_FRAMES + MEASURE_FRAMES)
if groups_run != GROUPS:
    print(f"{GROUPS - groups_run} of {GROUPS} groups are unshippable and skipped")
print(f"{measured} cells in {groups_run} groups, resuming at cell {start_index}")
print(f"{frames} frames, so around {frames * NOMINAL_FRAME_MS / 3_600_000:.1f} hours"
      f" at {NOMINAL_FRAME_MS}ms a frame, rebuilding {groups_run} times")
time.sleep(START_DELAY_S)

mighty = None
screen = None
frame_count = 0     # Carries the background cadence across the whole sweep
groups_done = 0
__rate_cache = {}   # Measured refresh rate per panel and configured rate

try:
    index = start_index
    while index < CELLS:
        group_index = index // CELLS_PER_GROUP
        group = cell_at(index)[0]
        panel_name, bitdepth, framerate, baudrate, band_lines, cache_columns = group

        # Stepped over before anything is built, since the panel would come up fine
        # and only the arithmetic afterwards would show it was never usable
        if unshippable(bitdepth, baudrate):
            index = (group_index + 1) * CELLS_PER_GROUP
            save_checkpoint(index, MATRIX_SHAPE)
            continue

        sys_hz, peri_hz = CLOCKS[baudrate]
        machine.freq(sys_hz, peri_hz)
        time.sleep(0.02)

        settings = {"bitdepth": bitdepth, "baudrate": baudrate,
                    "band_lines": band_lines, "cache_columns": cache_columns,
                    "v_sync": False}
        if framerate is not None:
            settings["framerate"] = framerate

        # A rate outside the controller's table, or a size the transport cannot
        # carry, is a whole group to step over rather than a run to abandon
        skipped = None
        try:
            port_name = PANEL_PORTS[panel_name]
            mighty = MightyFX(spce_a=SPCE.SCREEN if port_name == "a" else None,
                              spce_b=SPCE.SCREEN if port_name == "b" else None)
            port = mighty.spce_a if port_name == "a" else mighty.spce_b
            screen = PANEL_CLASSES[panel_name](port, **settings)
        except ValueError as e:
            skipped = e
            index = (group_index + 1) * CELLS_PER_GROUP
            save_checkpoint(index, MATRIX_SHAPE)

        if skipped is not None:
            print(f"skipping {group}: {skipped}")
            display = None
            achieved_baudrate = band_rows = actual_framerate = None
        else:
            display = screen.__display

            # Both went through a clamp, so record what the driver settled on and
            # not only what was asked for
            achieved_baudrate = display.baudrate()
            band_rows = display.band_rows()

            # The rate the panel actually runs at, which the refresh budget is spent
            # against. Measured rather than taken from FRAMERATE, though the two
            # agree within 2% on both panels, so this is corroboration not correction.
            # It depends on the panel and its rate alone, so the probe is worth its
            # second once per pair rather than once per group.
            rate_key = (panel_name, screen.framerate)
            actual_framerate = __rate_cache.get(rate_key)
            if actual_framerate is None:
                period_us, _, edges = display.te_probe(TE_PROBE_MS)
                actual_framerate = 1_000_000 / period_us if edges >= 2 and period_us else 0.0
                __rate_cache[rate_key] = actual_framerate

        canvases = None
        loaded = None

        while index < CELLS and index // CELLS_PER_GROUP == group_index:
            _, rotation, source, mirror, pixel_double = cell_at(index)

            if source not in sources:
                index += 1
                continue

            if mighty.boot_pressed():
                raise KeyboardInterrupt

            # Held across cells, since only a change of orientation or of region
            # needs the sources building again
            if loaded != (rotation in (90, 270), source):
                canvases = make_sources(screen, rotation, source)
                loaded = (rotation in (90, 270), source)

            averages, frame_count = measure(screen, display, canvases, rotation,
                                            mirror, pixel_double, frame_count)

            row = {
                "cell_index": index,
                "panel": panel_name,
                "port": port_name,
                "width": screen.width,
                "height": screen.height,
                "bitdepth": screen.__bitdepth,
                "framerate": screen.framerate,
                "actual_framerate": round(actual_framerate, 2),
                "requested_baudrate": baudrate,
                "baudrate": achieved_baudrate,
                "requested_band_lines": band_lines,
                "band_rows": band_rows,
                "cache_columns": cache_columns,
                "rotation": rotation,
                "mirror": mirror,
                "pixel_double": pixel_double,
                "source": source,
                "v_sync": V_SYNC,
                "sys_hz": sys_hz,
                "peri_hz": peri_hz,
            }
            row.update(averages)
            append_result(row)

            print(f"{index:>6} {panel_name} {achieved_baudrate // 1_000_000}MHz"
                  f" {screen.__bitdepth}bpp band {band_rows:>2} cache {cache_columns:>2}"
                  f" rot {rotation:>3} {'mir' if mirror else '   '} {source:>5}"
                  f" {'dbl' if pixel_double else '   '}"
                  f" convert {averages['convert_total_us']:>7} stall {averages['stall_us']:>7}"
                  f" frame {averages['frame_us']:>7}")

            index += 1
            save_checkpoint(index, MATRIX_SHAPE)

        # A port keeps every claim its screens made, so the next group needs a whole
        # new MightyFX. Verified on hardware 2026-08-01: shutdown() then rebuilding
        # in process takes effect, so a group boundary need not cost a reset
        if mighty is not None:
            mighty.shutdown()
            mighty = None
            screen = None
            display = None

            # A bus releases its DMA channel only from its finaliser, and a sweep
            # allocates too little to collect on its own, so the 16 channels would
            # run out after 16 rebuilds
            gc.collect()

        groups_done += 1
        if RESET_EVERY_GROUPS and index < CELLS and groups_done % RESET_EVERY_GROUPS == 0:
            print(f"resetting after {groups_done} groups, resuming at cell {index}")
            machine.reset()

    print("\nSweep complete.")

finally:
    if mighty is not None:
        mighty.shutdown()
