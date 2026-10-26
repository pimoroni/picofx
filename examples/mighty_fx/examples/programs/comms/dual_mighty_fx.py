from comms.fx import MightyFXControl
from mighty_fx import MightyFX

from picofx import ColourPlayer
from picofx.colour import RainbowWaveFX

"""
Play a rainbow wave across the RGB outputs of this Mighty FX and of a second
Mighty FX connected by I2C and running as an I2CTarget.

For this you will need a Qw/ST cable. Be sure to disconnect / cut the
red power wire before proceeding. This avoids potential damage to your
devices, caused by one board trying to power the other.

When ready, connect the Qw/ST cable from this Mighty FX's Qw/ST port to the
matching port on your second Mighty FX. The second Mighty FX should be running
the i2c_target.py example. Save it as main.py to make it run at power-up.

Press "Boot" to exit the program.
"""

# Constants
ADDRESS = 68                            # The I2C address of the Mighty FX we will be controlling
I2C_FREQUENCY = 400000                  # The frequency to run the I2C bus at (default is 100,000), raised for the 21 channels each update sends
RAINBOW_SPEED = 0.1                     # The speed to cycle through colours at, with 1.0 being 1 second
RAINBOW_LENGTH = 14                     # The length of the rainbow wave before positions repeat. The outputs of both boards (7 + 7)
RAINBOW_SATURATION = 1.0                # The saturation/intensity of the colour (from 0.0 to 1.0)
RAINBOW_VALUE = 1.0                     # The value/brightness of the colour (from 0.0 to 1.0)


# Variables
mighty = MightyFX(i2c_freq=I2C_FREQUENCY)           # Create a new MightyFX object to interact with the board
i2c_mighty = MightyFXControl(mighty.i2c, ADDRESS)   # Create a MightyFXControl object to control the connected board

# Create an effect player to control the outputs of both boards
player = ColourPlayer(mighty.outputs + i2c_mighty.outputs)  # 'outputs' are lists, so can be added together


# Create the rainbow wave effect and set it up to play, this board's outputs first
rainbow = RainbowWaveFX(speed=RAINBOW_SPEED,
                        length=RAINBOW_LENGTH,
                        sat=RAINBOW_SATURATION,
                        val=RAINBOW_VALUE)
player.effects = [rainbow(i) for i in range(len(mighty.outputs) + len(i2c_mighty.outputs))]

player.pair(i2c_mighty)     # Send the connected board its outputs after each update


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not mighty.boot_pressed():
        pass

# End the program by shutting down both boards
finally:
    player.stop()
    i2c_mighty.shutdown()
    mighty.shutdown()
