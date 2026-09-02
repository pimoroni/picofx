# examples/mighty_fx/examples/screens/slideshow_from_flash.py, decoding into a
# pre-allocated RGBA8888 image instead of allocating one per frame.
#
# The point is the palette route. image.load() on an indexed PNG returns a
# palettised image: one byte of palette index per pixel plus a 256-entry palette,
# which update() cannot read, so it raises. load_into() an existing image keeps that
# image's mode, which takes the decoder's RGBA expansion branch and produces a
# four-byte-per-pixel frame update() can convert. This confirms that path end to end.
#
# The preflight says so in numbers rather than leaving it to the picture: it loads
# the first image both ways and reports has_palette for each, so a run against a
# folder of truecolour PNGs cannot be mistaken for a successful conversion.
#
# Two side effects worth knowing, since they are the reason this is not simply the
# better example. The image is allocated once, so per-frame allocation and its
# collection go away. And load_into() decodes to the size of the image it is given,
# so the half-size scaling comes from the allocation rather than from load()'s
# arguments.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across,
# along with a folder of PNGs, to run it.

import os
import time

from mighty_fx import SPCE, MightyFX
from timing import Pacer
from screens import Screen280
from picovector import color, image

# Constants
IMAGE_FOLDER = "/frames"    # The folder on your Mighty FX that the images are stored in
IMAGE_WIDTH = 320           # The width the images are stored at, in pixels
IMAGE_HEIGHT = 240          # The height the images are stored at, in pixels
SLEEP_DELAY_MS = 100        # How long each image is displayed for, in milliseconds

# Raised when picovector cannot read a file, or refuses the source.
LOAD_ERRORS = (ValueError, TypeError, MemoryError, OSError)

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)


# Attempt to find all images in the given folder, keeping only their paths
paths = []
try:
    files = sorted(os.listdir(IMAGE_FOLDER))
except OSError:
    files = []

for file in files:
    file = file.rsplit("/", 1)[-1]
    try:
        name, ext = file.rsplit(".", 1)
        if ext.lower() == "png":
            paths.append(f"{IMAGE_FOLDER}/{name}.{ext}")
    except ValueError:
        pass

if len(paths) == 0:
    raise RuntimeError(f"No images found! Copy valid PNGs to your '{IMAGE_FOLDER}' folder (create it if missing)")


# Decode at half size, which is a quarter of the pixels to read from flash. This
# image is RGBA8888 and stays so, which is what makes load_into() the conversion.
canvas = image(IMAGE_WIDTH // 2, IMAGE_HEIGHT // 2)


def preflight(path):
    """Report the mode each route produces for the same file."""
    print(f"preflight on {path}")

    try:
        loaded = image.load(path, IMAGE_WIDTH // 2, IMAGE_HEIGHT // 2)
    except LOAD_ERRORS as e:
        print(f"  image.load():  failed, {type(e).__name__}: {e}")
        return
    direct = getattr(loaded, "has_palette", None)
    del loaded

    try:
        canvas.load_into(path)
    except LOAD_ERRORS as e:
        print(f"  load_into():   failed, {type(e).__name__}: {e}")
        return
    into = getattr(canvas, "has_palette", None)

    if direct is None or into is None:
        print("  has_palette is not exposed by this build, so the modes cannot be"
              " compared. The frames below still say whether load_into() works.")
        return

    print(f"  image.load():  has_palette {direct}")
    print(f"  load_into():   has_palette {into}")
    if direct and not into:
        print("  This is the case under test: indexed on disk, RGBA8888 after"
              " load_into(). A clean slideshow below confirms the conversion.")
    elif direct:
        print("  load_into() left it palettised, so update() will reject it. Not the"
              " expected outcome.")
    else:
        print("  These PNGs are not indexed, so nothing is being converted and a"
              " clean slideshow proves nothing. Use a palette-mode PNG.")


preflight(paths[0])

index = -1  # Start with -1 so that the first image gets shown
frames = 0
started = time.ticks_ms()
pacer = Pacer(SLEEP_DELAY_MS / 1000)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    print(f"\nplaying {len(paths)} images, boot to stop")
    while not mighty.boot_pressed():
        # Move along to the next image index, and wrap it into the range of available images
        index = (index + 1) % len(paths)

        # Decode over the same RGBA8888 buffer, which converts an indexed PNG
        canvas.load_into(paths[index])

        # Update the screen with the latest image, doubling it back up to full size
        screen.update(canvas, rotation=90, mirror=False, pixel_double=True,
                      bg_color=color.white)
        frames += 1

        # Have the image shown for the rest of its time, if any is left
        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    total = time.ticks_diff(time.ticks_ms(), started)
    if frames and total:
        per_frame = total / frames
        print(f"{frames} frames in {total} ms, {frames * 1000 / total:.2f} fps,"
              f" {per_frame:.1f} ms per frame against a {SLEEP_DELAY_MS} ms target")
        if per_frame > SLEEP_DELAY_MS:
            print("  Over the target, so the delay never fired and this is flat out.")
        s = screen.display.stats()
        print(f"  last update(): convert {s.convert_total_us / 1000:.1f} ms,"
              f" stall {s.stall_us / 1000:.1f} ms, {screen.display.band_rows()} rows per band,"
              f" {screen.display.baudrate()} Hz")
        if s.stall_us > s.convert_total_us:
            print("  Stall exceeds convert, so the frame is bound by the wire and not"
                  " by conversion. Decode is whatever is left of the frame time.")
    mighty.shutdown()
