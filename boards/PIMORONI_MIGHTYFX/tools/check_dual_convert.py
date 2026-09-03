# Measures what the second core buys frame conversion. Only rows reading SRAM are
# split, a canvas or a source read through the column cache, since two cores
# reading PSRAM over one QMI cost more than the halved pixel work saves. Each case
# says whether it expects the split, so a wrong answer either way is named.
#
# spidisplay.dual_convert() runs each case both ways over the same pixels, and
# core1_rows proves the split engaged. The setting survives a soft reset, so it is
# restored however the run ends. v_sync is off so the timings are conversion and the
# wire alone.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across
# to run it.

import gc

import spidisplay
from mighty_fx import SPCE, MightyFX
from picovector import color, image, mat3, shape
from screens import Screen154, Screen280

SCREEN = Screen154              # the panel type on SP/CE A
SETTINGS = ((2, 0), (12, 12))   # (band_lines, cache_columns) rows to compare
WARMUP_FRAMES = 2
MEASURE_FRAMES = 8

# What the split has to hold where it applies. A declined case must cost nothing.
SRAM_FLOOR = 1.6
CACHED_FLOOR = 1.1
DECLINE_TOLERANCE = 0.97        # A declined case at less than this lost time

BITS_PER_BYTE = 8

assert SCREEN in (Screen154, Screen280)


def draw(canvas):
    """Content with enough colour variety that no packer path is trivial."""
    canvas.pen = color.black
    canvas.clear()
    line = shape.line(40, 0, 0, 120, 2)
    for i in range(0, 360, 15):
        canvas.pen = color.hsv(((i * 255) // 360) % 256, 255, 255)
        line.transform = mat3().translate(canvas.width / 2, canvas.height / 2).rotate(i)
        canvas.shape(line)


def splits(source_name, rotation, cache_columns):
    """Whether these rows read SRAM, which is the whole rule for splitting.

    A canvas always does. A PSRAM source only does through a cache window, which
    needs both a rotation that strides by whole source rows and columns to cache.
    """
    if source_name == "SRAM":
        return True
    return rotation in (90, 270) and cache_columns >= 1


def measure(screen, source, rotation, dual):
    """Average convert wall time per row over MEASURE_FRAMES, and core1's share."""
    spidisplay.dual_convert(dual)
    for _ in range(WARMUP_FRAMES):
        screen.update(source, rotation=rotation)

    convert = core1 = frame = stall = 0
    for _ in range(MEASURE_FRAMES):
        screen.update(source, rotation=rotation)
        s = screen.__display.stats()
        convert += s.convert_total_us
        core1 += s.core1_rows
        frame += s.frame_us
        stall += s.stall_us

    return {"us_per_row": convert / MEASURE_FRAMES / screen.height,
            "core1_rows": core1 / MEASURE_FRAMES,
            "frame_ms": frame / MEASURE_FRAMES / 1000,
            "stall_ms": stall / MEASURE_FRAMES / 1000}


def verdict(expected, floor, ratio, core1_rows):
    """Judge one case against what its rows are allowed to do."""
    if not expected:
        if core1_rows:
            return "SPLIT SHOULD HAVE DECLINED"
        return "declines" if ratio > DECLINE_TOLERANCE else f"declined but {ratio:.2f}x"
    if not core1_rows:
        return "SPLIT NEVER ENGAGED"
    return "PASS" if ratio >= floor else f"under {floor}x"


try:
    for band_lines, cache_columns in SETTINGS:
        mighty = MightyFX(spce_a=SPCE.SCREEN)
        screen = SCREEN(mighty.spce_a, band_lines=band_lines,
                        cache_columns=cache_columns, v_sync=False)
        width, height = screen.width, screen.height

        # The GC heap is PSRAM-only on this board, so a plain image() lands in
        # PSRAM. canvas() places one in the SRAM region the GC never gets.
        sources = {"PSRAM": image(width, height), "SRAM": screen.canvas()}
        for source in sources.values():
            draw(source)

        row_bytes = width * 3 // 2 if screen.__bitdepth == 12 else width * 2
        baudrate = screen.__display.baudrate()
        row_wire_us = row_bytes * BITS_PER_BYTE * 1_000_000 / baudrate

        print(f"{type(screen).__name__} {width}x{height} {screen.__bitdepth}-bit at"
              f" {baudrate}Hz, band_lines={band_lines} cache_columns={cache_columns}")
        print(f"  wire: {row_wire_us:.1f}us a row, {row_wire_us * height / 1000:.1f}ms"
              f" a frame, {screen.__display.sram_bytes()}B of SRAM claimed")
        print("  source rot   one core   two cores   ratio  core1 rows"
              "     one frame    two frames   verdict")

        for name in ("SRAM", "PSRAM"):
            for rotation in (0, 90):
                expected = splits(name, rotation, cache_columns)
                floor = SRAM_FLOOR if name == "SRAM" else CACHED_FLOOR
                one = measure(screen, sources[name], rotation, False)
                two = measure(screen, sources[name], rotation, True)
                ratio = one["us_per_row"] / two["us_per_row"] if two["us_per_row"] else 0
                print(f"  {name:>6} {rotation:>3}   {one['us_per_row']:>7.1f}us"
                      f"   {two['us_per_row']:>7.1f}us   {ratio:>5.2f}x"
                      f"   {two['core1_rows']:>4.0f}/{height}"
                      f"   {one['frame_ms']:>5.1f}/{one['stall_ms']:<4.1f}ms"
                      f"  {two['frame_ms']:>5.1f}/{two['stall_ms']:<4.1f}ms"
                      f"   {verdict(expected, floor, ratio, two['core1_rows'])}")
        print()

        mighty.shutdown()
        del screen, sources, mighty
        gc.collect()

    print("frame columns are frame/stall. A frame at the wire figure is wire-bound,"
          " so conversion is no longer what limits it.")

# Leave the split as it ships, whatever the run did
finally:
    spidisplay.dual_convert(True)
