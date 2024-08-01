from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import FlashSequenceFX

"""
Play a flashing sequence across TinyFX's outputs.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                         # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)       # Create a new effect player to control TinyFX's mono outputs


# Create a FlashSequenceFX effect
flashing = FlashSequenceFX(speed=1.0,   # The speed to flash at, with 1.0 being 1 second
                           length=6.0,  # The length of the sequence before positions repeat. Usually the number of outputs (6)
                           flashes=2,   # The number of flashes to do within that time
                           window=0.2,  # How much of the flash time to perform the flashes in
                           phase=0.0,   # How far through the flash cycle to start the effect (from 0.0 to 1.0)
                           duty=0.5)    # How long as a percent from 0.0 to 1.0 each flash is on for


# Set up the sequence effect to play. Each output has a different position
# along the wave, with the value being related to the effect's length
player.effects = [
    flashing(0),
    flashing(1),
    flashing(2),
    flashing(3),
    flashing(4),
    flashing(5)
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
