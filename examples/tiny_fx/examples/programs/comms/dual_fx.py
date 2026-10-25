from tiny_fx import TinyFX
from comms.fx import TinyFXControl

from picofx import ColourPlayer, MonoPlayer
from picofx.colour import RainbowWaveFX
from picofx.mono import PulseWaveFX

"""
Play wave and rainbow animations across the outputs of this TinyFX
and another TinyFX connected by I2C and running as an I2CTarget.

For this you will need a Qw/ST cable. Be sure to disconnect / cut the
red power wire before proceeding. This avoids potential damage to your
devices, caused by one board trying to power the other.

When ready, connect the Qw/ST cable from this Tiny's Qw/ST port to the
matching port on your second TinyFX. The second TinyFX should be running
the i2c_target.py example. Save it as main.py to make it run at power-up.

Press "Boot" to exit the program.
"""

# Constants
ADDRESS = 68                            # The I2C address of the Tiny FX we will be controlling
WAVE_SPEED = 0.6                        # The speed to pulse at, with 1.0 being 1 second
WAVE_LENGTH = 12 * 2                    # The length of the pulse wave before positions repeat

RAINBOW_SPEED = 0.1                     # The speed to cycle through colours at, with 1.0 being 1 second
RAINBOW_LENGTH = 2                      # The length of the rainbow wave before positions repeat
RAINBOW_SATURATION = 1.0                # The saturation/intensity of the colour (from 0.0 to 1.0)
RAINBOW_VALUE = 1.0                     # The value/brightness of the colour (from 0.0 to 1.0)


# Variables
tiny = TinyFX()                                 # Create a new TinyFX object to interact with the board
i2c_tiny = TinyFXControl(tiny.i2c, ADDRESS)     # Create a TinyFXControl object to control the connected board

# Create effect players to control the outputs of both boards
player = MonoPlayer(tiny.outputs + i2c_tiny.outputs)    # 'outputs' are lists, so can be added together
rgb_player = ColourPlayer([tiny.rgb, i2c_tiny.rgb])     # 'rgb' is a single object, so a new list with both is needed


# Create the pulse wave effect and set it up to play
wave = PulseWaveFX(speed=WAVE_SPEED,
                   length=WAVE_LENGTH)
player.effects = [
    # ----- Our Board -----
    wave(0),
    wave(1),
    wave(2),
    wave(3),
    wave(4),
    wave(5),

    # ----- Connected Board -----
    wave(7),
    wave(8),
    wave(9),
    wave(10),
    wave(11),
    wave(12)
]

# Create the rainbow wave effect and set it up to play
rainbow = RainbowWaveFX(speed=RAINBOW_SPEED,
                        length=RAINBOW_LENGTH,
                        sat=RAINBOW_SATURATION,
                        val=RAINBOW_VALUE)
rgb_player.effects = [
    rainbow(0),     # Our Board
    rainbow(1)      # Connected Board
]

player.pair(rgb_player)     # Pair the RGB player with the Mono player so they run in sync
rgb_player.pair(i2c_tiny)   # Pair the TinyFXControl to the RGB player so it sends commands
                            # to the connected board after all effects have updated


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not tiny.boot_pressed():
        pass

# End the program by shutting down the board
finally:
    player.stop()
    i2c_tiny.shutdown()
    tiny.shutdown()
