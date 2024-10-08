from tiny_fx import TinyFX
from picofx import ColourPlayer
from picofx.colour import RGBFX

"""
Show a static colour on TinyFX's RGB output.

Press "Boot" to exit the program.
"""

# Constants
R = 255     # The amount of red (from 0 to 255)
G = 0       # The amount of green (from 0 to 255)
B = 0       # The amount of blue (from 0 to 255)

# Variables
tiny = TinyFX()                     # Create a new TinyFX object
player = ColourPlayer(tiny.rgb)     # Create a new effect player to control TinyFX's RGB output

# Set up the colour effect to play
player.effects = RGBFX(R, G, B)

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
