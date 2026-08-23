import time

from tiny_fx import TinyFX

"""
Count taps of TinyFX's Boot button, including the ones that happen while the board is
busy, and show the count on its mono outputs.

Each pass of the loop sleeps, which stands in for whatever real work a program does
between one look at the button and the next. Taps are caught by interrupt, so every
one made during that sleep is counted, where boot_pressed() only ever reports the
button's state at the moment it is asked.

Tap the button several times during a sleep to see them all arrive together. Hold it
down to exit the program.
"""

# Constants
BUSY_TIME = 1.0     # The time (in seconds) each pass spends busy
BRIGHTNESS = 0.6    # The brightness an output lights to count a tap

# Variables
tiny = TinyFX()     # Create a new TinyFX object to interact with the board


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not tiny.boot_pressed():
        # The taps since this was last asked, which empties the count
        taps = tiny.boot_taps()
        print("Taps =", taps)

        # One output per tap, up to as many outputs as the board has
        for i, output in enumerate(tiny.outputs):
            output.brightness(BRIGHTNESS if i < taps else 0)

        # Stand in for real work. Taps made now are still counted
        time.sleep(BUSY_TIME)

# Turn off all the outputs
finally:
    tiny.shutdown()
