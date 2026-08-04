# Checks which sources update() accepts and which it rejects, readiness item 2.
#
# update() walks src_h rows of the pitch the image reports, at four bytes per
# pixel (one for a palettised source), so a buffer shorter than that extent is
# read out of bounds. The guard should turn that into a ValueError. This checks
# both halves: that it fires on every bad source, and that it stays out of the
# way of the sources the shipped examples actually use.
#
# The preflight runs first because it decides what the rest of the run can mean. A
# source that reports its nominal size rather than the length of the buffer it
# wraps leaves update() comparing a number with itself, so every short case FAILs
# no matter how the guard is written. The dimension cases are unaffected and are
# what shows whether the guard is in the firmware at all.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across
# to run it.
#
# On a build without the guard a short source can lock the board outright, so each
# case prints its name before it runs and its verdict after. A line with a name and
# no verdict is the case that locked, and that lock is the out-of-bounds read.
# Add that name to SKIP and re-run to get past it and finish the matrix.
#
# Worth running unguarded first, to see which short cases are reachable at all. A
# case picovector refuses to build reports N/A and proves nothing either way, so
# the ones that FAIL unguarded are the ones that have to PASS guarded.

import gc

import spidisplay
from mighty_fx import SPCE, MightyFX
from screens import Screen280
from picovector import color, image

SCREEN = Screen280

# Case names to skip, for stepping past one that locks an unguarded build.
SKIP = ("empty buffer",)

# Raised if picovector or spidisplay.buffer validates a length itself. That is a
# different outcome from a guard failing to fire, so it is counted apart.
BUILD_ERRORS = (ValueError, TypeError, MemoryError, OSError)

# The preflight probe also tolerates an image type that exposes no buffer at all.
PROBE_ERRORS = BUILD_ERRORS + (AttributeError,)

mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = SCREEN(mighty.spce_a)
screen.brightness = 1.0

WIDTH, HEIGHT = screen.width, screen.height
EXACT_BYTES = WIDTH * HEIGHT * 4    # RGBA8888, the length update() infers

tally = {"PASS": 0, "FAIL": 0, "N/A": 0, "SKIP": 0}
drawn = 0
length_check_can_fire = True    # Set by the preflight

# The dimension cases do not depend on the reported buffer length, so they are the
# ones that say whether the guard is in the firmware at all. Tracked separately.
dimension_results = []


def build(width, height, nbytes):
    """An image of these dimensions over a buffer of nbytes, or the reason why not.

    Which buffer types picovector wraps is its business, so both the GC heap and
    the SRAM region are tried before a case is called unconstructible.
    """
    reasons = []
    for kind in ("bytearray", "spidisplay.buffer"):
        try:
            if kind == "bytearray":
                buffer = bytearray(nbytes)
            else:
                buffer = spidisplay.buffer(nbytes)
        except BUILD_ERRORS as e:
            reasons.append(f"{kind} of {nbytes} bytes: {type(e).__name__}: {e}")
            continue
        try:
            return image(width, height, buffer), None
        except BUILD_ERRORS as e:
            reasons.append(f"image() over {kind}: {type(e).__name__}: {e}")
    return None, "; ".join(reasons)


def verdict(kind, detail, group=None):
    tally[kind] += 1
    if group == "dimension":
        dimension_results.append(kind)
    print(f"{kind}  {detail}")


def check(name, expect_raise, img, build_error=None, rotation=0,
          on_accept="read out of bounds", group=None):
    """Update with img and report whether the guard behaved as expected.

    on_accept describes what accepting this source means, since a short buffer and
    a degenerate extent are wrong in different ways. group tags a case so the
    summary can weigh the dimension cases on their own.
    """
    global drawn

    if name in SKIP:
        verdict("SKIP", "listed in SKIP", group)
        return
    if img is None:
        verdict("N/A", build_error, group)
        return

    # Only a frame that should reach the panel is worth painting, and a degenerate
    # image is not worth handing to picovector's own drawing calls.
    if not expect_raise:
        img.pen = color.hsv(drawn * 24 % 256, 255, 255)
        img.clear()
        drawn += 1

    try:
        screen.update(img, rotation=rotation)
    except ValueError as e:
        if expect_raise:
            verdict("PASS", f"ValueError: {e}", group)
        else:
            verdict("FAIL", f"rejected a source that should draw. ValueError: {e}", group)
        return
    except BUILD_ERRORS as e:
        verdict("FAIL", f"unexpected {type(e).__name__}: {e}", group)
        return

    if expect_raise:
        verdict("FAIL", f"update() accepted it, so it {on_accept}", group)
    else:
        verdict("PASS", "drew", group)


def case(name, expect_raise, width, height, nbytes, rotation=0,
         on_accept="read out of bounds", group=None):
    """Announce the case, then build and run it."""
    print(f"  {name}: ", end="")
    gc.collect()
    img, build_error = build(width, height, nbytes)
    check(name, expect_raise, img, build_error, rotation, on_accept, group)


def ready_case(name, expect_raise, img):
    """A case whose image is already built, so it cannot report N/A."""
    print(f"  {name}: ", end="")
    check(name, expect_raise, img)


