from tiny_fx import TinyFX
from picofx import ColourPlayer
from picofx.colour import HueStepFX

"""
Play a stepped hue effect on TinyFX's RGB output.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                             # Create a new TinyFX object to interact with the board
player = ColourPlayer(tiny.rgb)             # Create a new effect player to control TinyFX's RGB output


# Create and set up a rainbow effect to play
player.effects = HueStepFX(interval=1.0,    # The time (in seconds) between each hue step
                           hue=0.0,         # The hue of the colour to start at (from 0.0 to 1.0)
                           sat=1.0,         # The saturation/intensity of the colour (from 0.0 to 1.0)
                           val=1.0,         # The value/brightness of the colour (from 0.0 to 1.0)
                           steps=6)         # The number of steps to take around the colour wheel


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
