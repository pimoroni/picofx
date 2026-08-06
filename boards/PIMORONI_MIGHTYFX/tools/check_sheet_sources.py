# Checks whether a spritesheet cell converts to the right pixels.
#
# check_update_sources.py asks which sources update() accepts. This asks whether an
# accepted one comes out right, which is a different question: a sheared cell is
# accepted, converts, streams, and is wrong.
#
# The verdict is the converted bytes, not the panel. Bands are claimed from the top
# of the SRAM arena and buffer(nbytes, offset) names an address without claiming, so
# a whole-region memoryview taken before the screen exists still addresses the bands
# afterwards. Sizing the bands at half the panel height makes the frame exactly two
# slots, so no slot is reused mid-frame and the ring holds the whole converted frame
# in panel byte order. That is compared against a packing computed here.
#
# Cells are full panel size, so nothing is centred and no background is involved:
# the model is the cell's own pixels and nothing else. Each cell is vertical bars,
# constant down the cell, so one 480-byte row template repeated 320 times is the
# whole expected frame, and a stride error moves bars sideways per row where both
# the arithmetic and the eye can see it.
#
# What this cannot decide: rotation and mirror sense, because the model and the
# kernel would share any wrong idea of clockwise; and rotation 90/270, because the
# ring layout needs cache_columns=0 and those rotations want the cache. Both are
# rotation 0 only here, and eyes elsewhere.
#
# A walking tear line on the glass is expected. These settings serve the readback,
# not the panel: 16-bit at 24MHz streams a frame in about 56ms against a ~44ms
# two-refresh budget, so the scan laps every write, v_sync on or not. The verdict
# is the ring bytes; ignore the glass.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across to
# run it. The GIF cases need an asset:
#   python3 -B .claude/assets/make_anim_gif.py anim_solid.gif
#   mpr.ps1 fs cp anim_solid.gif :/images/anim_solid.gif      (fs cp, NOT -Stage)

import gc

import spidisplay
from mighty_fx import SPCE, MightyFX
from screens import Screen280
from picovector import color, image

GIF_PATH = "/images/anim_solid.gif"
GIF_WIDE_PATH = "/images/anim6.gif"

# Bars, constant down a cell. The period is what a shear shifts, so keep it wide
# enough to read and narrow enough that a one-cell slip cannot alias to itself.
BAR_W = 20
PHASE_STEP = 10          # Per cell, so two cells never draw the same bars.

CELL_COLORS = (
    color.rgb(255, 0, 0),
    color.rgb(0, 255, 0),
    color.rgb(0, 0, 255),
    color.rgb(255, 255, 0),
    color.rgb(255, 0, 255),
    color.rgb(0, 255, 255),
)
BAR_BG = color.rgb(0, 0, 0)

# Raised when picovector or update() declines a case. That is a result for some
# cases and a void run for others, so it is always reported apart from a verdict.
BUILD_ERRORS = (ValueError, TypeError, MemoryError, OSError, AttributeError)

# Cases that would hang rather than fail. None known; kept so a future one has a
# home and does not have to be found twice.
SKIP = ()

tally = {"PASS": 0, "FAIL": 0, "N/A": 0, "SKIP": 0}


def pack565(c):
    """One RGB565 pixel, big-endian, as the kernel's packer emits it."""
    r, g, b = c.r, c.g, c.b
    v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    return bytes((v >> 8, v & 0xff))


