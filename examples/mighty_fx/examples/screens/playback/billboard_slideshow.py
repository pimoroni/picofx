from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280

"""
Show a folder of posters, one at a time, sent straight to the panel.

The simplest thing a player does: a folder walked on a clock. Nothing is drawn over the
picture, so nothing needs a canvas, and it is what the other examples in this folder add
to.

Every poster decodes into the heap when the player is made, so the whole folder is held
before the first one shows. These are palettised, which keeps that affordable:
eleven of them are about 850KB where truecolour ones would be four times that.

Press "Boot" to exit the program.
"""

# Constants
POSTERS = "/examples/assets/billboards/portrait"   # Shared with the billboard showcases
ROTATION = 0                     # Portrait, which is the shape these posters are
DWELL = 3.0                      # Seconds a poster is up for

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a)

# A folder of images declares no delays, so the rate is named here. fps=False would leave the
# timing out altogether and advance() would drive instead
player = SequencePlayer(POSTERS, fps=1 / DWELL)
print(f"{player.frames} posters, {DWELL}s each")

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The panel could be sent the same poster hundreds of times over; only a change needs it
        if player.has_advanced():
            screen.update(player.image, rotation=ROTATION)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
