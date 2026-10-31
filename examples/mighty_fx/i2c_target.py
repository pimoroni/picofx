from comms.fx import MightyFXTarget
from mighty_fx import MightyFX

"""
Turn your Mighty FX into an I2C target that can be controlled by other devices!

For this you will need a Qw/ST cable. Be sure to disconnect / cut the
red power wire before proceeding. This avoids potential damage to your
devices, caused by one board trying to power the other.

When ready, connect the Qw/ST cable from your Mighty FX's port to the Qw/ST port
on your I2C host board. Finally, save this program to your Mighty FX as main.py
with a unique address and press reset to set it running.

Your Mighty FX will now appear to your I2C host board as an I2C device at the
address you have given, and can be controlled by it.

Refer to the Mighty FX Host example for details of how to control your Mighty FX Target.
"""

# Constants
ADDRESS = 68                            # The I2C address to use for the target device
COLOUR = 255, 255, 255                  # The colour (as r, g, b) to set output one to when powering up

# Variables
mighty = MightyFX(init_i2c=False)           # Create a new MightyFX object without initialising its I2C
target = MightyFXTarget(mighty, ADDRESS)    # Create a MightyFXTarget to allow control of mighty over I2C

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Turn on output one to show the program is running
    mighty.one.set_rgb(*COLOUR)

    # Loop forever
    while True:
        # Process any I2C requests received since the last time this was called.
        # This should be done as frequently as possible to avoid interactions feeling sluggish
        target.process_i2c()

# End the program by shutting down the board
finally:
    mighty.shutdown()
    target.deinit()
