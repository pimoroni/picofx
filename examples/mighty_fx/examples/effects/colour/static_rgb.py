from mighty_fx import MightyFX

from picofx import ColourPlayer
from picofx.colour import RGBFX

"""
Show a static colour on all of MightyFX's RGB outputs.

Press "Boot" to exit the program.
"""

# Constants
R = 255     # The amount of red (from 0 to 255)
G = 0       # The amount of green (from 0 to 255)
B = 0       # The amount of blue (from 0 to 255)


# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs


# Create a static colour effect, then give it to every output. An effect assigned on its own
# rather than in a list plays on all of them
static = RGBFX(R, G, B)
player.effects = static


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
