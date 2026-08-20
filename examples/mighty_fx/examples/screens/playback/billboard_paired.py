# Shows two different posters at once, one on each of a pair of screens, both changing together.
#
# Two SP/CE ports are two streams, so a pair can be sent different pictures for about what one panel costs on
# its own. Measured on a Screen280 pair: 67ms for one panel, 68ms for the same poster on both, and 68ms for a
# different poster on each. The same two panels driven one after the other cost 134ms, which is what the pair
# is saving.
#
# One player feeds both. image_at() reads any frame without moving the player, so the second panel takes the
# poster a fixed distance along the folder, and the whole folder is held once rather than twice.

from mighty_fx import MightyFX, SPCE
from playback import SequencePlayer
from screens import Reserve, Screen280, ScreenPair

# Constants
POSTERS = "/examples/assets/billboards/portrait"   # Shared with the billboard showcases
ROTATION = 0                     # Portrait, which is the shape these posters are
DWELL = 3.0                      # Seconds a poster is up for
AHEAD = 4                        # How far along the folder the second panel reads, so the two never match

# Create a MightyFX object with both SP/CE ports set up for screens, and a 2.8" screen on
# each. Two screens each converting their own full-size poster is what the reserve buys.
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
pair = ScreenPair(Screen280(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES),
                  Screen280(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES))

player = SequencePlayer(POSTERS, fps=1 / DWELL)
print(f"{player.frames} posters, {DWELL}s each, the second panel {AHEAD} along")

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # One call sends both panels, so neither is ever left showing what the other has moved on from
        if player.has_advanced():
            pair.update(player.image, player.image_at((player.frame + AHEAD) % player.frames), rotation=ROTATION)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
