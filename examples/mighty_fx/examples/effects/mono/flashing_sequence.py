from mighty_fx import MightyFX

from picofx import MonoPlayer
from picofx.mono import FlashSequenceFX

"""
Play a flashing sequence across every colour of MightyFX's outputs.

The burst of flashes travels along them, and each output's red, green and blue take
their turn as it passes, so a run of flashes crosses the board changing colour as it goes.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = MonoPlayer(mighty.monos)       # Create a new effect player to control each colour of MightyFX's outputs


# Create a FlashSequenceFX effect
flashing = FlashSequenceFX(speed=1.0,                   # The speed to flash at, with 1.0 being 1 second
                           length=len(mighty.monos),    # The length of the sequence before positions repeat. Usually the number of them (21)
                           flashes=2,                   # The number of flashes to do within that time
                           window=0.2,                  # How much of the flash time to perform the flashes in
                           phase=0.0,                   # How far through the flash cycle to start the effect (from 0.0 to 1.0)
                           duty=0.5)                    # How long as a percent from 0.0 to 1.0 each flash is on for


# Set up the sequence effect to play. Each one has a different position
# along the sequence, with the value being related to the effect's length
player.effects = [flashing(position) for position in range(len(mighty.monos))]


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
