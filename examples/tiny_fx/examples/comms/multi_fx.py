import time

from tiny_fx import TinyFX
from comms.fx import TinyFXControl

from picofx import ColourPlayer, MonoPlayer
from picofx.colour import RainbowWaveFX
from picofx.mono import PulseWaveFX

"""
Play wave and rainbow animations across the outputs of this TinyFX
and multiple other TinyFX's connected by I2C and running as an I2CTarget.

For this you will need Qw/ST cables and hubs to connect all of the board together.
Be sure to leave the red power wire disconnected / cut to avoid potential damage
to your devices, caused by the boards all trying the power each other.

All connected Tiny's should be running the i2c_target.py example (save it as main.py
to have it run from power-up), and each should have a unique address.

Press "Boot" to exit the program.
"""

# Constants
START_ADDRESS = 68                          # The I2C address of the first Tiny FX we will be controlling
NUM_I2C_TINYS = 5                           # The number of Tiny FX's being controlled, each with sequential addresses
I2C_FREQUENCY = 400000                      # The frequency to run the I2C bus at (default is 100,000)
UPDATE_RATE = 30                            # The update rate to run the effects system at (default is 100)

WAVE_SPEED = 0.6                            # The speed to pulse at, with 1.0 being 1 second
WAVE_LENGTH = 6 * (NUM_I2C_TINYS + 1) * 2   # The length of the pulse wave before positions repeat

RAINBOW_SPEED = 0.1                         # The speed to cycle through colours at, with 1.0 being 1 second
RAINBOW_LENGTH = (NUM_I2C_TINYS + 1)        # The length of the rainbow wave before positions repeat
RAINBOW_SATURATION = 1.0                    # The saturation/intensity of the colour (from 0.0 to 1.0)
RAINBOW_VALUE = 1.0                         # The value/brightness of the colour (from 0.0 to 1.0)


# Variables
tiny = TinyFX(i2c_freq=I2C_FREQUENCY)           # Create a new TinyFX object to interact with the board

# Create a TinyFXControl object for each connected board to be controlled
i2c_tinys = [TinyFXControl(tiny.i2c, START_ADDRESS + i) for i in range(NUM_I2C_TINYS)]

# Combine their mono and colour outputs into unified lists
outputs = list(tiny.outputs) # Create copy of list
rgbs = [tiny.rgb]
for i2c_tiny in i2c_tinys:
    outputs += i2c_tiny.outputs
    rgbs.append(i2c_tiny.rgb)

# Create effects players to control the outputs of both boards
player = MonoPlayer(outputs)
rgb_player = ColourPlayer(rgbs)


# Create the pulse wave effect and set it up to play across all boards
wave = PulseWaveFX(speed=WAVE_SPEED,
                   length=WAVE_LENGTH)
player.effects = [wave(i) for i in range(len(outputs))]

# Create the rainbow wave effect and set it up to play across all boards
rainbow = RainbowWaveFX(speed=RAINBOW_SPEED,
                        length=RAINBOW_LENGTH,
                        sat=RAINBOW_SATURATION,
                        val=RAINBOW_VALUE)
rgb_player.effects = [rainbow(i) for i in range(len(rgbs))]


# Create a class that can be paired with an EffectPlayer, to update all connected Tiny's
class Updater:
    def __update(self, timer):
        for i2c_tiny in i2c_tinys:
            i2c_tiny.__update(timer)


player.pair(rgb_player)     # Pair the RGB player with the Mono player so they run in sync
rgb_player.pair(Updater())  # Pair a Updater to the RGB player so it sends commands
                            # to the connected boards after all effects have updated


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start(UPDATE_RATE)   # Start the effects running at a different update rate to normal

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not tiny.boot_pressed():
        # Report the update rates and timings, so we know if the effects
        # system can handle the number of boards being controlled
        print(f"Measured fps: {player.measured_fps():.2f}, Target fps: {player.target_fps():.2f}", end=", ")
        print(f"Measured ms: {player.measured_ms()}, Target ms: {player.target_ms()}")
        time.sleep(0.5)

# End the program by shutting down the board
finally:
    player.stop()
    for i2c_tiny in i2c_tinys:
        i2c_tiny.shutdown()
    tiny.shutdown()