def bar_row(width, index):
    """One row of cell `index`: vertical bars of its colour on black.

    Every row of a cell is this, so the expected frame is this repeated.
    """
    fg = CELL_COLORS[index % len(CELL_COLORS)]
    phase = (index * PHASE_STEP) % (BAR_W * 2)
    row = bytearray()
    fg_packed = pack565(fg)
    bg_packed = pack565(BAR_BG)
    for x in range(width):
        row += fg_packed if ((x + phase) // BAR_W) % 2 == 0 else bg_packed
    return bytes(row)


def paint_cell(target, x0, y0, w, h, index):
    """Paint cell `index` into target at (x0, y0), matching bar_row()."""
    fg = CELL_COLORS[index % len(CELL_COLORS)]
    phase = (index * PHASE_STEP) % (BAR_W * 2)
    target.pen = BAR_BG
    target.rectangle(x0, y0, w, h)
    target.pen = fg
    for x in range(w):
        if ((x + phase) // BAR_W) % 2 == 0:
            target.vspan(x0 + x, y0, h)


def stride_of(view):
    """Whether a contiguous walk of this view's bytes samples the view itself.

    image(w, h, memoryview(view)) is exactly the pitch update() infers, so this
    compares the view against that assumption over its own bytes and predicts
    nothing about what either holds. Returns (agrees, detail).
    """
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


# An arena claim outlives a soft reset, so a leak from an earlier run would leave
# the screen below short of its bands. shutdown() gives this run's claim back.
spidisplay.release_buffers()

mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = None
try:
    # Taken before the screen exists, so it spans the whole region including the
    # bands the screen is about to claim from the top of it. The offset form places
    # the view by address, leaving the arena for the screen to claim from.
    arena = spidisplay.buffer_size()
    region = spidisplay.buffer(arena, 0)

    screen = Screen280(mighty.spce_a, bitdepth=16, band_lines=160, cache_columns=0)
    screen.brightness = 1.0
    W, H = screen.width, screen.height
    ROW_BYTES = W * 2
    FRAME_BYTES = ROW_BYTES * H

    base = spidisplay.buffer_size()
    claim = screen.display.sram_bytes()
    ring = region[base:base + FRAME_BYTES]

    print(f"screen {W}x{H} at 16-bit, arena {arena}, claim {claim} at {base}")
    print(f"band_rows {screen.display.band_rows()}, a row is {ROW_BYTES} bytes,"
          f" a frame is {FRAME_BYTES}")

    # Preflight. Each of these can void every verdict below, so they run first and
    # say so plainly rather than being folded into a case. The claim is the band
    # ring first, then the display's other scratch (the palette table), so the
    # ring is its first FRAME_BYTES and the claim may run longer.
    ring_usable = True
    if claim < FRAME_BYTES:
        print(f"PREFLIGHT: claim {claim} is short of one frame ({FRAME_BYTES}), so"
              f" the ring holds fewer rows than a frame. Converted-byte verdicts are N/A.")
        ring_usable = False
    if screen.display.band_rows() * 2 != H:
        print(f"PREFLIGHT: {screen.display.band_rows()} band rows is not half of"
              f" {H}, so a slot is reused mid-frame. Converted-byte verdicts are N/A.")
        ring_usable = False

    # Slot order. Two bands, so the ring is either rows 0..159 then 160..319 or the
    # reverse. A frame whose halves differ settles it without assuming either.
    if ring_usable:
        halves = image(W, H)
        halves.pen = CELL_COLORS[0]
        halves.rectangle(0, 0, W, H // 2)
        halves.pen = CELL_COLORS[2]
        halves.rectangle(0, H // 2, W, H // 2)
        screen.update(halves, rotation=0, offset=(0, 0))
        top = pack565(CELL_COLORS[0])
        want_first = top * (W * (H // 2))
        if bytes(ring[:len(want_first)]) == want_first:
            print("PREFLIGHT: ring is in row order, first slot holds the top half")
        else:
            print("PREFLIGHT: the ring's first slot is not the frame's top half, so"
                  " the slot order is not what the model assumes."
                  " Converted-byte verdicts are N/A.")
            ring_usable = False
        del halves, want_first
        gc.collect()

    # The pitch a narrowed cell reports, which is what the cases below turn on.
    probe = image(W * 2, H).spritesheet(2, 1).sprite(0, 0)
    print(f"picovector: a {probe.width}x{probe.height} cell reports stride"
          f" {probe.stride}, against {probe.width * 4} if it were contiguous")
    del probe
    print(f"free memory {gc.mem_free()}")

    def run(name, make, expect_agree):
        """One case: classify the source, then check the bytes it converted to.

        make() returns (view, expected_row_index) or raises. expect_agree is
        whether this view's stride should already match its width.
        """
        if name in SKIP:
            tally["SKIP"] += 1
            print(f"\n{name}: SKIP")
            return
        print(f"\n{name}:")
        gc.collect()
        try:
            view, index = make()
        except BUILD_ERRORS as e:
            tally["N/A"] += 1
            print(f"  N/A  could not build it: {type(e).__name__}: {e}")
            return

        agrees, detail = stride_of(view)
        shape = f"{view.width}x{view.height}, {len(memoryview(view))} bytes"
        if agrees is None:
            print(f"  L1 N/A  {detail}. {shape}")
        elif agrees == expect_agree:
            print(f"  L1 as expected: {'contiguous' if agrees else 'strided'},"
                  f" {detail}. {shape}")
        else:
            print(f"  L1 UNEXPECTED: {'contiguous' if agrees else 'strided'} but the"
                  f" layout says otherwise, {detail}. {shape}")

        if not ring_usable:
            tally["N/A"] += 1
            print("  L2 N/A  the ring could not be trusted, see preflight")
            return
        try:
            screen.update(view, rotation=0, offset=(0, 0))
        except BUILD_ERRORS as e:
            tally["N/A"] += 1
            print(f"  L2 refused: {type(e).__name__}: {e}")
            return

        want = bar_row(W, index) * H
        count, at = first_diff(bytes(ring), want, ROW_BYTES)
        if count == 0:
            tally["PASS"] += 1
            print(f"  L2 PASS  all {FRAME_BYTES} bytes match the cell's own pixels")
        else:
            tally["FAIL"] += 1
            pct = count * 100 // FRAME_BYTES
            print(f"  L2 FAIL  {count} of {FRAME_BYTES} bytes differ ({pct}%),"
                  f" first at row {at[0]} column {at[1]}")

    # The control. A plain full-size image is unaffected by anything here, so a
    # failure means the model or the ring is wrong and nothing else can be read.
    def plain():
        img = image(W, H)
        paint_cell(img, 0, 0, W, H, 0)
        return img, 0
    run("control, plain full-size image", plain, True)

    # One column of full-panel cells. Each cell's width is its parent's, so its
    # stride already equals width * 4 and it should draw correctly untouched.
    def vertical(k, rows=4):
        parent = image(W, H * rows)
        for i in range(rows):
            paint_cell(parent, 0, i * H, W, H, i)
        return parent.spritesheet(1, rows).sprite(0, k), k
    run("1 column x 4 rows, cell 0", lambda: vertical(0), True)
    run("1 column x 4 rows, cell 3", lambda: vertical(3), True)

    # Cells side by side. The parent row is four cells wide, so a cell's rows are
    # four times further apart than its width claims.
    def horizontal(k, cols=4):
        parent = image(W * cols, H)
        for i in range(cols):
            paint_cell(parent, i * W, 0, W, H, i)
        return parent.spritesheet(cols, 1).sprite(k, 0), k
    run("4 columns x 1 row, cell 0", lambda: horizontal(0), False)
    run("4 columns x 1 row, cell 3", lambda: horizontal(3), False)

    # A grid, so the cell's origin is neither the parent's nor on its first row.
    def rectangular():
        cols, rows = 2, 3
        parent = image(W * cols, H * rows)
        for y in range(rows):
            for x in range(cols):
                paint_cell(parent, x * W, y * H, W, H, y * cols + x)
        return parent.spritesheet(cols, rows).sprite(1, 2), 2 * cols + 1
    run("2 columns x 3 rows, cell (1, 2)", rectangular, False)

    # A grid that does not divide its parent. The remainder is unreachable, which
    # is reported rather than judged: it is picovector's documented truncation.
    def non_dividing():
        cols = 7
        parent = image(W * cols + 13, H)
        for i in range(cols):
            paint_cell(parent, i * W, 0, W, H, i)
        sheet = parent.spritesheet(cols, 1)
        cell = sheet.sprite(0, 0)
        print(f"  cell width {cell.width} x {cols} = {cell.width * cols} of"
              f" {parent.width}, {parent.width - cell.width * cols} columns"
              f" unreachable")
        return cell, 0
    run("7 columns over a non-dividing width", non_dividing, False)

    # A grid larger than its parent gives a zero extent, which update() must refuse
    # rather than draw as a frame of background.
    print("\ngrid larger than the image:")
    try:
        tiny = image(W, H).spritesheet(W * 2, 1).sprite(0, 0)
        print(f"  cell is {tiny.width}x{tiny.height}")
        try:
            screen.update(tiny, rotation=0, offset=(0, 0))
            tally["FAIL"] += 1
            print("  FAIL  a zero-extent cell was accepted and drawn")
        except ValueError as e:
            tally["PASS"] += 1
            print(f"  PASS  refused: {e}")
    except BUILD_ERRORS as e:
        tally["N/A"] += 1
        print(f"  N/A  {type(e).__name__}: {e}")

    # The GIFs. Palettised horizontal strips, so a frame exercises the indexed
    # path and the stride at once. Every frame is one solid colour, so the
    # expected bytes are computable without a reference image: the view's own
    # colours over its extent at (0, 0), background everywhere else.
    def want_solid(c, cw, ch):
        fg, bg = pack565(c), pack565(BAR_BG)
        cw, ch = min(cw, W), min(ch, H)
        cell_row = fg * cw + bg * (W - cw)
        return cell_row * ch + bg * W * (H - ch)

    def gif_case(label, view, want):
        gc.collect()
        try:
            screen.update(view, rotation=0, offset=(0, 0))
        except BUILD_ERRORS as e:
            tally["FAIL"] += 1
            print(f"  {label}: FAIL  refused: {type(e).__name__}: {e}")
            return
        if not ring_usable:
            tally["N/A"] += 1
            print(f"  {label}: N/A  the ring could not be trusted, see preflight")
            return
        count, at = first_diff(bytes(ring), want, ROW_BYTES)
        if count == 0:
            tally["PASS"] += 1
            print(f"  {label}: PASS  all {FRAME_BYTES} bytes match")
        else:
            tally["FAIL"] += 1
            pct = count * 100 // FRAME_BYTES
            print(f"  {label}: FAIL  {count} of {FRAME_BYTES} bytes differ ({pct}%),"
                  f" first at row {at[0]} column {at[1]}")

    def gif_run(path, hint):
        print(f"\nGIF from {path}:")
        gc.collect()
        try:
            gif = image.load(path)
            sheet = gif.spritesheet()
        except BUILD_ERRORS as e:
            tally["N/A"] += 1
            print(f"  N/A  {type(e).__name__}: {e}")
            print(f"  generate it with '{hint}' and copy with"
                  f" 'mpr.ps1 fs cp <out> :{path}' (fs cp, NOT -Stage)")
            return
        print(f"  loaded {type(gif).__name__} {gif.width}x{gif.height},"
              f" frames {sheet.sprites}, palette {gif.palette_size} entries,"
              f" buffer {len(memoryview(gif))} bytes")

        # The whole strip is a contiguous indexed source: its visible columns
        # are the frames' colours side by side.
        fw = gif.width // sheet.sprites
        vis = min(gif.width, W)
        row = b"".join(pack565(CELL_COLORS[x // fw]) for x in range(vis))
        row += pack565(BAR_BG) * (W - vis)
        ch = min(gif.height, H)
        gif_case("whole strip", gif,
                 row * ch + pack565(BAR_BG) * W * (H - ch))

        # First and last frames: strided indexed cells, the last one's origin
        # deep in the strip and its extent ending exactly at the buffer's.
        for i in (0, sheet.sprites - 1):
            gif_case(f"frame {i}", sheet.sprite(i, 0),
                     want_solid(CELL_COLORS[i], fw, gif.height))

    gif_run(GIF_PATH, "make_anim_gif.py anim_solid.gif")
    # The wide strip: a cell of a 5-frames-or-wider strip reports a buffer
    # extent past its nominal w*h*4, the shape that once slipped a nominal
    # length check as an unconverted read.
    gif_run(GIF_WIDE_PATH, "make_anim_gif.py anim6.gif 64 6")

    print(f"\n{tally['PASS']} passed, {tally['FAIL']} failed,"
          f" {tally['N/A']} inconclusive, {tally['SKIP']} skipped")

    if tally["N/A"] and not tally["PASS"]:
        print("Nothing was measured, so this run says nothing about any source.")
    elif tally["N/A"] and not tally["FAIL"]:
        print("No converted bytes disagreed, but the inconclusive cases above limit"
              " what this run covers.")
    elif tally["FAIL"]:
        print("The failures are the point on a firmware that infers a cell's pitch"
              " from its width: every case whose cell is narrower than its parent"
              " should differ, and the control and the one-column cases should not."
              " Read the L1 lines first: if a case's classification is UNEXPECTED,"
              " its L2 verdict is about something other than the stride.")
    else:
        print("Every source converted to its own pixels exactly, including the ones"
              " whose stride differs from their width, so update() is being told the"
              " real pitch.")
finally:
    if screen is not None:
        screen.brightness = 0.0
    mighty.shutdown()
