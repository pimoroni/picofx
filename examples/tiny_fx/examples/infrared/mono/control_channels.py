from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import StaticFX

import aye_arr.logging as logging
from aye_arr.nec import NECRemoteReceiver
from aye_arr.nec.remotes import PimoroniRemote


"""
Turn each of Tiny FX's mono outputs on and off by pressing the number buttons
on the Pimoroni Aye Arr Remote, and hold to adjust their brightness.

Actions:
- (1)-(6) Button [Press] = Toggle Channel
- (1)-(6) Button [Press + Hold] = Increase Brightness (wraps to zero when full)

An IR Stick should be connected to the Sensor port on Tiny FX.

Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 1.0                    # The initial brightess of each channel (from 0.0 to 1.0)
BRIGHTNESS_STEP = 0.02              # The amount to change the brightness by when fading

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = MonoPlayer(tiny.outputs)   # Create a new effect player to control TinyFX's mono outputs


# Create and set up a blink effect to play
player.effects = [
    StaticFX(BRIGHTNESS),
    StaticFX(BRIGHTNESS),
    StaticFX(BRIGHTNESS),
    StaticFX(BRIGHTNESS),
    StaticFX(BRIGHTNESS),
    StaticFX(BRIGHTNESS),
]


# Function to toggle the specified channel
def toggle_mono(channel):
    fx = player.effects[channel - 1]
    if fx is not None:
        fx.brightness = 0.0 if fx.brightness > 0.0 else BRIGHTNESS
    print(f"Toggle Channel #{channel}, Brightness: {fx.brightness:.2f}")


# Function to fade the specified channel
def fade_mono(channel):
    fx = player.effects[channel - 1]
    if fx is not None:
        fx.brightness = (fx.brightness + BRIGHTNESS_STEP) % 1.0
    print(f"Fade Channel #{channel}, Brightness: {fx.brightness:.2f}")


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.bind("1_RED", on_press=None, on_short=(toggle_mono, 1), on_repeat=(fade_mono, 1))
remote.bind("2_GREEN", on_press=None, on_short=(toggle_mono, 2), on_repeat=(fade_mono, 2))
remote.bind("3_BLUE", on_press=None, on_short=(toggle_mono, 3), on_repeat=(fade_mono, 3))
remote.bind("4_CYAN", on_press=None, on_short=(toggle_mono, 4), on_repeat=(fade_mono, 4))
remote.bind("5_MAGENTA", on_press=None, on_short=(toggle_mono, 5), on_repeat=(fade_mono, 5))
remote.bind("6_YELLOW", on_press=None, on_short=(toggle_mono, 6), on_repeat=(fade_mono, 6))

# Set up a receiver on Tiny FX's sensor pin, using PIO 1 and SM 0, and bind the remote to it.
receiver = NECRemoteReceiver(TinyFX.SENSOR_PIN, 1, 0, logging_level=logging.LOG_NONE)
receiver.bind(remote)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    receiver.start()
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while not tiny.boot_pressed():
        # Decode any IR pulses received since the last time this was called.
        # This should be done as frequently as possible to avoid inputs feeling sluggish
        receiver.decode()

# End the program by stopping any active systems
finally:
    receiver.stop()
    player.stop()
    tiny.shutdown()
