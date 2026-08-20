from mighty_fx import MightyFX, SPCE
from playback import GIFPlayer
from screens import Reserve, Screen280, ScreenPair

"""
Play one animated GIF across two screens, both changing frame together.

A pair presents its panels together, so one call sends the frame to both and neither can
be left showing what the other has moved on from. There is one player rather than two: the
animation has one position, shown twice.

Both panels are full size and each converts its own frame, so the SRAM for two of them is
set aside when the screens are made. That is what the reserve is.

Press "Boot" to exit the program.
"""

# Constants
GIF_PATH = "/examples/assets/pirate_coin.gif"   # The GIF to play, beside this example
ROTATION = 90                              # Quarter turn, to suit how the screens are mounted

# Create a MightyFX object with both SP/CE ports set up for screens, and a 2.8" screen on each
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
pair = ScreenPair(Screen280(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES),
                  Screen280(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES))

# A GIF carries a delay for each frame but no clock, so a player is what walks them
player = GIFPlayer(GIF_PATH)

# The ground the file was authored over, read from its own corner
ground = player.image.get(0, 0)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # One call reaches both panels, so only send when the frame changes
        if player.has_advanced():
            pair.update(player.image, rotation=ROTATION, bg_color=ground)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
