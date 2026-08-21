from mighty_fx import MightyFX, SPCE
from screens import Screen154, Screen280
from picovector import color, font, image, shape, vec2

"""
Build both screen types explicitly, one on each SP/CE port, and let each panel say which it is.

A panel cannot be asked its size. The controller answers the same either way, so the class
is how the board is told, and naming the wrong one still starts: the picture simply comes
out the wrong size for the glass.

Every other screen example takes a size and looks its class up, which is how one file runs
on either panel. This is the plain form underneath, and it shows what a class carries
besides its dimensions, since the two panels hold different refresh rates of their own.

Each panel draws itself the way a television is drawn on the side of its box: a screen with
a measured diagonal, a screen's size being its diagonal and nothing else.

Press "Boot" to exit the program.
"""

# Constants for drawing
GROUND = color.navy                     # The panel behind everything
INK = color.white                       # The diagonal and every word of it
TITLE = 0.30                            # The size, as a fraction of the panel's width
DETAIL = 0.12                           # The line naming the class, the same way
PAD = 5                                 # Clearance the diagonal leaves around lettering
VECTOR_FACE = "/rom/fonts/AdventPro-Medium.af"
INK_MIDDLE = 0.805                      # Where that face centres its ink below the position
                                        # given, measured: another face wants measuring again

# Create a MightyFX object with both SP/CE ports set up for screens
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)

# Each class named directly, which is the whole subject of this example. Swap them over and
# both panels still light, each showing a frame cut for the other one
screens = (Screen280(mighty.spce_a), Screen154(mighty.spce_b))

face = font.load(VECTOR_FACE)


def rule(canvas, start, end):
    """A dimension line between two points, with a head at each end."""
    canvas.pen = INK
    canvas.shape(shape.line(start[0], start[1], end[0], end[1], 1.4))

    # A head a twentieth of the diagonal, and not quite half that across
    span = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
    head = span * 0.055
    half = head * 0.4
    for tip, other in ((start, end), (end, start)):
        # Back along the shaft to the head's base, then out to either side of it
        along = ((other[0] - tip[0]) / span, (other[1] - tip[1]) / span)
        base = (tip[0] + along[0] * head, tip[1] + along[1] * head)
        canvas.shape(shape.custom([vec2(tip[0], tip[1]),
                                   vec2(base[0] - along[1] * half, base[1] + along[0] * half),
                                   vec2(base[0] + along[1] * half, base[1] - along[0] * half)]))


def label(canvas, text, size, across, ink_middle):
    """Lettering with its ink centred on a point, the ground painted back in behind it first.

    Painting first leaves the diagonal a gap to stop either side of, rather than running
    behind the lettering and touching it.
    """
    wide = canvas.measure_text(text, font_size=size)[0]

    canvas.pen = GROUND
    canvas.rectangle(round(across - wide / 2 - PAD), round(ink_middle - size / 4 - PAD),
                     round(wide + PAD * 2), round(size / 2 + PAD * 2))

    canvas.pen = INK
    canvas.text(text, across - wide / 2, ink_middle - INK_MIDDLE * size, font_size=size)


def card(screen):
    """One panel's own diagram: the diagonal it measures, and the size that diagonal is."""
    canvas = image(screen.width, screen.height)
    canvas.antialias = image.X4

    canvas.pen = GROUND
    canvas.clear()

    # Corner to corner, which is what a screen's size measures
    rule(canvas, (0, canvas.height), (canvas.width, 0))

    canvas.font = face
    middle = canvas.width / 2
    label(canvas, f'{screen.SIZE}"', round(canvas.width * TITLE), middle, canvas.height / 2)

    # What the class is, small and along the bottom
    detail = round(canvas.width * DETAIL)
    named = f"{type(screen).__name__}   {screen.width}x{screen.height}   {screen.framerate}fps"
    label(canvas, named, detail, middle, canvas.height - detail + 14)

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
