# Checks the frame converter: the sources it must accept and refuse, and that an
# accepted one converts to exactly the right bytes. Spritesheet cells, palettised GIF
# frames and alpha compositing are the cases.
#
# The converted bytes are the verdict, not the glass. A whole-region SRAM view taken
# before the screen exists still addresses the band ring afterwards, and bands of half
# the panel height make a frame exactly two slots, so the ring holds the whole frame.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across to
# run it, with a 2.8" on SP/CE A. The three asset paths below report N/A when absent.
# GIF_PATH is a panel-sized strip of solid CELL_COLORS frames, GIF_WIDE_PATH a 64-wide
# strip of six, and INDEXED_PATH an indexed PNG with transparent, translucent and
# opaque palette entries.

import gc

import spidisplay
from mighty_fx import SPCE, MightyFX
from picovector import color, image
from screens import Screen280

SCREEN = Screen280

GIF_PATH = "/images/anim_solid.gif"
GIF_WIDE_PATH = "/images/anim6.gif"
INDEXED_PATH = "/images/transparent_indexed.png"

CELL_COLORS = (
    color.rgb(255, 0, 0),
    color.rgb(0, 255, 0),
    color.rgb(0, 0, 255),
    color.rgb(255, 255, 0),
    color.rgb(255, 0, 255),
    color.rgb(0, 255, 255),
)
BAR_BG = color.rgb(0, 0, 0)
BAR_W = 20              # Bars in a cell; a shear shifts them sideways per row
PHASE_STEP = 10         # Per cell, so two cells never draw the same bars

BG = color.rgb(0, 96, 255)          # Differs from SRC in all three channels
BG_OTHER = color.rgb(255, 32, 0)    # A second background that must not show through
SRC = color.rgb(255, 224, 32)

# Case names to skip, for stepping past one that locks an unguarded build
SKIP = ()

# Raised when picovector or update() declines a case, which is reported as N/A
BUILD_ERRORS = (ValueError, TypeError, MemoryError, OSError, AttributeError)

tally = {"PASS": 0, "FAIL": 0, "N/A": 0, "SKIP": 0}


def verdict(kind, detail):
    tally[kind] += 1
    print(f"  {kind}  {detail}")


def pack565(c):
    # One RGB565 pixel, big-endian, as the kernel's packer emits it
    v = ((c[0] >> 3) << 11) | ((c[1] >> 2) << 5) | (c[2] >> 3)
    return bytes((v >> 8, v & 0xff))


def rgb(c):
    return (c.r, c.g, c.b)


def blend(src, bg, alpha):
    # One premultiplied channel over the background, byte for byte picovector's blend_over_premul()
    if alpha == 0:
        return bg
    if alpha == 255:
        return src
    return min(src + ((bg * (255 - alpha) + 128) >> 8), 255)


def composite(src_rgb, bg_rgb, alpha):
    return pack565(tuple(blend(src_rgb[i], bg_rgb[i], alpha) for i in range(3)))


