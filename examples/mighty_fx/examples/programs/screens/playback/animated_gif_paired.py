import sys
from mighty_fx import MightyFX, SPCE
from playback import GIFPlayer
from screens import SCREEN_TYPES, Reserve, ScreenPair

"""
Play one animated GIF across two screens, both changing frame together.

A pair presents its panels together, so one call sends the frame to both from a single player.

Both panels are full size and each converts its own frame, so room for two is set aside when
the screens are made. That is what the reserve is.

Press "Boot" to exit the program.

Section: Multi-screen
Args: Screen size = 2.8, Rotation = 90
"""

# Constants
GIF_PATH = "/examples/pictures/pirate_coin.gif"   # The GIF to play

# Which screens are on the ports, "2.8" or "1.54", and how far they are turned, 0, 90, 180 or 270,
# or what the effects file passes in args, the size first. A pair wants two of the same size
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ROTATION = 90 if not sys.argv[2:] else int(sys.argv[2])
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with both SP/CE ports set up for screens, and a panel on each
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
pair = ScreenPair(ScreenType(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES, rotation=ROTATION),
                  ScreenType(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES, rotation=ROTATION))

# A GIF carries a delay for each frame but no clock, so a player is what walks them
try:
    player = GIFPlayer(GIF_PATH)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{GIF_PATH}' is missing! Check it is on the board") from None

# The background the file was authored over, read from its own corner
background = player.image.get(0, 0)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # One call reaches both panels, so only send when the frame changes
        if player.has_advanced():
            pair.update(player.image, bg_color=background)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
