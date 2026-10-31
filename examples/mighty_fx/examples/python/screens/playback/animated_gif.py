import sys
from mighty_fx import MightyFX, SPCE
from playback import GIFPlayer
from screens import SCREEN_TYPES

"""
Play an animated GIF on a screen, at the frame delays the file was authored with.

The coin's colours sit on the 16 levels the screens drive a channel at, where a photograph
exported straight to a GIF falls between them and bands into patches.

The coin sits on a middle grey so its near-black rim shows. The panel takes that grey from
the file's corner, so another GIF lands on its own background.

Press "Boot" to exit the program.
"""

# Constants
GIF_PATH = "/examples/assets/pirate_coin.gif"   # The GIF to play
ROTATION = 90                                   # Quarter turn, to suit how the screen is mounted

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a, rotation=ROTATION)

# A player walks the frames at the file's own delays, or at a rate given as fps=
try:
    player = GIFPlayer(GIF_PATH)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{GIF_PATH}' is missing! Check it is on the board") from None

# A decoded frame is palettised, and get() resolves that and hands back a colour
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
