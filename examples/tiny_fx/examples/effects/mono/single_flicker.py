from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import FlickerFX

"""
Play a flickering effect on one of TinyFX's outputs.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control TinyFX's mono outputs


# Create and set up a blink effect to play
player.effects = [
    FlickerFX(brightness=1.0,       # The brightness to use when being bright (from 0.0 to 1.0)
              dimness=0.5,          # How much to dim the brightness by (from 0.0 to 1.0) when being dim
              bright_min=0.05,      # The min amount of time (in seconds) to be bright for
              bright_max=0.1,       # The max amount of time (in seconds) to be bright for
              dim_min=0.02,         # The min amount of time (in seconds) to be dim for
              dim_max=0.04),        # The max amount of time (in seconds) to be dim for

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
