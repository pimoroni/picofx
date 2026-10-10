from mighty_fx import MightyFX
from picofx import ColourPlayer
from picofx.colour import HueStepFX

"""
Step MightyFX's seven RGB outputs around the colour wheel together, each one holding its own place in it.

Press "Boot" to exit the program.
"""

# Constants
INTERVAL = 1.0      # The time (in seconds) between each hue step
STEPS = 6           # The number of steps to take around the colour wheel
SATURATION = 1.0    # The saturation/intensity of the colours (from 0.0 to 1.0)
VALUE = 1.0         # The value/brightness of the colours (from 0.0 to 1.0)


# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs


# Set up a stepped hue effect on each output, each starting from a different hue so the
# whole board moves around the wheel at once without any two outputs matching
num_outputs = len(mighty.outputs)
player.effects = [HueStepFX(interval=INTERVAL,
                            hue=i / num_outputs,
                            sat=SATURATION,
                            val=VALUE,
                            steps=STEPS) for i in range(num_outputs)]


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
