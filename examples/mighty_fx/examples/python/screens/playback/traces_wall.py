from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280, ScreenGroup

"""
Play one animation across every panel a hub can reach, each showing the same frame.

The pattern tiles both ways, so a wall reads as one surface. Every panel takes the same stream at
once, so a frame costs the same however many panels show it.

Bezels hide a band at each join, so the pattern steps there. Indexed PNGs are the choice worth
copying, since the player holds each at a quarter of a truecolour frame's memory.

Press "Boot" to exit the program.

Section: Across several screens
"""

# Constants
FRAMES = "/examples/assets/traces"   # The folder of frames, shared with the scroll example
FPS = 10                         # The rate to play at, a folder of images declaring none

# Create a MightyFX object driving a screen hub, which takes SP/CE port B for extra chip selects
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.HUB_SELECTS)

# Build a screen on every hub port and keep those that answer, as a hub need not be full
panels = []
for port in mighty.hub.ports:
    try:
        panels.append(Screen280(port))
    except ValueError:
        pass

if not panels:
    # Release the hub first, as one of its chip selects is a panel's backlight pin
    mighty.shutdown()
    raise RuntimeError("No panels answered! Check the hub is plugged into SP/CE A, with its panels on the hub rather than on the board")

# A group plays one frame at one rotation onto every panel it holds, however many answered
wall = ScreenGroup(*panels, rotation=90)
print(f"{len(panels)} of {len(mighty.hub.ports)} hub positions answered")

try:
    player = SequencePlayer(FRAMES, fps=FPS)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{FRAMES}' is missing! Check it is on the board") from None

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The panels refresh faster than the animation changes, so only send a new frame
        if player.has_advanced():
            wall.update(player.image)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
