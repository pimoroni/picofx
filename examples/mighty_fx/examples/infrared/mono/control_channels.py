from aye_arr.nec.remotes import PimoroniRemote
from mighty_fx import MightyFX
from sensor import IR

from picofx import ColourPlayer
from picofx.colour import BLUE, CYAN, GREEN, MAGENTA, RED, WARM, YELLOW
from picofx.mono import StaticFX

"""
Turn each of Mighty FX's outputs on and off by pressing the number buttons on the
Pimoroni Aye Arr Remote, and hold to adjust their brightness.

Each output lights in the colour its own button is marked with, so pressing the blue
button lights the blue output. The effect brings no colour of its own: it gives a
brightness, and the player draws it in the colour the output was given.

Actions:
- (1)-(7) Button [Press] = Toggle Output
- (1)-(7) Button [Press + Hold] = Increase Brightness (wraps to zero when full)

An IR Stick should be connected to the Sensor port on Mighty FX.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 1.0                        # The initial brightess of each output (from 0.0 to 1.0)
BRIGHTNESS_STEP = 0.02                  # The amount to change the brightness by when fading

# Variables
mighty = MightyFX(sensor=IR)            # Create a new MightyFX object, with the infrared receiver on its sensor connector
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs


# The colour each output draws its light in, matching the button that toggles it
player.colours = [RED, GREEN, BLUE, CYAN, MAGENTA, YELLOW, WARM]


# Create and set up a static effect to play on every output
player.effects = [StaticFX(BRIGHTNESS) for _ in mighty.outputs]


# Function to toggle the specified output
def toggle_output(output):
    fx = player.effects[output - 1]
    if fx is not None:
        fx.brightness = 0.0 if fx.brightness > 0.0 else BRIGHTNESS
    print(f"Toggle Output #{output}, Brightness: {fx.brightness:.2f}")


# Function to fade the specified output
def fade_output(output):
    fx = player.effects[output - 1]
    if fx is not None:
        fx.brightness = (fx.brightness + BRIGHTNESS_STEP) % 1.0
    print(f"Fade Output #{output}, Brightness: {fx.brightness:.2f}")


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.bind("1_RED", on_press=None, on_short=(toggle_output, 1), on_repeat=(fade_output, 1))
remote.bind("2_GREEN", on_press=None, on_short=(toggle_output, 2), on_repeat=(fade_output, 2))
remote.bind("3_BLUE", on_press=None, on_short=(toggle_output, 3), on_repeat=(fade_output, 3))
remote.bind("4_CYAN", on_press=None, on_short=(toggle_output, 4), on_repeat=(fade_output, 4))
remote.bind("5_MAGENTA", on_press=None, on_short=(toggle_output, 5), on_repeat=(fade_output, 5))
remote.bind("6_YELLOW", on_press=None, on_short=(toggle_output, 6), on_repeat=(fade_output, 6))
remote.bind("7_WARM", on_press=None, on_short=(toggle_output, 7), on_repeat=(fade_output, 7))

# Take the receiver the board set up, and bind the remote to it.
receiver = mighty.sensor
receiver.bind(remote)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while not mighty.boot_pressed():
        # Decode any IR pulses received since the last time this was called.
        # This should be done as frequently as possible to avoid inputs feeling sluggish
        receiver.decode()

# End the program by stopping any active systems
finally:
    player.stop()
    mighty.shutdown()
