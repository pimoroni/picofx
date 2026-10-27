import sys
from mighty_fx import MightyFX, SPCE
from timing import Pacer, Roller
from screens import SCREEN_TYPES, ScreenGroup
from picovector import color, image, shape, vec2

"""
Flash runway chevrons across a screen hub in two interleaved banks, each bank a subset of
one group.

subset() names some of a group's panels, and is bound once here and reused. Writing a
subset keeps the whole group's refresh rates held together, where writing a member's own
screen would not. Every panel in a bank shows the same chevrons, so a bank is one write
however many panels it holds. That only works because the picture repeats per panel, where
one spanning the wall would need each panel's own slice, and a write each.

Press "Boot" to exit the program.

Section: Across several screens
"""

# Constants for drawing
FLASH = 0.5                         # How long each bank stays lit before the other takes over, in seconds
CHEVRONS = 3                        # How many chevrons each panel carries, one above the next
LIT = color.rgb(255, 204, 0)        # A chevron switched on
UNLIT = color.rgb(51, 51, 34)       # And switched off, still faintly there as a real lamp is
GROUND = color.black

# Which screen is on every hub position, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with a screen hub across both SP/CE ports. One carries the
# screen bus and the other gives up its five lines as extra chip selects, which is what
# lets one port drive six panels instead of one
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_SELECTS)

# The hub hands out a port per chip select it reaches, whether or not a panel is on the end
# of it. One that is not there refuses to be created, so build them all and keep whichever
# answered: a hub does not have to be full to be used
panels = []
for port in mighty.hub.ports:
    try:
        panels.append(ScreenType(port))
    except ValueError:
        pass

if not panels:
    # Give the connectors back before saying so. A hub drives its chip selects high,
    # and one of those is the backlight pin of whatever is plugged into that connector
    mighty.shutdown()
    raise RuntimeError("No panels answered! Check the hub is plugged into SP/CE A, with its panels on the hub rather than on the board")

wall = ScreenGroup(*panels)

# The two banks, every other panel in each, bound once. A hub of one panel has a single bank,
# as a subset needs at least one panel
banks = [wall.subset(*members) for members in (panels[0::2], panels[1::2]) if members]
print(f"{len(panels)} of {len(mighty.hub.ports)} hub positions answered, in {len(banks)} bank(s)")

WIDTH, HEIGHT = panels[0].width, panels[0].height


def chevrons(pen):
    """Draw a panel's chevrons in one pen, each a thick upward point."""
    canvas = image(WIDTH, HEIGHT)
    canvas.antialias = image.X4
    canvas.pen = GROUND
    canvas.clear()

    canvas.pen = pen
    reach = WIDTH * 0.35                # How far each arm runs out from the middle
    thick = HEIGHT / (CHEVRONS * 4)     # How deep each stroke is
    pitch = HEIGHT / CHEVRONS
    middle = WIDTH / 2
    for index in range(CHEVRONS):
        top = index * pitch + (pitch - reach - thick) / 2
        canvas.shape(shape.custom([vec2(middle, top), vec2(middle + reach, top + reach),
                                   vec2(middle + reach, top + reach + thick), vec2(middle, top + thick),
                                   vec2(middle - reach, top + reach + thick), vec2(middle - reach, top + reach)]))
    return canvas


# Each state is drawn once, so changing over is only the writes
lit, unlit = chevrons(LIT), chevrons(UNLIT)

pacer = Pacer(0.02)
flash = Roller()                    # When the banks next change over, at once to begin with
showing = 0                         # Which bank is lit

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        if flash.is_due():
            # One write per bank, the lit one and the dark one, however many panels each holds
            for index, bank in enumerate(banks):
                bank.update(lit if index == showing else unlit)

            showing = (showing + 1) % 2
            flash.restart(FLASH)

        pacer.hold()

# Turn off the panels and all the outputs
finally:
    mighty.shutdown()
