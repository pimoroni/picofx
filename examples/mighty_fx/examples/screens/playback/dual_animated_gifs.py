from mighty_fx import MightyFX, SPCE
from playback import GIFPlayer
from screens import Reserve, Screen280, ScreenPair

"""
Play a different animated GIF on each of two screens, each its own size, length and rate.

A player holds one animation's position, so two animations need two of them. Neither knows
about the other: each has its own length and its own delays, and each takes its position
from the clock, so two loops of different periods drift in and out of step as they run.

Both panels are sent together, so a frame appears when the pair next comes round rather than
at the moment its own file asks for it. Each animation keeps its own speed; what neither
keeps is its own beat exactly.

Neither file is the shape of a panel, and they are not the same shape as each other. A
source is centred either way: the coin is smaller than the panel and takes the background
down both sides, and the scan is larger, so what runs past the edges is split between them.
Neither needs an offset to sit where it should.

Press "Boot" to exit the program.
"""

# Constants
GIF_PATH_A = "/examples/assets/pirate_coin.gif"     # The GIF to play on the screen on SP/CE port A
GIF_PATH_B = "/examples/assets/medscan.gif"         # The GIF to play on the screen on SP/CE port B
ROTATION = 90                                       # Quarter turn, to suit how the screens are mounted

# Create a MightyFX object with both SP/CE ports set up for screens, and a 2.8" screen on
# each. Two screens each converting their own full-size frame is what the reserve buys.
mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN)
pair = ScreenPair(Screen280(mighty.spce_a, reserve=Reserve.FULL_SIZE_IMAGES),
                  Screen280(mighty.spce_b, reserve=Reserve.FULL_SIZE_IMAGES))

# A player each, since the two GIFs declare their own delays and are different lengths. The scan
# sweeps one way only, so it plays as a ping-pong and sweeps back down: run forward, its last frame
# is a whole skeleton and would jump straight to an outline
player_a = GIFPlayer(GIF_PATH_A)
player_b = GIFPlayer(GIF_PATH_B, ping_pong=True)

# The ground each file was authored over, read from its own corner, so the strips either side of
# the coin match its edges instead of being black. Every placement setting takes a value per screen,
# which is what keeps the scan's own ground its own, whether or not any of it shows
grounds = player_a.image.get(0, 0), player_b.image.get(0, 0)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Either one changing sends both panels, a pair presenting together. The or short
        # circuits, so B is not asked when A has already advanced, and that costs at most
        # one redundant redraw: a player's position comes from the clock and never from how
        # often it was asked
        if player_a.has_advanced() or player_b.has_advanced():
            pair.update(player_a.image, player_b.image, rotation=ROTATION, bg_color=grounds)

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
