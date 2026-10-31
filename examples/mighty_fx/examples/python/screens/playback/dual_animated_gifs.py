from mighty_fx import MightyFX, SPCE
from playback import GIFPlayer
from screens import Reserve, Screen280, ScreenPair

"""
Play a different animated GIF on each of two screens, each its own size, length and rate.

A player holds one animation's position, so two animations need two. Each takes its position
from the clock, so loops of different periods drift in and out of step.

Both panels are sent together, so a frame shows when the pair next comes round. Each
animation keeps its speed but not its exact beat.

Neither file is the shape of a panel. A source is centred either way, so the coin takes
background down its sides and the scan's overrun is split between edges.

Press "Boot" to exit the program.
"""

# Constants
GIF_PATH_A = "/examples/assets/pirate_coin.gif"     # The GIF to play on the screen on SP/CE port A
GIF_PATH_B = "/examples/assets/medscan.gif"         # The GIF to play on the screen on SP/CE port B
ROTATION = 90                                       # Quarter turn, to suit how the screens are mounted

# Create a MightyFX object with both SP/CE ports set up for screens, and a 2.8" screen on
# each with the reserve two full-size frames need
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
pair = ScreenPair(Screen280(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES, rotation=ROTATION),
                  Screen280(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES, rotation=ROTATION))

# A player each, as the GIFs differ in delays and length.
# The scan plays as a ping-pong, or its skeleton would jump to an outline
try:
    player_a = GIFPlayer(GIF_PATH_A)
    player_b = GIFPlayer(GIF_PATH_B, ping_pong=True)
except OSError:
    mighty.shutdown()
    raise RuntimeError(f"'{GIF_PATH_A}' or '{GIF_PATH_B}' is missing! Check both are on the board") from None

# The background each file was authored over as read from its own corner, one per screen
backgrounds = player_a.image.get(0, 0), player_b.image.get(0, 0)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Either one changing sends both, as a pair presents together.
        # Both are asked, so one send covers a change to each
        a_moved = player_a.has_advanced()
        b_moved = player_b.has_advanced()
        if a_moved or b_moved:
            pair.update(player_a.image, player_b.image, bg_color=backgrounds)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
