from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import StaticFX
from aye_arr.nec import NECRemoteReceiver
from aye_arr.nec.remotes import PimoroniRemote


"""
Press "Boot" to exit the program.
"""

# Constants
BRIGHTNESS = 1.0    # The brightness (from 0.0 to 1.0)

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


def toggle_mono(channel):
    fx = player.effects[channel - 1]
    if fx is not None:
        fx.brightness = 0.0 if fx.brightness > 0.0 else BRIGHTNESS


def fade_mono(channel):
    fx = player.effects[channel - 1]
    if fx is not None:
        fx.brightness = (fx.brightness + 0.02) % 1.0


# Bind functions to each of the Pimoroni remote's buttons.
remote = PimoroniRemote()
remote.bind("1_RED", on_press=None, on_repeat=(fade_mono, 1), on_short=(toggle_mono, 1))
remote.bind("2_GREEN", on_press=None, on_repeat=(fade_mono, 2), on_short=(toggle_mono, 2), )
remote.bind("3_BLUE", on_press=None, on_repeat=(fade_mono, 3), on_short=(toggle_mono, 3))
remote.bind("4_CYAN", on_press=None, on_repeat=(fade_mono, 4), on_short=(toggle_mono, 4))
remote.bind("5_MAGENTA", on_press=None, on_repeat=(fade_mono, 5), on_short=(toggle_mono, 5))
remote.bind("6_YELLOW", on_press=None, on_repeat=(fade_mono, 6), on_short=(toggle_mono, 6))

# Set up the IR receiver on GP26, using PIO 1 and SM 0
receiver = NECRemoteReceiver(TinyFX.SENSOR_PIN, 1, 0, debug_pin_base=TinyFX.RGB_PINS[0])
receiver.bind(remote)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    receiver.start()
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while not tiny.boot_pressed():
        receiver.decode()

# Stop any running effects and turn off all the outputs
finally:
    receiver.stop()
    player.stop()
    tiny.shutdown()
