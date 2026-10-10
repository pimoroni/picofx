from mighty_fx import MightyFX

from picofx import MonoPlayer
from picofx.mono import BlinkWaveFX

"""
Play a wave of blinks across every colour of MightyFX's outputs.

Half of them are on at once, so three or four lit outputs sweep along the board. An
output's red, green and blue switch on in turn as the block arrives and off in turn as it
leaves, so each one runs red, yellow, white, then cyan, blue and dark.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX()                 # Create a new MightyFX object to interact with the board
player = MonoPlayer(mighty.monos)   # Create a new effect player to control each colour of MightyFX's outputs


# Create a BlinkWaveFX effect
wave = BlinkWaveFX(speed=1.0,                   # The speed to blink at, with 1.0 being 1 second
                   length=len(mighty.monos),    # The length of the wave before positions repeat. Usually the number of them (21)
                   phase=0.0,                   # How far through the blink to start the effect (from 0.0 to 1.0)
                   duty=0.5)                    # How long the blink is on for (from 0.0 to 1.0)


# Set up the wave effect to play. Each output has a different position
# along the wave, with the value being related to the effect's length
player.effects = [wave(position) for position in range(len(mighty.monos))]


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
