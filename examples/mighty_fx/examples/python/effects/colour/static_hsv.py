from mighty_fx import MightyFX

from picofx import ColourPlayer
from picofx.colour import HSVFX

"""
Show a static colour on all of MightyFX's RGB outputs, using HSV.

Press "Boot" to exit the program.
"""

# Constants
HUE = 0.0       # The colour's hue (from 0.0 to 1.0)
SAT = 1.0       # The colour's saturation (from 0.0 to 1.0)
VAL = 1.0       # The colour's value/brightness (from 0.0 to 1.0)


# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs


# Create a static colour effect, then give it to every output. An effect assigned on its own
# rather than in a list plays on all of them
static = HSVFX(HUE, SAT, VAL)
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
