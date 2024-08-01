from tiny_fx import TinyFX
from picofx.colour import RED, GREEN

"""
Show the state of TinyFX's Boot button on its RGB output.
"""

# Constants
PRESSED_COLOUR = RED        # The colour to show when the boot button is pressed
RELEASED_COLOUR = GREEN     # The colour to show when the boot button is released

# Variables
tiny = TinyFX()             # Create a new TinyFX object to interact with the board


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Loop forever
    while True:
        if tiny.boot_pressed():
            tiny.rgb.set_rgb(*PRESSED_COLOUR)
        else:
            tiny.rgb.set_rgb(*RELEASED_COLOUR)

# Turn off all the outputs
finally:
    tiny.shutdown()
