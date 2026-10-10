from mighty_fx import MightyFX

from picofx import MonoPlayer
from picofx.mono import RandomFX

"""
Play a randomly changing brightness on every colour of MightyFX's outputs.

Each one picks its own brightness, and an output's three are picked independently, so
every output twinkles through random colours without a colour effect being involved.

Press "Boot" to exit the program.
"""

# Constants
INTERVAL = 0.2          # The time (in seconds) between each random brightness
BRIGHTNESS_MIN = 0.0    # The min brightness to randomly go down to
BRIGHTNESS_MAX = 1.0    # The max brightness to randomly go up to


# Variables
mighty = MightyFX()                 # Create a new MightyFX object to interact with the board
player = MonoPlayer(mighty.monos)   # Create a new effect player to control each colour of MightyFX's outputs


# Create and set up a random effect on each colour. Each gets an effect of its own, since
# one shared between them would give them all the same brightness
player.effects = [RandomFX(interval=INTERVAL,
                           brightness_min=BRIGHTNESS_MIN,
                           brightness_max=BRIGHTNESS_MAX) for _ in mighty.monos]


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not mighty.boot_pressed():
        pass

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    mighty.shutdown()
