from mighty_fx import MightyFX, SPCE
from screens import Screen154, Screen280
from picovector import color, font, image, shape

"""
Build both screen types explicitly, one on each SP/CE port, and let each panel say which it is.

A panel cannot be asked its size, so the class tells the board. The wrong one still starts,
with the picture the wrong size for the glass.

Every other screen example looks its class up from a size. This is the plain form, and shows
each class carries its own refresh rate.

Each panel draws its measured diagonal, since a screen's size is its diagonal.

Press "Boot" to exit the program.
"""

# Constants for drawing
BACKGROUND = color.navy                 # The panel behind everything
FOREGROUND = color.white                # The diagonal and every word of it
TITLE = 0.30                            # The size, as a fraction of the panel's width
DETAIL = 0.12                           # The line naming the class, the same way
PAD = 5                                 # Clearance the diagonal leaves around lettering
VECTOR_FACE = "/rom/fonts/AdventPro-Medium.af"
TEXT_MIDDLE = 0.805                     # Where this face centres its lettering below the given y, measured
                                        # for this face only

# Create a MightyFX object with both SP/CE ports set up for screens
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# Each class named directly, which is the whole subject of this example. Swap them over and
# both panels still light, each showing a frame cut for the other one
screens = (Screen280(mighty.spce_a), Screen154(mighty.spce_b))

face = font.load(VECTOR_FACE)


def label(canvas, text, size, down):
    """Draw lettering centred across the panel on a patch of background that stops the diagonal."""
    across = canvas.width / 2
    wide = canvas.measure_text(text, font_size=size)[0]

    canvas.pen = BACKGROUND
    canvas.rectangle(round(across - wide / 2 - PAD), round(down - size / 4 - PAD),
                     round(wide + PAD * 2), round(size / 2 + PAD * 2))

    canvas.pen = FOREGROUND
    canvas.text(text, across - wide / 2, down - TEXT_MIDDLE * size, font_size=size)


def card(screen):
    """Draw one panel's own diagram, the diagonal it measures and the size that diagonal is."""
    canvas = image(screen.width, screen.height)
    canvas.antialias = image.X4

    canvas.pen = BACKGROUND
    canvas.clear()

    # Corner to corner, which is what a screen's size measures
    canvas.pen = FOREGROUND
    canvas.shape(shape.line(0, canvas.height, canvas.width, 0, 1.4))

    canvas.font = face
    label(canvas, f'{screen.SIZE}"', round(canvas.width * TITLE), canvas.height / 2)

    # What the class is, small and along the bottom
    detail = round(canvas.width * DETAIL)
    named = f"{type(screen).__name__}   {screen.width}x{screen.height}   {screen.framerate}fps"
    label(canvas, named, detail, canvas.height - detail + detail // 2)

    return canvas


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    for screen in screens:
        screen.update(card(screen))
        print(f"SP/CE {screen.port.name}: {type(screen).__name__} at {screen.framerate}fps")

    # Neither panel has anything left to change, so both hold their frame and this waits
    while not mighty.boot_pressed():
        pass

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
