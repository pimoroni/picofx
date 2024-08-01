from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import BlinkWaveFX

"""
Play a wave of blinks on TinyFX's outputs.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control TinyFX's mono outputs


# Create a BlinkWaveFX effect
wave = BlinkWaveFX(speed=1.0,       # The speed to blink at, with 1.0 being 1 second
                   length=6.0,      # The length of the wave before positions repeat. Usually the number of outputs (6)
                   phase=0.0,       # How far through the blink to start the effect (from 0.0 to 1.0)
                   duty=0.5)        # How long the blink is on for (from 0.0 to 1.0)


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
