from comms.fx import TinyFXControl
from mighty_fx import MightyFX

from picofx import ColourPlayer, MonoPlayer
from picofx.colour import RainbowWaveFX
from picofx.mono import PulseWaveFX

"""
Play a rainbow wave across MightyFX's RGB outputs and on to the RGB output of a
TinyFX connected by I2C and running as an I2CTarget, with a pulse wave on the
TinyFX's mono outputs.

For this you will need a Qw/ST cable. Be sure to disconnect / cut the
red power wire before proceeding. This avoids potential damage to your
devices, caused by one board trying to power the other.

When ready, connect the Qw/ST cable from MightyFX's Qw/ST port to the
matching port on your TinyFX. The TinyFX should be running the
i2c_target.py example. Save it as main.py to make it run at power-up.

Press "Boot" to exit the program.
"""

# Constants
ADDRESS = 68                            # The I2C address of the TinyFX we will be controlling
RAINBOW_SPEED = 0.1                     # The speed to cycle through colours at, with 1.0 being 1 second
RAINBOW_LENGTH = 8                      # The length of the rainbow wave before positions repeat. The outputs of both boards (7 + 1)
RAINBOW_SATURATION = 1.0                # The saturation/intensity of the colour (from 0.0 to 1.0)
RAINBOW_VALUE = 1.0                     # The value/brightness of the colour (from 0.0 to 1.0)

WAVE_SPEED = 0.6                        # The speed to pulse at, with 1.0 being 1 second
WAVE_LENGTH = 6 * 2                     # The length of the pulse wave before positions repeat


# Variables
mighty = MightyFX()                             # Create a new MightyFX object to interact with the board
i2c_tiny = TinyFXControl(mighty.i2c, ADDRESS)   # Create a TinyFXControl object to control the connected board

# Create effect players to control the outputs of both boards
rgb_player = ColourPlayer(mighty.outputs + [i2c_tiny.rgb])   # 'outputs' is a list, so the TinyFX's 'rgb' joins it in a list of its own
player = MonoPlayer(i2c_tiny.outputs)


# Create the rainbow wave effect and set it up to play, the connected board's RGB output last
rainbow = RainbowWaveFX(speed=RAINBOW_SPEED,
                        length=RAINBOW_LENGTH,
                        sat=RAINBOW_SATURATION,
                        val=RAINBOW_VALUE)
rgb_player.effects = [rainbow(i) for i in range(len(mighty.outputs) + 1)]

# Create the pulse wave effect and set it up to play on the connected board's mono outputs
wave = PulseWaveFX(speed=WAVE_SPEED,
                   length=WAVE_LENGTH)
player.effects = [wave(i) for i in range(len(i2c_tiny.outputs))]

rgb_player.pair(player)     # Pair the Mono player with the RGB player so they run in sync
player.pair(i2c_tiny)       # Pair the TinyFXControl to the Mono player so it sends commands
                            # to the connected board after all effects have updated


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    rgb_player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while rgb_player.is_running() and not mighty.boot_pressed():
        pass

# End the program by shutting down both boards
finally:
    rgb_player.stop()
    i2c_tiny.shutdown()
    mighty.shutdown()
