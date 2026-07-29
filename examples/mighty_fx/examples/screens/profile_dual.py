# Measures whether one core can convert for two screens at once.
#
# Two screens streaming concurrently share one CPU but have a wire each, so the
# convert cost for both must fit inside one screen's per-row wall time. This
# reports that budget against the measured cost for a source in PSRAM and in
# SRAM, since conversion reads the source once per pixel and PSRAM is reached
# over XIP. It also reports the TE shape and the write-start skew that sequential
# updates produce today.
#
# Edit BAND_LINES and re-run to compare band sizes. Values above 16 are clamped.

from mighty_fx import SPCE, MightyFX, ScreenDef, screen_defs
from picovector import color, image, mat3, shape

SCREEN_A = SPCE.SCREEN_280
SCREEN_B = SPCE.SCREEN_280
BAND_LINES = 1
FRAMES = 30
TE_PROBE_MS = 500

BITS_PER_BYTE = 8
UINT32 = 0xFFFFFFFF

# MightyFX takes whole screen definitions, so the band size is swept by
# overriding the shipped definition for each port.
defs = [ScreenDef(d.baud, d.bits, d.fps, BAND_LINES, d.width, d.height, d.columns, d.spi_bits)
        for d in (screen_defs[SCREEN_A], screen_defs[SCREEN_B])]

mighty = MightyFX(spce_a=SCREEN_A, spce_b=SCREEN_B, native_display=True,
                  sdef_a=defs[0], sdef_b=defs[1])
screens = mighty.screen_a, mighty.screen_b
displays = [s._display for s in screens]

WIDTH, HEIGHT = screens[0].width, screens[0].height
centre_x, centre_y = WIDTH / 2, HEIGHT / 2
line = shape.line(40, 0, 0, 120, 2)

# The GC heap is PSRAM-only on this board, so a plain image() lands in PSRAM.
# canvas() places one in the SRAM region the GC never gets.
psram_canvas = image(WIDTH, HEIGHT)
sram_canvas = screens[0].canvas()


def row_bytes(screen):
    # Matches make_descriptor: RGB444 packs two pixels into three bytes.
    return screen.width * 3 // 2 if screen._bitdepth == 12 else screen.width * 2


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


def run(canvas, rotation, v_sync, frame_bits):
    """Update both screens sequentially, keeping the worst case of FRAMES frames."""
    for display in displays:
        display.spi_frame_bits(frame_bits)

    worst = [{"convert": 0, "stall": 0, "frame": 0, "te": 0, "bands": 0} for _ in displays]
    worst_skew = 0
    t = r = 0

    for _ in range(FRAMES):
        draw(canvas, t, r)
        for screen in screens:
            screen.update(canvas, rotation=rotation, v_sync=v_sync)

        stats = [d.stats() for d in displays]
        for i, display in enumerate(displays):
            _, _, te_us, frame_us = display.profile()
            convert_us, stall_us, bands, _, _ = stats[i]
            w = worst[i]
            w["convert"] = max(w["convert"], convert_us)
            w["stall"] = max(w["stall"], stall_us)
            w["frame"] = max(w["frame"], frame_us)
            w["te"] = max(w["te"], te_us)
            w["bands"] = bands

        # write_start_us is absolute, so the difference between the two RAMWRs is
        # the skew. Screen A always goes first, and the mask covers timer wrap.
        worst_skew = max(worst_skew, (stats[1][3] - stats[0][3]) & UINT32)

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
    configured = defs[index].fps
    print(f"  TE: period {period_us}us ({fps:.1f}fps, {configured} configured),"
          f" high {high_us}us ({duty:.1f}% duty)")
    if high_us * 2 < period_us:
        print("  high is vertical blanking, so the falling edge starts row 0 as assumed")
    else:
        print("  high is the visible scan, so the polarity is inverted and the tear analysis flips")


def report_case(name, canvas, rotation, v_sync=False, frame_bits=8):
    worst, skew = run(canvas, rotation, v_sync, frame_bits)
    rows = HEIGHT
    wire_us = row_wire_us(screens[0], displays[0].stats()[4])

    print(f"\n{name}, rotation {rotation}, {frame_bits}-bit frames, v_sync={v_sync},"
          f" worst of {FRAMES} frames:")
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
          f" band_lines={BAND_LINES}")

    for index, (screen, display) in enumerate(zip(screens, displays)):
        baud = display.stats()[4]
        print(f"\nscreen {index}: baudrate {baud} ({defs[index].baud} requested)")
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

    # One v_sync pass for the skew a TE wait adds on top.
    report_case("sram source", sram_canvas, 0, v_sync=True, frame_bits=16)

finally:
    mighty.shutdown()
