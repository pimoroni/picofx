from mighty_fx import MightyFX

from picofx import MonoPlayer
from picofx.mono import RandomFX

"""
Play a randomly changing brightness effect on a single colour of a MightyFX output.

The effect plays on the first colour of output one, its red, so output one
jumps between random red brightnesses and the rest stay dark.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX()                 # Create a new MightyFX object to interact with the board
player = MonoPlayer(mighty.monos)   # Create a new effect player to control each colour of MightyFX's outputs


# Create and set up a random effect to play on the first colour. The rest are left without
# one, which the player takes as nothing to play
player.effects = [
    RandomFX(interval=0.05,         # The time (in seconds) between each random brightness
             brightness_min=0.0,    # The min brightness to randomly go down to
             brightness_max=1.0),   # The max brightness to randomly go up to
]


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
