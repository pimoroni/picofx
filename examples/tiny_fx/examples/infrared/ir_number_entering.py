from tiny_fx import TinyFX
from picofx import MonoPlayer
from picofx.mono import StaticFX
from aye_arr.nec import NECRemoteReceiver
from aye_arr.nec.remotes import PimoroniRemote
import time

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


def toggle_mono(channel, _, _1):
    fx = player.effects[channel - 1]
    if fx is not None:
        fx.brightness = 0.0 if fx.brightness > 0.0 else BRIGHTNESS


def fade_mono(channel, _, _1):
    fx = player.effects[channel - 1]
    if fx is not None:
        fx.brightness = (fx.brightness + 0.02) % 1.0


numbers = {
    "1/RED": 1,
    "2/GREEN": 2,
    "3/BLUE": 3,
    "4/CYAN": 4,
    "5/MAGENTA": 5,
    "6/YELLOW": 6,
    "7/WARM": 7,
    "8/WHITE": 8,
    "9/COOL": 9,
    "0/RAINBOW": 0,
}

last_press = time.ticks_ms()
word = ""


def known(cmd, now, last):
    global last_press
    global word
    try:
        num = numbers[cmd]
    except KeyError:
        return False

    print(str(num), end="")
    word += str(num)
    last_press = now
    return True


# Bind functions to each of the Pimoroni remote's buttons.
remote = PimoroniRemote()
remote.on_known = known

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

        if time.ticks_diff(time.ticks_ms(), last_press) >= 800 and len(word) > 0:
            print(": ", word)
            word = ""

# Stop any running effects and turn off all the outputs
finally:
    receiver.stop()
    player.stop()
    tiny.shutdown()
