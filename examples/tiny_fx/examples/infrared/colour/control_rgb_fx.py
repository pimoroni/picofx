from tiny_fx import TinyFX
from picofx import ColourPlayer
from picofx.colour import RGBFX, RED, GREEN, BLUE, CYAN, MAGENTA, YELLOW, WARM, WHITE, COOL, BLACK

import aye_arr.logging as logging
from aye_arr.nec import NECRemoteReceiver
from aye_arr.nec.remotes import PimoroniRemote

"""
Set the colour of Tiny FX's onboard RGB LED using the number buttons
on the Pimoroni Aye Arr Remote. This version uses the effects system
to interact with the LED.

Actions:
- (1)-(9) Buttons [Press + Hold] = Set Colour
- OK Button [Press + Hold] = Set Black

An IR Stick should be connected to the Sensor port on Tiny FX.

Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = ColourPlayer(tiny.rgb)     # Create a new effect player to control TinyFX's RGB output


# Create and set up a static colour effect to "play"
rgb = RGBFX(*BLACK)
player.effects = rgb


# Function called when a colour button is pressed
def set_led(colour):
    rgb.red, rgb.green, rgb.blue = colour
    print(f"Colour = #{colour[0]:02x}{colour[1]:02x}{colour[2]:02x}")


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.bind("1_RED", (set_led, RED))
remote.bind("2_GREEN", (set_led, GREEN))
remote.bind("3_BLUE", (set_led, BLUE))
remote.bind("4_CYAN", (set_led, CYAN))
remote.bind("5_MAGENTA", (set_led, MAGENTA))
remote.bind("6_YELLOW", (set_led, YELLOW))
remote.bind("7_WARM", (set_led, WARM))
remote.bind("8_WHITE", (set_led, WHITE))
remote.bind("9_COOL", (set_led, COOL))
remote.bind("OK_STOP", (set_led, BLACK))

# Set up a receiver on the RX pin, using PIO 1 and SM 0, and bind the remote to it.
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
