from tiny_fx import TinyFX
from comms.fx import TinyFXTarget

"""
Turn your Tiny FX into an I2C target that can be controlled by other devices!

For this you will need a Qw/ST cable. Be sure to disconnect / cut the
red power wire before proceeding. This avoids potential damage to your
devices, caused by one board trying to power the other.

When ready, connect the Qw/ST cable from your Tiny's port to the Qw/ST port
on your I2C host board. Finally, save this program to your Tiny FX as main.py
with a unique address and press reset to set it running.

Your Tiny FX will now appear to your I2C host board as an I2C device at the
address you have given, and can be controlled by it.

Refer to the Tiny FX Host example for details of how to control your Tiny FX Target.
"""

# Constants
ADDRESS = 0x43                          # The I2C address to use for the target device
COLOUR = 255, 255, 255                  # The colour (as r, g, b) to set the RGB LED to when powering up

# Variables
tiny = TinyFX(init_i2c=False)           # Create a new TinyFX object without initialising its I2C
target = TinyFXTarget(tiny, ADDRESS)    # Create a TinyFXTarget to allow control of tiny over I2C

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Turn on the RGB LED to show the program is running
    tiny.rgb.set_rgb(*COLOUR)

    # Loop forever
    while True:
        # Process any I2C requests received since the last time this was called.
        # This should be done as frequently as possible to avoid interactions feeling sluggish
        target.process_i2c()

# End the program by shutting down the board
finally:
    tiny.shutdown()
    target.shutdown()
