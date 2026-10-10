from mighty_fx import MightyFX

from picofx import ColourPlayer
from picofx.colour import RainbowFX

"""
Play a rainbow effect on all of MightyFX's RGB outputs.

Every output shows the same colour, so the whole board cycles through the rainbow as one.
rainbow_wave.py spreads the colours along the outputs instead.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs


# Create a rainbow effect, then give it to every output. An effect assigned on its own rather
# than in a list plays on all of them, so they cycle together
rainbow = RainbowFX(speed=0.2,          # The speed to cycle through colours at, with 1.0 being 1 second
                    sat=1.0,            # The saturation/intensity of the colour (from 0.0 to 1.0)
                    val=1.0)            # The value/brightness of the colour (from 0.0 to 1.0)
player.effects = rainbow


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
