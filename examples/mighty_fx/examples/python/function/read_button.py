from mighty_fx import MightyFX

from picofx.colour import GREEN, RED

"""
Show the state of MightyFX's Boot button on its RGB outputs.
"""

# Constants
PRESSED_COLOUR = RED        # The colour to show when the boot button is pressed
RELEASED_COLOUR = GREEN     # The colour to show when the boot button is released

# Variables
mighty = MightyFX()         # Create a new MightyFX object to interact with the board


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Loop forever
    while True:
        colour = PRESSED_COLOUR if mighty.boot_pressed() else RELEASED_COLOUR
        for output in mighty.outputs:
            output.set_rgb(*colour)

# Turn off all the outputs
finally:
    mighty.shutdown()
