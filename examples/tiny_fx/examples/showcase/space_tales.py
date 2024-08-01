from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import PulseFX, RandomFX, StaticFX, BlinkFX

"""
Play effects for each space themed "postcard".

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                     # Create a new TinyFX object
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control TinyFX's mono outputs

# Set up the effects to play
player.effects = [
    PulseFX(speed=0.2),
    RandomFX(interval=0.01, brightness_min=0.5, brightness_max=1.0),
    StaticFX(brightness=0.5),
    BlinkFX(speed=0.5),
    None,
    None
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
