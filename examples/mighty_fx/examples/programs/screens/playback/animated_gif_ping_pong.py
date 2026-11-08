import sys
from mighty_fx import MightyFX, SPCE
from playback import GIFPlayer
from screens import SCREEN_TYPES

"""
Play an animated GIF forwards then backwards with a pause at each end.

ping_pong walks the frames forward then back, so an animation with two ends never jumps.
The coin loops, so first_as_last replays its first frame at the far end for a full turn each way.

hold= sets the wait at each turn, one value for both ends or two.

Press "Boot" to exit the program.

Program: Animated GIF (ping pong)
Section: Pictures and GIFs
Args: Screen size = 2.8, Rotation = 90
"""

# Constants
GIF_PATH = "/examples/pictures/pirate_coin.gif"   # The GIF to play
HOLD = 1.0                       # Seconds to dwell at each end, both being the coin face

# Which screen is on the port, "2.8" or "1.54", and how far it is turned, 0, 90, 180 or 270, or
# what the effects file passes in args, the size first
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ROTATION = 90 if not sys.argv[2:] else int(sys.argv[2])
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a, rotation=ROTATION)

# ping_pong needs somewhere to turn around, and first_as_last needs a turn to put its extra
# frame at, so a plain forward loop refuses both
try:
    player = GIFPlayer(GIF_PATH, ping_pong=True, first_as_last=True, hold=HOLD)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{GIF_PATH}' is missing! Check it is on the board") from None

# The background the file was authored over, read from its own corner
background = player.image.get(0, 0)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The screen refreshes faster than the GIF changes, so only send a new frame
        if player.has_advanced():
            screen.update(player.image, bg_color=background)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