def first_diff(got, want, row_bytes):
    # Bytes differing, and where the first one is, as (count, (row, column))
    n = min(len(got), len(want))
    count = 0
    at = None
    for i in range(n):
        if got[i] != want[i]:
            count += 1
            if at is None:
                at = (i // row_bytes, (i % row_bytes) // 2)
    return count, at


def bar_row(width, index):
    # One packed row of cell index: vertical bars of its colour on black
    fg = pack565(rgb(CELL_COLORS[index % len(CELL_COLORS)]))
    bg = pack565(rgb(BAR_BG))
    phase = (index * PHASE_STEP) % (BAR_W * 2)
    row = bytearray()
    for x in range(width):
        row += fg if ((x + phase) // BAR_W) % 2 == 0 else bg
    return bytes(row)


def paint_cell(target, x0, y0, w, h, index):
    # Paint cell index into target at (x0, y0), matching bar_row()
    phase = (index * PHASE_STEP) % (BAR_W * 2)
    target.pen = BAR_BG
    target.rectangle(x0, y0, w, h)
    target.pen = CELL_COLORS[index % len(CELL_COLORS)]
    for x in range(w):
        if ((x + phase) // BAR_W) % 2 == 0:
            target.vspan(x0 + x, y0, h)


def fill_rgba(img, row_bytes):
    # Write one row template into every row of an RGBA image's own buffer
    view = memoryview(img)
    stride = len(row_bytes)
    for y in range(img.height):
        view[y * stride:(y + 1) * stride] = row_bytes


def stride_of(view):
    # Whether a contiguous walk of the view's bytes samples the view itself: image()
    # over its memoryview is exactly the pitch a naive reader would infer
    try:
        model = image(view.width, view.height, memoryview(view))
    except BUILD_ERRORS as e:
        return None, f"cannot model it: {type(e).__name__}: {e}"
    step = max(1, view.width // 8)
    for y in range(view.height):
        for x in range(0, view.width, step):
            if model.get(x, y).p != view.get(x, y).p:
                return False, f"first disagreement at row {y}, column {x}"
    return True, "agrees over every sample"


# Phase 1: the sources update() must accept and refuse. A buffer shorter than the
# extent the image reports would be read out of bounds, and a degenerate extent
# would draw a frame of background, so both must raise ValueError.

def phase_sources():
    print("\n=== sources update() must accept and refuse ===")
    mighty = MightyFX(spce_a=SPCE.SCREEN)
    screen = SCREEN(mighty.spce_a)
    screen.brightness(1.0)
    W, H = screen.width, screen.height
    exact = W * H * 4
    drawn = [0]

    def build(width, height, nbytes):
        # Both the GC heap and the SRAM region are tried before a case is N/A
        reasons = []
        for kind in ("bytearray", "spidisplay.buffer"):
            try:
                buffer = bytearray(nbytes) if kind == "bytearray" else spidisplay.buffer(nbytes)
                return image(width, height, buffer), None
            except BUILD_ERRORS as e:
                reasons.append(f"{kind}: {type(e).__name__}: {e}")
        return None, "; ".join(reasons)

    def check(name, expect_raise, img, build_error=None, rotation=0):
        print(f"  {name}: ", end="")
        if name in SKIP:
            verdict("SKIP", "listed in SKIP")
            return
        if img is None:
            verdict("N/A", build_error)
            return
        if not expect_raise:
            img.pen = color.hsv(drawn[0] * 24 % 256, 255, 255)
            img.clear()
            drawn[0] += 1
        try:
            screen.update(img, rotation=rotation)
        except ValueError as e:
            verdict("PASS" if expect_raise else "FAIL", f"ValueError: {e}")
            return
        except BUILD_ERRORS as e:
            verdict("FAIL", f"unexpected {type(e).__name__}: {e}")
            return
        verdict("FAIL" if expect_raise else "PASS", "accepted and drew" if expect_raise else "drew")

    def case(name, expect_raise, width, height, nbytes, rotation=0):
        gc.collect()
        img, build_error = build(width, height, nbytes)
        check(name, expect_raise, img, build_error, rotation)

    # Whether the reported length tracks the wrapped buffer. If it is nominal, the
    # length half of the check compares a number with itself and cannot fire.
    try:
        probe = image(W, H, bytearray(64))
        reported = len(memoryview(probe))
        length_tracks = reported == 64
        print(f"  a {W}x{H} image over 64 bytes reports {reported} bytes,"
              f" so the length check {'can' if length_tracks else 'cannot'} fire")
        del probe
    except BUILD_ERRORS as e:
        length_tracks = True
        print(f"  picovector refuses a short buffer itself ({e}), so the short cases report N/A")

    print("\n  must draw:")
    gc.collect()
    check("plain image(), PSRAM", False, image(W, H))
    gc.collect()
    check("screen.canvas(), SRAM", False, screen.canvas())
    case("exact backing buffer", False, W, H, exact)
    case("buffer with 64 bytes spare", False, W, H, exact + 64)
    case("source smaller than the screen", False, W // 2, H // 2, (W // 2) * (H // 2) * 4)
    case("1x1 source", False, 1, 1, 4)
    print("  animated GIF frame, palettised: ", end="")
    try:
        frame = image.load(GIF_PATH).spritesheet().sprite(0, 0)
        screen.update(frame, rotation=0)
        verdict("PASS", "drew")
    except BUILD_ERRORS as e:
        verdict("N/A", f"{GIF_PATH}: {type(e).__name__}: {e}")

    print("\n  must raise:")
    case("one byte short", True, W, H, exact - 1)
    case("half length", True, W, H, exact // 2)
    case("1x1 source with 3 bytes", True, 1, 1, 3)
    case("empty buffer", True, W, H, 0)
    for angle in (90, 180, 270):
        case(f"half length at rotation {angle}", True, W, H, exact // 2, rotation=angle)
    case("zero width", True, 0, H, exact)
    case("zero height", True, W, 0, exact)

    print("\n  the bus survives a rejection:")
    gc.collect()
    check("draw after the rejections", False, screen.canvas())

    if not length_tracks:
        print("  the short cases cannot pass while the source reports its nominal size;"
              " the dimension cases alone say whether the check is in the firmware")
    mighty.shutdown()


# Phase 2: the converted bytes, read back from the band ring.

def phase_readback():
    print("\n=== converted bytes, read back from the band ring ===")
    spidisplay.release_buffers()
    mighty = MightyFX(spce_a=SPCE.SCREEN)
    screen = None
    try:
        # Taken before the screen exists, so it spans the bands the screen claims
        region = spidisplay.buffer(spidisplay.buffer_size(), 0)
        screen = SCREEN(mighty.spce_a, bitdepth=16, band_lines=160, cache_columns=0)
        screen.brightness(1.0)
        W, H = screen.width, screen.height
        ROW_BYTES = W * 2
        FRAME_BYTES = ROW_BYTES * H
        base = spidisplay.buffer_size()
        ring = region[base:base + FRAME_BYTES]
        display = screen.__display
        print(f"  {W}x{H} at 16-bit, band_rows {display.band_rows()},"
              f" claim {display.sram_bytes()} bytes at {base}")

        # Preflight: the ring must hold a whole frame in row order, or nothing below means anything
        usable = display.sram_bytes() >= FRAME_BYTES and display.band_rows() * 2 == H
        if usable:
            halves = image(W, H)
            halves.pen = CELL_COLORS[0]
            halves.rectangle(0, 0, W, H // 2)
            halves.pen = CELL_COLORS[2]
            halves.rectangle(0, H // 2, W, H // 2)
            screen.update(halves, rotation=0, offset=(0, 0))
            want = pack565(rgb(CELL_COLORS[0])) * (W * (H // 2))
            usable = bytes(ring[:len(want)]) == want
            del halves, want
            gc.collect()
        print(f"  PREFLIGHT: {'ring is in row order' if usable else 'ring cannot be trusted, byte verdicts are N/A'}")

        def check_frame(label, view, want, **placement):
            gc.collect()
            print(f"  {label}: ", end="")
            try:
                screen.update(view, rotation=0, offset=(0, 0), **placement)
            except BUILD_ERRORS as e:
                verdict("FAIL", f"refused: {type(e).__name__}: {e}")
                return
            if not usable:
                verdict("N/A", "see preflight")
                return
            count, at = first_diff(bytes(ring[:len(want)]), want, ROW_BYTES)
            if count == 0:
                verdict("PASS", f"all {len(want)} bytes match")
            else:
                verdict("FAIL", f"{count} bytes differ, first at row {at[0]} column {at[1]}")

        def cell_case(label, make, expect_contiguous):
            # make() returns (view, cell index). The stride classification is
            # reported first, so an unexpected byte verdict can be read against it.
            gc.collect()
            try:
                view, index = make()
            except BUILD_ERRORS as e:
                print(f"  {label}: ", end="")
                verdict("N/A", f"could not build it: {type(e).__name__}: {e}")
                return
            agrees, detail = stride_of(view)
            layout = "contiguous" if agrees else "strided"
            note = "" if agrees is None or agrees == expect_contiguous else " (UNEXPECTED)"
            print(f"  {label}: {layout}{note}, {detail}")
            check_frame(f"{label}, bytes", view, bar_row(W, index) * H)

        print("\n  spritesheet cells:")

        def plain():
            img = image(W, H)
            paint_cell(img, 0, 0, W, H, 0)
            return img, 0

        def vertical(k, rows=4):
            parent = image(W, H * rows)
            for i in range(rows):
                paint_cell(parent, 0, i * H, W, H, i)
            return parent.spritesheet(1, rows).sprite(0, k), k

        def horizontal(k, cols=4):
            parent = image(W * cols, H)
            for i in range(cols):
                paint_cell(parent, i * W, 0, W, H, i)
            return parent.spritesheet(cols, 1).sprite(k, 0), k

        def rectangular():
            cols, rows = 2, 3
            parent = image(W * cols, H * rows)
            for y in range(rows):
                for x in range(cols):
                    paint_cell(parent, x * W, y * H, W, H, y * cols + x)
            return parent.spritesheet(cols, rows).sprite(1, 2), 2 * cols + 1

        cell_case("control, plain full-size image", plain, True)
        cell_case("1 column x 4 rows, cell 3", lambda: vertical(3), True)
        cell_case("4 columns x 1 row, cell 0", lambda: horizontal(0), False)
        cell_case("4 columns x 1 row, cell 3", lambda: horizontal(3), False)
        cell_case("2 columns x 3 rows, cell (1, 2)", rectangular, False)

        print("  grid larger than the image: ", end="")
        try:
            tiny = image(W, H).spritesheet(W * 2, 1).sprite(0, 0)
            try:
                screen.update(tiny, rotation=0, offset=(0, 0))
                verdict("FAIL", "a zero-extent cell was accepted and drawn")
            except ValueError as e:
                verdict("PASS", f"refused: {e}")
        except BUILD_ERRORS as e:
            verdict("N/A", f"{type(e).__name__}: {e}")

        # Palettised strips: every frame one solid colour, so the expected bytes
        # need no reference image
        def want_solid(c, cw, ch):
            fg, bg = pack565(rgb(c)), pack565(rgb(BAR_BG))
            cw, ch = min(cw, W), min(ch, H)
            return (fg * cw + bg * (W - cw)) * ch + bg * W * (H - ch)

        def gif_run(path):
            print(f"\n  GIF {path}:")
            gc.collect()
            try:
                gif = image.load(path)
                sheet = gif.spritesheet()
            except BUILD_ERRORS as e:
                print("  load: ", end="")
                verdict("N/A", f"{type(e).__name__}: {e}")
                return
            fw = gif.width // sheet.sprites
            vis = min(gif.width, W)
            row = b"".join(pack565(rgb(CELL_COLORS[x // fw])) for x in range(vis))
            row += pack565(rgb(BAR_BG)) * (W - vis)
            ch = min(gif.height, H)
            check_frame("whole strip", gif, row * ch + pack565(rgb(BAR_BG)) * W * (H - ch))
            for i in (0, sheet.sprites - 1):
                check_frame(f"frame {i}", sheet.sprite(i, 0),
                            want_solid(CELL_COLORS[i], fw, gif.height))

        gif_run(GIF_PATH)
        gif_run(GIF_WIDE_PATH)

        # An RGBA source's alpha is ignored: only a palette composites, ahead of the
        # pixel loop, a per-pixel blend having measured too expensive to keep
        print("\n  RGBA alpha is ignored:")
        src_rgb, bg_rgb = rgb(SRC), rgb(BG)
        canvas = image(W, H)
        ramp = b"".join(bytes((src_rgb[0], src_rgb[1], src_rgb[2], x * 255 // (W - 1))) for x in range(W))
        fill_rgba(canvas, ramp)
        check_frame("alpha ramp converts as opaque", canvas, pack565(src_rgb) * (W * H), bg_color=BG)
        fill_rgba(canvas, bytes(src_rgb + (255,)) * W)
        screen.update(canvas, rotation=0, offset=(0, 0), bg_color=BG)
        opaque = bytes(ring[:FRAME_BYTES])
        fill_rgba(canvas, bytes(src_rgb + (0,)) * W)
        check_frame("alpha 0 over another background converts the same", canvas, opaque, bg_color=BG_OTHER)
        del canvas, opaque
        gc.collect()

        print("\n  palette alpha composites over the background:")
        print(f"  {INDEXED_PATH}: ", end="")
        try:
            sprite = image.load(INDEXED_PATH)
            if sprite.palette is None:
                raise ValueError("loaded as truecolour, so it carries no table")
            palette = bytes(memoryview(sprite.palette))
            indices = bytes(memoryview(sprite))
            table = [composite((palette[i * 4], palette[i * 4 + 1], palette[i * 4 + 2]), bg_rgb, palette[i * 4 + 3])
                     for i in range(len(palette) // 4)]
            want = bytearray(pack565(bg_rgb) * (W * H))
            for y in range(sprite.height):
                row = b"".join(table[indices[y * sprite.stride + x]] for x in range(sprite.width))
                want[y * ROW_BYTES:y * ROW_BYTES + len(row)] = row
            print(f"{sprite.width}x{sprite.height}, {len(palette) // 4} entries")
            check_frame("composited frame", sprite, bytes(want), bg_color=BG)
        except BUILD_ERRORS as e:
            verdict("N/A", f"{type(e).__name__}: {e}")
    finally:
        if screen is not None:
            screen.brightness(0.0)
        mighty.shutdown()


phase_sources()
phase_readback()

print(f"\n{tally['PASS']} passed, {tally['FAIL']} failed, {tally['N/A']} inconclusive, {tally['SKIP']} skipped")
if tally["FAIL"]:
    print("A failed refusal reads out of bounds or draws a background frame; a failed"
          " byte case converted the wrong pixels. Read a cell's stride line against its verdict.")
elif tally["N/A"] and not tally["PASS"]:
    print("Nothing was measured, so this run says nothing about the converter.")
else:
    print("Every source was accepted or refused as it should be, and every accepted"
          " one converted to its own pixels exactly.")
