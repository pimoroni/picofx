# Checks whether update() honours a sub-view's row stride.
#
# picovector's window() and sprite() return a view that shares the parent's pixels:
# the bounds narrow to the sub-rect but the row stride stays the parent's, so
# successive rows of the view are parent_width * 4 bytes apart. update() is not told
# that. make_descriptor takes the width the object reports and computes
# src_row_bytes = src_w * 4 (scanline.hpp:384), so it walks the view as if its rows
# were contiguous and samples progressively further along the parent.
#
# It stays inside the parent's buffer, so this is a wrong picture rather than a
# fault, and the length guard passes because the reported buffer size narrows to the
# sub-rect the same way the dimensions do.
#
# The arithmetic half is the verdict, and needs no screen and no eyes:
# image(w, h, mv) over the view's own memoryview is exactly update()'s assumption, a
# contiguous walk of the same bytes from the same origin. Reading it back through
# picovector's own get() reports what the kernel would sample, and comparing that
# against the view itself, which does honour the stride, needs no prediction about
# what either one should contain.
#
# The visual half is a demonstration, not the verdict, and how legible it is depends
# entirely on the view's width.
#
# A half-width view drifts by exactly one row per row: model row r starts where true
# row r/2 does, in one half of the parent or the other, so it reads two cells in
# alternation at a one-row pitch. That is the defect, but at that pitch the panel
# blends the pair into a flat colour: red against green reads as yellow, yellow
# against blue reads as white. Easy to mistake for a solid frame, and it is the
# reason the drift case below exists.
#
# The drift case is two pixels narrower than its parent, so each row starts two
# pixels earlier and vertical bars visibly lean. That is the same defect at a pitch
# the eye can resolve.
#
# A view as wide as its parent is the control: its stride already equals its width,
# so it must come out clean whether or not the defect is present. If that one
# disagrees too, the cause is not the stride.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across to
# run it.

import gc
import time

from mighty_fx import SPCE, MightyFX
from picovector import color, image

SCREEN = SPCE.SCREEN_280

# A 2x2 grid keeps the arithmetic easy to read: a cell is half the parent's width,
# so a contiguous walk lands in the neighbouring cell on every second row.
COLS = 2
ROWS = 2

# Solid, unmistakable, and far enough apart that a packed comparison cannot alias.
CELL_COLORS = (
    color.rgb(255, 0, 0),
    color.rgb(0, 255, 0),
    color.rgb(0, 0, 255),
    color.rgb(255, 255, 0),
)
CELL_NAMES = ("red", "green", "blue", "yellow")

# The drift case's bars, named so a mismatch there reports a colour too.
BAR_BG = color.rgb(0, 0, 0)
BAR_FG = color.rgb(255, 255, 255)
KNOWN_COLORS = CELL_COLORS + (BAR_BG, BAR_FG)
KNOWN_NAMES = CELL_NAMES + ("black", "white")

# Raised when picovector declines to build a case. That says nothing either way, so
# it is reported apart from a real verdict.
BUILD_ERRORS = (ValueError, TypeError, MemoryError, OSError, AttributeError)

# Columns sampled per row. The drift moves whole cells at this grid, so a handful of
# positions across the row catches it, and a full sweep would be thousands of
# get() calls.
SAMPLES_PER_ROW = 4

# Vertical bars for the drift case, wide enough to read at a glance.
BAR_W = 20

SECONDS_PER_VIEW = 4

mighty = MightyFX(spce_a=SCREEN)
screen = mighty.screen_a
mighty.bl_a.on()

WIDTH, HEIGHT = screen.width, screen.height
CELL_W, CELL_H = WIDTH // COLS, HEIGHT // ROWS

tally = {"PASS": 0, "FAIL": 0, "N/A": 0}


def build_sheet():
    """A full-screen canvas painted as a COLS x ROWS grid of solid colours."""
    sheet = image(WIDTH, HEIGHT)
    for row in range(ROWS):
        for col in range(COLS):
            sheet.pen = CELL_COLORS[row * COLS + col]
            sheet.rectangle(col * CELL_W, row * CELL_H, CELL_W, CELL_H)
    return sheet


def build_bars():
    """A half-height canvas of vertical bars, for the drift case.

    The bar period is BAR_W * 2, and the drift is two pixels per row, so the pattern
    realigns every BAR_W rows: expect CELL_H / BAR_W rows to agree by coincidence.
    """
    bars = image(WIDTH, CELL_H)
    bars.pen = BAR_BG
    bars.clear()
    bars.pen = BAR_FG
    for x in range(0, WIDTH, BAR_W * 2):
        bars.rectangle(x, 0, BAR_W, CELL_H)
    return bars


def contiguous_model(view):
    """view's bytes read as if its rows were contiguous, which is update()'s
    assumption. Same origin, same bytes, different stride."""
    return image(view.width, view.height, memoryview(view))


