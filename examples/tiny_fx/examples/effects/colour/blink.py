from tiny_fx import TinyFX
from picofx import ColourPlayer
from picofx.colour import RGBBlinkFX, RED, YELLOW, GREEN, CYAN, BLUE, MAGENTA

"""
Play a blinking sequence effect on TinyFX's RGB output. Each blink in the sequence can be a different colour.

Press "Boot" to exit the program.
"""

# Constants
COLOURS = [RED, YELLOW, GREEN, CYAN, BLUE, MAGENTA]

# Variables
tiny = TinyFX()                         # Create a new TinyFX object to interact with the board
player = ColourPlayer(tiny.rgb)         # Create a new effect player to control TinyFX's RGB output


# Create and set up a rainbow effect to play
player.effects = RGBBlinkFX(colour=COLOURS,     # The colour (or colours to blink in sequence)
                            speed=0.5)          # The speed to cycle through colours at, with 1.0 being 1 second


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
