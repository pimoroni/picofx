from picovector import color, image

"""
Drawing: Alternating images
Two pictures in turn, each shown for its own time.
Section: Pictures
"""

# Entry: screenA: graphics file=alternating_images.py fps=20

# Constants
IMAGE_FOLDER = "/examples/assets"           # The folder the images are in
FIRST_IMAGE = "gold_macaw_card.png"         # The name of the first image
SECOND_IMAGE = "red_macaw_card.png"         # The name of the second image
FIRST_MS = 1500                             # How long the first image is shown for
SECOND_MS = 500                             # And the second
BACKGROUND = color.black                    # Around a picture smaller than the panel

try:
    first_image = image.load(f"{IMAGE_FOLDER}/{FIRST_IMAGE}")
    second_image = image.load(f"{IMAGE_FOLDER}/{SECOND_IMAGE}")
except (ValueError, OSError):
    raise RuntimeError(f"'{IMAGE_FOLDER}/{FIRST_IMAGE}' or '{IMAGE_FOLDER}/{SECOND_IMAGE}' is missing or corrupt! Check both are on the drive") from None

shown = None


def place(canvas, picture):
    """Draw one picture centred on the canvas, the background round it."""
    canvas.pen = BACKGROUND
    canvas.clear()
    canvas.blit(picture, (canvas.width - picture.width) // 2, (canvas.height - picture.height) // 2)


def draw(canvas, elapsed):
    global shown
    # One turn is both dwells, the first picture for its share and the second for the rest
    showing_second = int(elapsed * 1000) % (FIRST_MS + SECOND_MS) >= FIRST_MS

    # The canvas keeps the picture, so it is only drawn again when the turn changes
    if showing_second != shown:
        place(canvas, second_image if showing_second else first_image)
        shown = showing_second
