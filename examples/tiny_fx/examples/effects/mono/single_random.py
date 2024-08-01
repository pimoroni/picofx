from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import RandomFX

"""
Play a randomly changing brightness effect on one of TinyFX's outputs.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control TinyFX's mono outputs


# Create and set up a blink effect to play
player.effects = [
    RandomFX(interval=0.05,         # The time (in seconds) between each random brightness
             brightness_min=0.0,    # The min brightness to randomly go down to
             brightness_max=1.0),   # The max brightness to randomly go up to

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