def preflight():
    """Report whether an image's buffer length tracks the buffer it wraps.

    update() compares the length it is handed against width * height * 4. If
    picovector reports the nominal image size instead of the wrapped buffer's own
    length, those are the same number and the length half of the guard cannot
    fire, whatever the rest of this run says.
    """
    global length_check_can_fire

    probe_bytes = 64
    try:
        probe = image(WIDTH, HEIGHT, bytearray(probe_bytes))
        reported = len(memoryview(probe))
    except PROBE_ERRORS as e:
        print(f"  inconclusive: {type(e).__name__}: {e}")
        return
    length_check_can_fire = reported == probe_bytes
    if length_check_can_fire:
        print(f"  length tracks the buffer, {reported} bytes reported for {probe_bytes}."
              " The length check can fire.")
    else:
        print(f"  length is nominal, {reported} bytes reported for a {probe_bytes} byte"
              " buffer. The length check compares that number with itself, so it"
              " cannot fire and every short source below is expected to FAIL.")


print(f"screen {WIDTH}x{HEIGHT}, {EXACT_BYTES} bytes at RGBA8888")
print(f"SRAM region available: {spidisplay.buffer_size()} bytes")
if SKIP:
    print(f"skipping: {', '.join(SKIP)}")

print("\nwhat update() is told about a short buffer")
preflight()

# Sources the examples use. None of these may start raising.
print("\nsources that must draw")
gc.collect()
ready_case("plain image(), PSRAM", False, image(WIDTH, HEIGHT))
gc.collect()
ready_case("screen.canvas(), SRAM", False, screen.canvas())
case("exact backing buffer", False, WIDTH, HEIGHT, EXACT_BYTES)
case("buffer with 64 bytes spare", False, WIDTH, HEIGHT, EXACT_BYTES + 64)
case("source smaller than the screen", False, WIDTH // 2, HEIGHT // 2,
     (WIDTH // 2) * (HEIGHT // 2) * 4)
case("1x1 source", False, 1, 1, 4)


# A palettised source draws through its colour table, so it must be accepted
# like any other; built apart from ready_case, which would paint over it.
def palettised_case(path="/images/anim_solid.gif"):
    print("  animated GIF frame, palettised: ", end="")
    gc.collect()
    try:
        frame = image.load(path).spritesheet().sprite(0, 0)
    except BUILD_ERRORS as e:
        verdict("N/A", f"could not load {path}: {type(e).__name__}: {e}")
        return
    try:
        screen.update(frame, rotation=0)
    except BUILD_ERRORS as e:
        verdict("FAIL", f"rejected a palettised frame. {type(e).__name__}: {e}")
        return
    verdict("PASS", "drew")


palettised_case()

# Short sources, ordered least to most likely to fault on an unguarded build. The
# one byte case is the bound itself: src_w * src_h * 4 is exact, because the
# covered box is clamped to the source extent, so one byte less has to be
# rejected. An empty buffer has no meaningful data pointer, so an unguarded build
# converts a whole frame from wherever that lands.
print("\nshort sources that must raise")
case("one byte short", True, WIDTH, HEIGHT, EXACT_BYTES - 1)
case("half length, the RGBA4444 shape", True, WIDTH, HEIGHT, EXACT_BYTES // 2)
case("1x1 source with 3 bytes", True, 1, 1, 3)
case("empty buffer", True, WIDTH, HEIGHT, 0)

# The guard runs before the transform is resolved, so rotation must not change the
# verdict. 90 and 270 also reach the column cache, which copies from the source on
# its own account.
print("\nshort source at every rotation")
for angle in (0, 90, 180, 270):
    case(f"half length at rotation {angle}", True, WIDTH, HEIGHT,
         EXACT_BYTES // 2, rotation=angle)

# Degenerate extents convert to a frame of solid background without the guard,
# because the covered box comes out empty and no source pixel is read. So these
# are safe to run unguarded, and expected to FAIL there.
print("\ndegenerate dimensions that must raise")
case("zero width", True, 0, HEIGHT, EXACT_BYTES,
     on_accept="silently drew a background frame", group="dimension")
case("zero height", True, WIDTH, 0, EXACT_BYTES,
     on_accept="silently drew a background frame", group="dimension")

# The guard raises before update() asserts CS or writes RAMWR, so a rejected frame
# must leave the panel able to draw the next one.
print("\nthe bus survives a rejection")
gc.collect()
ready_case("draw after the rejections", False, screen.canvas())

print(f"\n{tally['PASS']} passed, {tally['FAIL']} failed,"
      f" {tally['N/A']} not constructible, {tally['SKIP']} skipped")

if tally["N/A"]:
    print("An N/A case is unreachable from Python by that route, so it says nothing"
          " about the guard either way.")

if not length_check_can_fire:
    # The dimension cases are the only ones a nominal length cannot mask, so they
    # decide whether the guard is present.
    decided = [kind for kind in dimension_results if kind in ("PASS", "FAIL")]
    if not decided:
        print("No dimension case reached update(), so this run cannot say whether the"
              " guard is in the firmware.")
    elif all(kind == "PASS" for kind in decided):
        print("The guard is in this firmware: the dimension cases pass. The short cases"
              " cannot pass while the source reports its nominal size, so the length"
              " half needs fixing where the buffer is wrapped, not here.")
    else:
        print("The guard is absent from this firmware: the dimension cases fail, and"
              " they do not depend on the reported length. The short cases say nothing"
              " while the source reports its nominal size.")
elif tally["FAIL"]:
    print("Expected on a build without the guard. On a build with it, a defect.")
else:
    print("The guard behaves as intended on this panel.")
