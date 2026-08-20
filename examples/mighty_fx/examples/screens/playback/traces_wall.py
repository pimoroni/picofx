from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280, ScreenGroup

"""
Play one animation across every panel a hub can reach, each showing the same frame.

The pattern was drawn to tile in both directions, so a wall reads as one surface rather
than as six copies, and its pulses travel across the joins. Every panel showing the same
frame is what makes that work, and it costs one decode rather than six.

The joins interrupt it, and are meant to here: two panels butted together hide a band of
pixels behind their bezels, so the pattern steps at each one. Taking that out means an
offset per panel, which the pair examples cover.

A frame costs the same however many panels are on the hub, which is the point of driving
them as a group: the panels latch one stream of pixels together, so the rate a wall can
hold is the rate one panel can hold.

The frames are indexed PNGs, one a frame, which is the choice worth copying: eight of this
size cost 609KB of heap indexed against about 2.4MB truecolour, the player holding
whatever each file carries.

Press "Boot" to exit the program.
"""

# Constants
FRAMES = "/examples/assets/traces"   # The folder of frames, beside this example
ROTATION = 90                    # Quarter turn, to suit how the screens are mounted
FPS = 10                         # The rate to play at, a folder of images declaring none

# SP/CE B gives up its five pins as the chip selects for the panels on SP/CE A, so
# the board hands back six ports and every panel is brought up and cleared together
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_LINES)

# The hub hands out a port per chip select it reaches, whether or not a panel is on the end
# of it. One that is not there refuses to be created, so build them all and keep whichever
# answered: a hub does not have to be full to be used
panels = []
for port in mighty.hub.ports:
    try:
        panels.append(Screen280(port))
    except ValueError:
        pass

if not panels:
    # Give the connectors back before saying so. A hub drives its chip selects high,
    # and one of those is the backlight pin of whatever is plugged into that connector
    mighty.shutdown()
    raise RuntimeError("No panels answered! Check the hub is plugged into SP/CE A, with its panels on the hub rather than on the board")

# A group plays the one frame onto every panel it holds. One panel is a group too, so
# however many answered are driven the same way
wall = ScreenGroup(*panels)
print(f"{len(panels)} of {len(mighty.hub.ports)} hub positions answered")

# Every frame decodes into the heap here, so a frame costs nothing to reach afterwards
player = SequencePlayer(FRAMES, fps=FPS)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The panels refresh faster than the animation changes, so only send a new frame
        if player.has_advanced():
            wall.update(player.image, rotation=ROTATION)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
