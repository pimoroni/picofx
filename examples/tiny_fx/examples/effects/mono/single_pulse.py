from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import PulseFX

"""
Play a pulsing effect on one of TinyFX's outputs.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control TinyFX's mono outputs


# Create and set up a blink effect to play
player.effects = [
    PulseFX(speed=1.0,              # The speed to pulse at, with 1.0 being 1 second
            phase=0.0),             # How far through the blink to start the effect (from 0.0 to 1.0)

    # No effects played on the rest of the outputs (unnecessary to list, but show for clarity)
    None,
    None,
    None,
    None,
    None,
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
