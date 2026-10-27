from mighty_fx import MightyFX, SPCE
from playback import GIFPlayer
from screens import Screen280

"""
Play an animated GIF forward then back, dwelling at each turn.

ping_pong walks the frames forward then back, so an animation with two ends never jumps.
The coin loops, so first_as_last replays its first frame at the far end for a full turn each way.

hold= sets the wait at each turn, one value for both ends or two.

Press "Boot" to exit the program.
"""

# Constants
GIF_PATH = "/examples/assets/pirate_coin.gif"   # The GIF to play
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted
HOLD = 1.0                       # Seconds to dwell at each end, both being the coin face

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a, rotation=ROTATION)

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
