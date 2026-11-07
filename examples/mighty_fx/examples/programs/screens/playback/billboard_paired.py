import sys

from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Reserve, Screen280, ScreenPair

"""
Show two different posters at once, one on each of a pair of screens, both changing together.

Two SP/CE ports are two streams, so a pair shows a different poster on each for one panel's cost.

One player feeds both. image_at() reads a frame without moving the player, so the second panel runs ahead.

Press "Boot" to exit the program.

Section: Two screens
Args: Rotation = 0 or 180
"""

# Constants
POSTERS = "/examples/pictures/billboards/portrait"   # Shared with the billboard showcases
DWELL = 3.0                      # Seconds a poster is up for
AHEAD = 4                        # How far along the folder the second panel reads, so the two never match

# How far the screens are turned, 0 or 180 for portrait posters, or what the effects file passes in args
ROTATION = 0 if not sys.argv[1:] else int(sys.argv[1])

# Create a MightyFX object with both SP/CE ports set up for screens, and a 2.8" screen on
# each with the reserve two full-size posters need
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
pair = ScreenPair(Screen280(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES, rotation=ROTATION),
                  Screen280(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES, rotation=ROTATION))

try:
    player = SequencePlayer(POSTERS, fps=1 / DWELL)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{POSTERS}' is missing! Check it is on the board") from None

print(f"{player.frames} posters, {DWELL}s each, the second panel {AHEAD} along")

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # One call sends both panels, so neither is ever left showing what the other has moved on from
        if player.has_advanced():
            pair.update(player.image, player.image_at((player.frame + AHEAD) % player.frames))

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
