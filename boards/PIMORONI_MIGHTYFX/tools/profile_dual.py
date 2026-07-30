# Measures whether one core can convert for two screens at once.
#
# Two screens streaming concurrently share one CPU but have a wire each, so the
# convert cost for both must fit inside one screen's per-row wall time. This
# reports that budget against the measured cost for a source in PSRAM and in
# SRAM, since conversion reads the source once per pixel and PSRAM is reached
# over XIP. It also reports the TE shape and the write-start skew that sequential
# updates produce today.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across
# to run it. Edit BAND_LINES and re-run to compare band sizes. Values above 16
# are clamped.

from mighty_fx import SPCE, MightyFX
from picovector import color, image, mat3, shape
from screens import Screen280

SCREEN_A = Screen280
SCREEN_B = Screen280
BAND_LINES = 1
FRAMES = 30
TE_PROBE_MS = 500

BITS_PER_BYTE = 8
UINT32 = 0xFFFFFFFF

# A screen class carries its panel's settings, so the band size is swept by
# overriding that one setting on each. v_sync is off so the timings are the
# conversion and the wire alone, while te stays on so the TE shape can be probed.
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
screens = (SCREEN_A(mighty.spce_a, band_lines=BAND_LINES, v_sync=False),
           SCREEN_B(mighty.spce_b, band_lines=BAND_LINES, v_sync=False))
displays = [s.display for s in screens]

WIDTH, HEIGHT = screens[0].width, screens[0].height
centre_x, centre_y = WIDTH / 2, HEIGHT / 2
line = shape.line(40, 0, 0, 120, 2)

# The GC heap is PSRAM-only on this board, so a plain image() lands in PSRAM.
# canvas() places one in the SRAM region the GC never gets.
psram_canvas = image(WIDTH, HEIGHT)
sram_canvas = screens[0].canvas()


def row_bytes(screen):
    # Matches make_descriptor: RGB444 packs two pixels into three bytes.
    return screen.width * 3 // 2 if screen.bitdepth == 12 else screen.width * 2


def row_wire_us(screen, baudrate):
    return row_bytes(screen) * BITS_PER_BYTE * 1_000_000 / baudrate


def draw(canvas, t, r):
    canvas.pen = color.black
    canvas.clear()
    for i in range(0, 360, 15):
        hue = (i * 255) // 360
        canvas.pen = color.hsv((hue + t) % 256, 255, 255)
        line.transform = mat3().translate(centre_x, centre_y).rotate(i + r)
        canvas.shape(line)


def run(canvas, rotation, frame_bits):
    """Update both screens sequentially, keeping the worst case of FRAMES frames."""
    for display in displays:
        display.spi_frame_bits(frame_bits)

    worst = [{"convert": 0, "stall": 0, "frame": 0, "te": 0} for _ in displays]
    worst_skew = 0
    t = r = 0

    for _ in range(FRAMES):
        draw(canvas, t, r)
        for screen in screens:
            screen.update(canvas, rotation=rotation)

        stats = [d.stats() for d in displays]
        for i, s in enumerate(stats):
            w = worst[i]
            w["convert"] = max(w["convert"], s.convert_total_us)
            w["stall"] = max(w["stall"], s.stall_us)
            w["frame"] = max(w["frame"], s.frame_us)
            w["te"] = max(w["te"], s.te_wait_us)

        # write_start_us is absolute, so the difference between the two RAMWRs is
        # the skew. Screen A always goes first, and the mask covers timer wrap.
        worst_skew = max(worst_skew, (stats[1].write_start_us - stats[0].write_start_us) & UINT32)

        t += 4
        r += 2

    return worst, worst_skew


def report_te(index, display):
    period_us, high_us, edges = display.te_probe(TE_PROBE_MS)
    if edges < 2:
        print(f"  TE: no signal ({edges} edges) - was TEON issued?")
        return

    fps = 1_000_000 / period_us
    duty = 100.0 * high_us / period_us
    configured = screens[index].framerate
    print(f"  TE: period {period_us}us ({fps:.1f}fps, {configured} configured),"
          f" high {high_us}us ({duty:.1f}% duty)")
    if high_us * 2 < period_us:
        print("  high is vertical blanking, so the falling edge starts row 0 as assumed")
    else:
        print("  high is the visible scan, so the polarity is inverted and the tear analysis flips")


def report_case(name, canvas, rotation, frame_bits=8):
    worst, skew = run(canvas, rotation, frame_bits)
    rows = HEIGHT
    wire_us = row_wire_us(screens[0], displays[0].baudrate())

    print(f"\n{name}, rotation {rotation}, {frame_bits}-bit frames,"
          f" v_sync={screens[0].v_sync}, worst of {FRAMES} frames:")
    for index, w in enumerate(worst):
        print(f"  screen {index}: convert {w['convert']}us ({w['convert'] / rows:.1f}us/row),"
              f" stall {w['stall']}us, frame {w['frame']}us, te_wait {w['te']}us")

    # Wall time per row is what a second screen has to hide inside. It exceeds
    # the arithmetic wire time by the SPI peripheral's per-frame idle.
    wall_us = max(w["frame"] for w in worst) / rows
    both_us = sum(w["convert"] for w in worst) / rows
    print(f"  wire {wire_us:.1f}us/row computed, {wall_us:.1f}us/row measured,"
          f" ratio {wall_us / wire_us:.4f} ({wall_us / wire_us * frame_bits:.2f}"
          f" clocks per {frame_bits}-bit frame)")
    verdict = "fits" if both_us < wall_us * 0.75 else "does not fit"
    print(f"  both screens convert {both_us:.1f}us/row against {wall_us:.1f}us"
          f" ({both_us / wall_us:.2f}x) - {verdict}")
    print(f"  1 screen {1_000_000 / max(w['frame'] for w in worst):.1f}fps,"
          f" write-start skew {skew}us")


try:
    print(f"screens: {WIDTH}x{HEIGHT} and {screens[1].width}x{screens[1].height},"
          f" band_lines={BAND_LINES} requested, {displays[0].band_rows()} rows per band")

    for index, (screen, display) in enumerate(zip(screens, displays)):
        baud = display.baudrate()
        print(f"\nscreen {index}: baudrate {baud} ({screen.requested_baudrate} requested)")
        print(f"  row is {row_bytes(screen)} bytes"
              f" = {row_wire_us(screen, baud):.1f}us on the wire")
        report_te(index, display)

    # Rotation 0 walks the source sequentially and covers the whole destination,
    # so PSRAM against SRAM here is the clean measure of how much of the convert
    # cost is the source read.
    report_case("psram source", psram_canvas, 0)
    report_case("sram source", sram_canvas, 0)

    # 16-bit frames should not change convert at all, and should cut wall time by
    # halving the number of inter-frame gaps. Watch the clocks-per-frame figure:
    # if the gap is what it looks like, it stays constant while the ratio drops.
    # CHECK THE PANELS: wrong byte order shows up as scrambled colour, since the
    # firmware cannot see what actually went out on the wire.
    report_case("sram source", sram_canvas, 0, frame_bits=16)
    report_case("psram source", psram_canvas, 0, frame_bits=16)

    # Rotation 90 walks a source column per destination row. The column cache
    # serves that, but only for a PSRAM source, and a portrait source into a
    # portrait destination covers less area here, so compare the two 90s to each
    # other and not to the 0s.
    report_case("psram source", psram_canvas, 90)
    report_case("sram source", sram_canvas, 90)

finally:
    mighty.shutdown()
