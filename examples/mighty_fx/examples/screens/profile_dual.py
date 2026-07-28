# Measures whether one core can convert for two screens at once.
#
# Two screens streaming concurrently share one CPU but have a wire each, so the
# convert cost for both must fit inside one screen's per-row wire time. This
# reports that budget against the measured cost, plus the TE shape and the
# write-start skew that sequential updates produce today.
#
# Edit BAND_LINES and re-run to compare band sizes. Values above 16 are clamped.

from mighty_fx import SPCE, MightyFX, screen_defs
from picovector import color, image, mat3, shape

SCREEN_A = SPCE.SCREEN_280
SCREEN_B = SPCE.SCREEN_280
BAND_LINES = 1
FRAMES = 100
TE_PROBE_MS = 500

BITS_PER_BYTE = 8
UINT32 = 0xFFFFFFFF

mighty = MightyFX(spce_a=SCREEN_A, spce_b=SCREEN_B, native_display=True, bands=BAND_LINES)
screens = mighty.screen_a, mighty.screen_b
displays = [s._display for s in screens]
defs = screen_defs[SCREEN_A], screen_defs[SCREEN_B]

canvas = image(screens[0].width, screens[0].height)
centre_x, centre_y = screens[0].width / 2, screens[0].height / 2
line = shape.line(40, 0, 0, 120, 2)


def row_bytes(screen):
    # Matches make_descriptor: RGB444 packs two pixels into three bytes.
    return screen.width * 3 // 2 if screen._bitdepth == 12 else screen.width * 2


def row_wire_us(screen, baudrate):
    return row_bytes(screen) * BITS_PER_BYTE * 1_000_000 / baudrate


def draw(t, r):
    canvas.pen = color.black
    canvas.clear()
    for i in range(0, 360, 15):
        hue = (i * 255) // 360
        canvas.pen = color.hsv((hue + t) % 256, 255, 255)
        line.transform = mat3().translate(centre_x, centre_y).rotate(i + r)
        canvas.shape(line)


def run(v_sync):
    """Update both screens sequentially for FRAMES frames, keeping the worst case."""
    worst = [{"convert": 0, "stall": 0, "frame": 0, "te": 0, "bands": 0} for _ in displays]
    worst_skew = 0
    t = r = 0

    for _ in range(FRAMES):
        draw(t, r)
        for screen in screens:
            screen.update(canvas, v_sync=v_sync)

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


try:
    print(f"screens: {screens[0].width}x{screens[0].height}"
          f" and {screens[1].width}x{screens[1].height}, band_lines={BAND_LINES}")

    for index, (screen, display) in enumerate(zip(screens, displays)):
        baud = display.stats()[4]
        wire_us = row_wire_us(screen, baud)
        print(f"\nscreen {index}: baudrate {baud} ({defs[index].baud} requested)")
        print(f"  row is {row_bytes(screen)} bytes = {wire_us:.1f}us on the wire")
        report_te(index, display)

    for v_sync in (False, True):
        worst, skew = run(v_sync)
        budget_us = row_wire_us(screens[0], displays[0].stats()[4])
        print(f"\nv_sync={v_sync}, worst of {FRAMES} frames:")
        for index, w in enumerate(worst):
            rows = screens[index].height
            per_row = w["convert"] / rows
            print(f"  screen {index}: convert {w['convert']}us total"
                  f" ({per_row:.1f}us/row over {rows} rows, {w['bands']} bands)")
            print(f"            stall {w['stall']}us, frame {w['frame']}us, te_wait {w['te']}us")

        both = sum(w["convert"] for w in worst) / screens[0].height
        verdict = "fits, one core can feed both wires" if both < budget_us * 0.75 \
            else "too tight, one core cannot feed both wires"
        print(f"  both screens: {both:.1f}us/row against a {budget_us:.1f}us budget - {verdict}")
        print(f"  write-start skew: {skew}us")

finally:
    mighty.shutdown()
