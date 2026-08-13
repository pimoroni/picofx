from mighty_fx import MightyFX
from picofx import ColourPlayer
from picofx.colour import BLUE, CYAN, GREEN, MAGENTA, RED, YELLOW, RGBBlinkFX

"""
Chase a blink around MightyFX's seven RGB outputs, each blink a different colour in turn.

Press "Boot" to exit the program.
"""

# Constants
COLOURS = [RED, YELLOW, GREEN, CYAN, BLUE, MAGENTA]     # The colours each output blinks through
SPEED = 0.5                                             # The speed of one pass along the board, with 1.0 being 1 second


# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs


# Set up a blink on each output, a little later than the one before, which turns seven blinks
# into a chase. One output's share each, or a blink outlasts the pass and changes colour part way
num_outputs = len(mighty.outputs)
player.effects = [RGBBlinkFX(colour=COLOURS,
                             speed=SPEED,
                             phase=-i / num_outputs,
                             duty=1 / num_outputs) for i in range(num_outputs)]


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
