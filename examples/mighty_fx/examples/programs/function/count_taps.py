import time

from mighty_fx import MightyFX

"""
Count taps of Mighty FX's Boot button and show the count on its RGB outputs, including
the taps made while the board is busy.

Each pass of the loop sleeps in place of real work. Taps are caught by interrupt, so every
one made during the sleep is counted. boot_pressed() reports only the button's state at
the moment it is asked.

Tap the button several times during a sleep to see them all arrive together. Hold it
down to exit the program.
"""

# Constants
BUSY_TIME = 1.0                         # The time (in seconds) each pass spends busy
TAP_COLOUR = (0, 128, 255)              # The colour an output lights to count a tap

# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # The taps since this was last asked, which empties the count
        taps = mighty.boot_taps()
        print("Taps =", taps)

        # One output per tap, up to as many outputs as the board has
        for i, output in enumerate(mighty.outputs):
            if i < taps:
                output.set_rgb(*TAP_COLOUR)
            else:
                output.off()

        # Stand in for real work. Taps made now are still counted
        time.sleep(BUSY_TIME)

# Turn off all the outputs
finally:
    mighty.shutdown()
