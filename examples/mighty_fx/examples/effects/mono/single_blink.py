from mighty_fx import MightyFX

from picofx import MonoPlayer
from picofx.mono import BlinkFX

"""
Play a blinking effect on a single colour of a MightyFX output.

The effect plays on the first colour of output one, its red, so output one
blinks red and the rest stay dark.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX()                 # Create a new MightyFX object to interact with the board
player = MonoPlayer(mighty.monos)   # Create a new effect player to control each colour of MightyFX's outputs


# Create and set up a blink effect to play on the first colour. The rest are left without
# one, which the player takes as nothing to play
player.effects = [
    BlinkFX(speed=1.0,              # The speed to blink at, with 1.0 being 1 second
            phase=0.0,              # How far through the blink to start the effect (from 0.0 to 1.0)
            duty=0.5),              # How long the blink is on for (from 0.0 to 1.0)
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
