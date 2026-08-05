# Checks that a palettised image's transparency composites over the background
# colour, and that a truecolour image's alpha stays ignored.
#
# The verdict is the converted bytes, not the panel, by check_sheet_sources.py's
# ring readback: bands at half the panel height make a frame exactly two slots, so
# no slot is reused mid-frame and the ring holds the whole converted frame in panel
# byte order. That is compared against a packing computed here.
#
# Only an indexed source composites, because only its colour table can be
# composited ahead of the pixel loop; a per-pixel blend measured too expensive to
# keep. So the RGBA cases here assert the absence of a blend, which is what stops
# a later change reintroducing its cost unnoticed. They are built by writing bytes
# into an image's own buffer, since a picovector colour is always opaque and
# cannot supply an alpha byte.
#
# picovector stores colour premultiplied by its alpha, so the model here adds the
# source rather than scaling it. An asset with only transparent and opaque entries
# cannot tell the two apart, which is why the palettised case wants graded alpha:
# an indexed PNG carries one alpha per palette entry in tRNS, where a GIF offers
# only a single index that is either shown or not.
#
# What this cannot decide: an index byte reaching past the entries its image
# supplied, since picovector will not build such an image. That zero-filled tail
# is host-tested instead (test_indexed_short_palette_tail_is_transparent).
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across to
# run it. The palettised case needs its asset, which is generated rather than
# stored:
#   python3 -B .claude/assets/make_transparent_indexed_png.py
#   mpr.ps1 fs cp transparent_indexed.png :/images/   (fs cp, NOT -Stage)

import gc

import spidisplay
from mighty_fx import SPCE, MightyFX
from screens import Screen280
from picovector import color, image

INDEXED_PATH = "/images/transparent_indexed.png"

BG = color.rgb(0, 96, 255)        # Differs from the sources in all three channels
BG_OTHER = color.rgb(255, 32, 0)  # For the endpoint case, where bg must not show
SRC = color.rgb(255, 224, 32)

BUILD_ERRORS = (ValueError, TypeError, MemoryError, OSError, AttributeError)

tally = {"PASS": 0, "FAIL": 0, "N/A": 0}


def pack565(r, g, b):
    """One RGB565 pixel, big-endian, as the kernel's packer emits it."""
    v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    return bytes((v >> 8, v & 0xff))


def blend(src, bg, alpha):
    """One premultiplied channel over the background, as composite_over() does.

    Which is also picovector's blend_over_premul(), byte for byte.
    """
    if alpha == 0:
        return bg
    if alpha == 255:
        return src
    return min(src + ((bg * (255 - alpha) + 128) >> 8), 255)


def composite(src_rgb, bg_rgb, alpha):
    """A packed pixel of a premultiplied src over bg at this alpha."""
    return pack565(*(blend(src_rgb[i], bg_rgb[i], alpha) for i in range(3)))


def fill_rgba(img, row_bytes):
    """Write one row template into every row of an RGBA image's own buffer."""
    view = memoryview(img)
    stride = len(row_bytes)
    for y in range(img.height):
        view[y * stride:(y + 1) * stride] = row_bytes