def compare(model, view):
    """Rows where the contiguous walk and the real view disagree.

    Returns (bad_rows, first_bad_row, what the walk read, what is really there). A
    row counts once, at its first differing sample.
    """
    step = max(1, view.width // SAMPLES_PER_ROW)
    bad_rows = 0
    first_bad = -1
    walked_p = 0
    real_p = 0
    for y in range(view.height):
        for x in range(0, view.width, step):
            walked = model.get(x, y).p
            real = view.get(x, y).p
            if walked != real:
                bad_rows += 1
                if first_bad < 0:
                    first_bad = y
                    walked_p = walked
                    real_p = real
                break
    return bad_rows, first_bad, walked_p, real_p


def name_of(packed):
    """The painted colour a packed value belongs to, for reporting.

    A packed colour fills all 32 bits, so an opaque one comes back from .p as a
    negative machine word. Mask before formatting, as st7789.update() does with its
    background colour, or the fallback prints a signed hex value.
    """
    for index, known in enumerate(KNOWN_COLORS):
        if known.p == packed:
            return KNOWN_NAMES[index]
    return f"0x{packed & 0xffffffff:08x}"


def arithmetic(name, view, expect_mismatch):
    """Report whether a contiguous walk of view's bytes samples the view.

    expect_mismatch says whether the stride and the width disagree for this view, so
    the same routine covers the control.
    """
    print(f"  {name}: ", end="")

    stride = getattr(view, "stride", None)
    if stride is None:
        reported = f"{view.width}x{view.height}, stride not exposed"
    else:
        reported = (f"{view.width}x{view.height}, stride {stride}"
                    f" (contiguous would be {view.width * 4})")

    try:
        buffer = memoryview(view)
        model = contiguous_model(view)
    except BUILD_ERRORS as e:
        tally["N/A"] += 1
        print(f"N/A  cannot model it: {type(e).__name__}: {e}")
        return

    bad, first_bad, walked_p, real_p = compare(model, view)
    detail = f"{reported}, {len(buffer)} bytes"

    if bad and expect_mismatch:
        tally["PASS"] += 1
        print(f"PASS  wrong rows as expected: {bad} of {view.height}, first at row"
              f" {first_bad} where the walk reads {name_of(walked_p)} and the view"
              f" holds {name_of(real_p)}. {detail}")
    elif bad:
        tally["FAIL"] += 1
        print(f"FAIL  disagrees, but its stride matches its width so it should not:"
              f" {bad} rows, first at row {first_bad} reading {name_of(walked_p)}"
              f" against {name_of(real_p)}. {detail}")
    elif expect_mismatch:
        tally["PASS"] += 1
        print(f"PASS  agrees, so update() is being told the real stride. {detail}")
    else:
        tally["PASS"] += 1
        print(f"PASS  agrees, as the control must. {detail}")


def show(name, view, looks_like):
    """Put a view on the panel, alongside what a correct frame looks like."""
    print(f"  {name}: correct is {looks_like}")
    try:
        screen.update(view, rotation=0, v_sync=True, bg_color=color.rgb(40, 40, 40))
    except BUILD_ERRORS as e:
        print(f"    rejected: {type(e).__name__}: {e}")
        return
    time.sleep(SECONDS_PER_VIEW)


def views_of(sheet, bars):
    """The cases, as (name, view, expect_mismatch, what a correct frame looks like).

    A cell away from the top left still reads inside the parent: the bytes a
    contiguous walk covers from its origin are fewer than the parent has left.
    """
    cases = [
        ("window, cell (0, 0)", sheet.window(0, 0, CELL_W, CELL_H), True,
         "solid red, not red and green on alternate rows blending to yellow"),
        ("window, cell (1, 1)", sheet.window(CELL_W, CELL_H, CELL_W, CELL_H), True,
         "solid yellow, not yellow and blue on alternate rows blending to white"),
        ("window, two pixels narrow", bars.window(0, 0, WIDTH - 2, CELL_H), True,
         "upright bars, not bars leaning two pixels per row"),
        # The control: as wide as its parent, so its rows really are contiguous.
        ("window, full width", bars.window(0, 0, WIDTH, CELL_H), False,
         "upright bars, and this one must be right either way"),
    ]

    # sprite() is the same sub-view by another route, and the one a user reaches for.
    try:
        sheet.spritesheet(COLS, ROWS)
        cases.append(("sprite (0, 0)", sheet.sprite(0, 0), True,
                      "solid red, as for cell (0, 0)"))
    except BUILD_ERRORS as e:
        print(f"  sprite (0, 0): N/A  {type(e).__name__}: {e}")
        tally["N/A"] += 1
    return cases


print(f"screen {WIDTH}x{HEIGHT}, {COLS}x{ROWS} grid of {CELL_W}x{CELL_H} cells")
print(f"a parent row is {WIDTH * 4} bytes, a cell row is {CELL_W * 4}")

gc.collect()
sheet = build_sheet()
bars = build_bars()

print("\nwhat a contiguous walk of each view samples")
cases = views_of(sheet, bars)
for name, view, expect_mismatch, _ in cases:
    arithmetic(name, view, expect_mismatch)

print("\nthe same views on the panel")
for name, view, _, looks_like in cases:
    show(name, view, looks_like)

print(f"\n{tally['PASS']} passed, {tally['FAIL']} failed, {tally['N/A']} inconclusive")

if tally["N/A"] and not tally["PASS"]:
    print("Nothing was measured, so this run says nothing about the stride.")
elif tally["FAIL"]:
    print("A view whose stride matches its width disagreed with a contiguous walk of"
          " its own bytes, which should be impossible. Check the canvases are painted"
          " as described above before reading anything into the other cases.")
else:
    print("The narrowed views disagree with a contiguous walk of their bytes and the"
          " full-width control does not, which is the stride being inferred from the"
          " width rather than read from the image.")

mighty.shutdown()
