from mighty_fx import MightyFX

from picofx import MonoPlayer
from picofx.mono import FlickerFX

"""
Play a flickering effect on a single colour of a MightyFX output.

The effect plays on the first colour of output one, its red, so output one
flickers red like a flame and the rest stay dark.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX()                 # Create a new MightyFX object to interact with the board
player = MonoPlayer(mighty.monos)   # Create a new effect player to control each colour of MightyFX's outputs


# Create and set up a flicker effect to play on the first colour. The rest are left without
# one, which the player takes as nothing to play
player.effects = [
    FlickerFX(brightness=1.0,       # The brightness to use when being bright (from 0.0 to 1.0)
              dimness=0.5,          # How much to dim the brightness by (from 0.0 to 1.0) when being dim
              bright_min=0.05,      # The min amount of time (in seconds) to be bright for
              bright_max=0.1,       # The max amount of time (in seconds) to be bright for
              dim_min=0.02,         # The min amount of time (in seconds) to be dim for
              dim_max=0.04),        # The max amount of time (in seconds) to be dim for
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
