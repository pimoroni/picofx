from tiny_fx import TinyFX
from picofx import ColourPlayer
from picofx.colour import HSVFX

"""
Show a static colour on TinyFX's RGB output, using HSV.

Press "Boot" to exit the program.
"""

# Constants
HUE = 0.0       # The colour's hue (from 0.0 to 1.0)
SAT = 1.0       # The colour's saturation (from 0.0 to 1.0)
VAL = 1.0       # The colour's value/brightness (from 0.0 to 1.0)

# Variables
tiny = TinyFX()                     # Create a new TinyFX object
player = ColourPlayer(tiny.rgb)     # Create a new effect player to control TinyFX's RGB output

# Set up the colour effect to play
player.effects = HSVFX(HUE, SAT, VAL)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not tiny.boot_pressed():
        pass

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    tiny.shutdown()
