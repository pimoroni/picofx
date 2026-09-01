from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280, ScreenGroup

"""
Play one animation across every panel a hub can reach, each showing the same frame.

The pattern was drawn to tile in both directions, so a wall reads as one surface and its pulses
travel across the joins. Every panel showing the same frame is what makes that work: a frame
costs the same however many panels are on the hub, the panels latching one stream of pixels
together, so the rate a wall can hold is the rate one panel can hold.

Two panels butted together hide a band of pixels behind their bezels, so the pattern steps at
each join. The frames are indexed PNGs, one a frame, which is the choice worth copying: eight of
this size cost 609KB against about 2.4MB truecolour.

Press "Boot" to exit the program.
"""

# Constants
FRAMES = "/examples/assets/traces"   # The folder of frames, beside this example
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
# however many answered are driven the same way. The rotation these panels are mounted
# at belongs to the group, a frame reaching all of them being placed once
wall = ScreenGroup(*panels, rotation=90)
print(f"{len(panels)} of {len(mighty.hub.ports)} hub positions answered")

# Every frame decodes when the player is made, so a frame costs nothing to reach afterwards
player = SequencePlayer(FRAMES, fps=FPS)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The panels refresh faster than the animation changes, so only send a new frame
        if player.has_advanced():
            wall.update(player.image)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
