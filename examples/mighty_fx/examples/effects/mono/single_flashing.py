from mighty_fx import MightyFX

from picofx import MonoPlayer
from picofx.mono import FlashFX

"""
Play a flashing effect on a single colour of a MightyFX output.

The effect plays on the first colour of output one, its red, so output one
flashes red in bursts and the rest stay dark.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX()                 # Create a new MightyFX object to interact with the board
player = MonoPlayer(mighty.monos)   # Create a new effect player to control each colour of MightyFX's outputs


# Create and set up a flash effect to play on the first colour. The rest are left without
# one, which the player takes as nothing to play
player.effects = [
    FlashFX(speed=1.0,              # The speed to flash at, with 1.0 being 1 second
            flashes=2,              # The number of flashes to do within that time
            window=0.2,             # How much of the flash time to perform the flashes in
            phase=0.0,              # How far through the flash cycle to start the effect (from 0.0 to 1.0)
            duty=0.5),              # How long as a percent from 0.0 to 1.0 each flash is on for
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
