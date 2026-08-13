from mighty_fx import MightyFX

from picofx import MonoPlayer
from picofx.mono import PulseWaveFX

"""
Play a wave of pulses across every colour of MightyFX's outputs.

They run red, green then blue along each output, so a wave sweeping them fades an
output's three components up in turn: it passes through red, yellow, white where all three
are up, then cyan and blue. No colour effect is involved in any of it.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX()                 # Create a new MightyFX object to interact with the board
player = MonoPlayer(mighty.monos)   # Create a new effect player to control each colour of MightyFX's outputs


# Create a PulseWaveFX effect
wave = PulseWaveFX(speed=1.0,                   # The speed to pulse at, with 1.0 being 1 second
                   length=len(mighty.monos),    # The length of the wave before positions repeat. Usually the number of them (21)
                   phase=0.0)                   # How far through the pulse to start the effect (from 0.0 to 1.0)


# Set up the wave effect to play. Each one has a different position
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
