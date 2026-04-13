from tiny_fx import TinyFX
from picofx import MonoPlayer, ColourPlayer
from picofx.mono import PulseWaveFX
from picofx.colour import RainbowFX

"""
Play a wave animation on TinyFX's mono outputs, and a rainbow on its RGB output.

Press "Boot" to exit the program.
"""

# Constants
WAVE_SPEED = 0.6                        # The speed to pulse at, with 1.0 being 1 second
WAVE_LENGTH = 6                         # The length of the wave before positions repeat. Usually the number of outputs (6)

RAINBOW_SPEED = 0.1                     # The speed to cycle through colours at, with 1.0 being 1 second
RAINBOW_SATURATION = 1.0                # The saturation/intensity of the colour (from 0.0 to 1.0)
RAINBOW_VALUE = 1.0                     # The value/brightness of the colour (from 0.0 to 1.0)


# Variables
tiny = TinyFX()                         # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)       # Create a new effect player to control TinyFX's mono outputs
rgb_player = ColourPlayer(tiny.rgb)     # Create a new effect player to control TinyFX's RGB output


# Create a PulseWaveFX effect
wave = PulseWaveFX(speed=WAVE_SPEED,
                   length=WAVE_LENGTH)

# Set up the wave effect to play. Each output has a different position
# along the wave, with the value being related to the effect's length
player.effects = [
    wave(0),
    wave(1),
    wave(2),
    wave(3),
    wave(4),
    wave(5)
]

# Create and set up a rainbow effect to play
rgb_player.effects = RainbowFX(speed=RAINBOW_SPEED,
                               sat=RAINBOW_SATURATION,
                               val=RAINBOW_VALUE)

# Pair the RGB player with the Mono player so they run in sync
player.pair(rgb_player)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not tiny.boot_pressed():
        pass

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    tiny.shutdown()