def ramp_row(width, rgb):
    """A constant colour whose alpha ramps 0..255 across the width."""
    row = bytearray()
    for x in range(width):
        row += bytes((rgb[0], rgb[1], rgb[2], x * 255 // (width - 1)))
    return bytes(row)


def flat_row(width, rgb, alpha):
    return bytes((rgb[0], rgb[1], rgb[2], alpha)) * width


def first_diff(got, want, row_bytes):
    """Bytes differing, and where the first one is, as (count, row, col)."""
    n = min(len(got), len(want))
    count = 0
    at = None
    for i in range(n):
        if got[i] != want[i]:
            count += 1
            if at is None:
                at = (i // row_bytes, (i % row_bytes) // 2)
    return count, at


def verdict(kind, detail):
    tally[kind] += 1
    print(f"  {kind}  {detail}")


# An arena claim outlives a soft reset, so a leak from an earlier run would leave
# the screen below short of its bands.
spidisplay.release_buffers()

mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = None
try:
    # Taken before the screen exists, so it spans the region including the bands the
    # screen claims from the top of it.
    arena = spidisplay.buffer_size()
    region = spidisplay.buffer(arena, 0)

    screen = Screen280(mighty.spce_a, bitdepth=16, band_lines=160, cache_columns=0)
    screen.brightness = 1.0
    W, H = screen.width, screen.height
    ROW_BYTES = W * 2
    FRAME_BYTES = ROW_BYTES * H

    base = spidisplay.buffer_size()
    ring = region[base:base + FRAME_BYTES]
    bg_rgb = (BG.r, BG.g, BG.b)
    src_rgb = (SRC.r, SRC.g, SRC.b)

    print(f"screen {W}x{H} at 16-bit, band_rows {screen.display.band_rows()},"
          f" a frame is {FRAME_BYTES} bytes")

    # Preflight, as in check_sheet_sources.py: the ring has to hold a whole frame
    # in row order or every byte verdict below is void.
    ring_usable = True
    claim = screen.display.sram_bytes()
    if claim < FRAME_BYTES:
        print(f"PREFLIGHT: claim {claim} is short of one frame ({FRAME_BYTES}).")
        ring_usable = False
    if screen.display.band_rows() * 2 != H:
        print(f"PREFLIGHT: {screen.display.band_rows()} band rows is not half of {H}.")
        ring_usable = False
    if ring_usable:
        halves = image(W, H)
        halves.pen = SRC
        halves.rectangle(0, 0, W, H // 2)
        halves.pen = BG
        halves.rectangle(0, H // 2, W, H // 2)
        screen.update(halves, rotation=0, offset=(0, 0))
        want_first = pack565(*src_rgb) * (W * (H // 2))
        if bytes(ring[:len(want_first)]) == want_first:
            print("PREFLIGHT: ring is in row order, first slot holds the top half")
        else:
            print("PREFLIGHT: the ring's first slot is not the frame's top half.")
            ring_usable = False
        del halves, want_first
        gc.collect()
    if not ring_usable:
        print("PREFLIGHT: converted-byte verdicts are N/A, see above")

    def check_frame(name, want):
        """Compare the ring against a modelled frame."""
        print(f"\n{name}:")
        if not ring_usable:
            verdict("N/A", "the ring could not be trusted, see preflight")
            return
        got = bytes(ring[:len(want)])
        if got == want:
            verdict("PASS", f"all {len(want)} converted bytes match the model")
            return
        count, at = first_diff(got, want, ROW_BYTES)
        verdict("FAIL", f"{count} bytes differ, first at row {at[0]} column {at[1]}:"
                        f" got {got[at[0] * ROW_BYTES + at[1] * 2:][:2]},"
                        f" want {want[at[0] * ROW_BYTES + at[1] * 2:][:2]}")

    # A full-panel source whose alpha ramps 0..255 across the width. None of it
    # reaches the conversion, so every column must convert to the source colour.
    print("\n--- direct RGBA source, alpha ignored ---")
    canvas = image(W, H)
    fill_rgba(canvas, ramp_row(W, src_rgb))
    screen.update(canvas, rotation=0, offset=(0, 0), bg_color=BG)
    check_frame("alpha ramp 0..255 converts as fully opaque",
                pack565(*src_rgb) * (W * H))

    # And without the model: the same colours at opposite alpha, over different
    # backgrounds, must still land on the same bytes.
    fill_rgba(canvas, flat_row(W, src_rgb, 255))
    screen.update(canvas, rotation=0, offset=(0, 0), bg_color=BG)
    on_bg = bytes(ring[:FRAME_BYTES])
    fill_rgba(canvas, flat_row(W, src_rgb, 0))
    screen.update(canvas, rotation=0, offset=(0, 0), bg_color=BG_OTHER)
    on_other = bytes(ring[:FRAME_BYTES])
    print("\nalpha and background change nothing:")
    if not ring_usable:
        verdict("N/A", "the ring could not be trusted, see preflight")
    elif on_bg == on_other:
        verdict("PASS", "alpha 255 and alpha 0 convert identically")
    else:
        count, at = first_diff(on_bg, on_other, ROW_BYTES)
        verdict("FAIL", f"{count} bytes differ, first at row {at[0]} column {at[1]}")
    del canvas
    gc.collect()

    # A palettised source composites in its colour table, so a transparent entry
    # has to reach the glass as background and a translucent one part way there.
    print("\n--- palettised source, composited ---")
    try:
        sprite = image.load(INDEXED_PATH)
    except BUILD_ERRORS as e:
        print(f"{INDEXED_PATH}: N/A  could not load it: {type(e).__name__}: {e}")
        tally["N/A"] += 1
        sprite = None

    if sprite is not None and sprite.palette is None:
        print(f"{INDEXED_PATH}: N/A  loaded as truecolour, so it carries no table")
        tally["N/A"] += 1
        sprite = None

    if sprite is not None:
        palette = bytes(memoryview(sprite.palette))
        indices = bytes(memoryview(sprite))
        used = sorted({indices[y * sprite.stride + x]
                       for y in range(sprite.height) for x in range(sprite.width)})
        alphas = sorted({palette[i * 4 + 3] for i in used})
        print(f"{sprite.width}x{sprite.height}, stride {sprite.stride},"
              f" {len(used)} entries used, alphas {alphas[0]}..{alphas[-1]}")
        if 0 not in alphas:
            print("  note: no transparent entry, so the lower endpoint is untested")
        if not any(0 < a < 255 for a in alphas):
            print("  note: no translucent entry, so premultiplied and straight"
                  " alpha would agree and this case cannot tell them apart")

        # Composite each entry here, exactly as prepare_palette() does, then place
        # the image at the origin over a background-filled frame.
        table = [composite((palette[i * 4], palette[i * 4 + 1], palette[i * 4 + 2]),
                           bg_rgb, palette[i * 4 + 3])
                 for i in range(len(palette) // 4)]
        bg_packed = pack565(*bg_rgb)
        want = bytearray(bg_packed * (W * H))
        for y in range(sprite.height):
            row = b"".join(table[indices[y * sprite.stride + x]]
                           for x in range(sprite.width))
            want[y * ROW_BYTES:y * ROW_BYTES + len(row)] = row

        screen.update(sprite, rotation=0, offset=(0, 0), bg_color=BG)
        check_frame("palette alpha composites over the background", bytes(want))
        del want, table, sprite
        gc.collect()

    print(f"\n{tally['PASS']} PASS, {tally['FAIL']} FAIL, {tally['N/A']} N/A")
finally:
    if screen is not None:
        screen.update(image(W, H), bg_color=color.black)
    mighty.shutdown()
