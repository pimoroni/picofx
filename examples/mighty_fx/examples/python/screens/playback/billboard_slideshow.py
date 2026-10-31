from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Screen280

"""
Show a folder of posters, one at a time, sent straight to the panel.

The simplest thing a player does, a folder walked on a clock. Nothing is drawn over the
picture, so nothing needs a canvas.

Every poster decodes when the player is made, before the first shows. Palettised posters keep
that affordable at a quarter of a truecolour one's memory.

Press "Boot" to exit the program.
"""

# Constants
POSTERS = "/examples/assets/billboards/portrait"   # Shared with the billboard showcases
ROTATION = 0                     # Portrait, which is the shape these posters are
DWELL = 3.0                      # Seconds a poster is up for

# Create a MightyFX object with SP/CE port A set up for screens, and a 2.8" screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = Screen280(mighty.spce_a, rotation=ROTATION)

# A folder of images declares no delays, so the rate is named here. fps=False would leave the
# timing out altogether and advance() would drive instead
try:
    player = SequencePlayer(POSTERS, fps=1 / DWELL)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{POSTERS}' is missing! Check it is on the board") from None

print(f"{player.frames} posters, {DWELL}s each")

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Only send the poster when it changes
        if player.has_advanced():
            screen.update(player.image)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
