# Plays an animated GIF on a screen, at the frame delays the file was authored with.
#
# The coin was drawn for this panel: its colours already sit on the 16 levels a channel the panel resolves,
# dithered, so a smooth gradient reads smooth. A photograph exported straight to a GIF has colours between
# those levels and bands into patches instead, which is worth knowing before blaming the screen. It is
# square, so it centres with the background above and below it whichever way the panel is turned.
#
# The coin sits on a middle grey. Its own rim is almost black, so on a dark ground the two meet and the coin
# loses its outline: a subject needs a ground it is not the same value as, and grey suits a design carrying
# both dark and near white. The panel is given the same grey for the strip the square does not reach, and it
# is read from the file rather than typed here, so naming a different GIF above still lands on its own ground.

from mighty_fx import MightyFX, SPCE
from playback import GIFPlayer
from screens import Screen280

# Constants
GIF_PATH = "/examples/assets/pirate_coin.gif"   # The GIF to play, beside this example
ROTATION = 90                    # Quarter turn, to suit how the screen is mounted

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# A GIF declares a delay for each of its frames but keeps no clock, so a player is what
# walks them. The default plays at the file's own delays; fps=12 would name a rate instead
player = GIFPlayer(GIF_PATH)

# What the panel shows where the frames do not reach. A decoded frame is palettised, and get() resolves that
# and hands back a colour, so the corner pixel is the ground the file was authored over
ground = player.image.get(0, 0)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The screen refreshes faster than the GIF changes, so only send a new frame
        if player.has_advanced():
            screen.update(player.image, rotation=ROTATION, bg_color=ground)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
