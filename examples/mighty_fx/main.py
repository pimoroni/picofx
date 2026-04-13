from mighty_fx import MightyFX
from picofx import ColourPlayer
from picofx.colour import RainbowWaveFX

"""
Play a rainbow wave animation on MightyFX's RGB outputs.

Press "Boot" to exit the program.
"""

# Constants
RAINBOW_SPEED = 0.3                     # The speed to cycle through colours at, with 1.0 being 1 second
RAINBOW_LENGTH = 7                      # The length of the wave before positions repeat. Usually the number of outputs (7)
RAINBOW_SATURATION = 1.0                # The saturation/intensity of the colour (from 0.0 to 1.0)
RAINBOW_VALUE = 1.0                     # The value/brightness of the colour (from 0.0 to 1.0)


# Variables
mighty = MightyFX()
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB output


# Create a PulseWaveFX effect
wave = RainbowWaveFX(speed=RAINBOW_SPEED,
                     length=RAINBOW_LENGTH,
                     sat=RAINBOW_SATURATION,
                     val=RAINBOW_VALUE)

# Set up the wave effect to play. Each output has a different position
# along the wave, with the value being related to the effect's length
player.effects = [
    wave(0),
    wave(1),
    wave(2),
    wave(3),
    wave(4),
    wave(5),
    wave(6)
]


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not mighty.boot_pressed():
        pass

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    mighty.shutdown()
