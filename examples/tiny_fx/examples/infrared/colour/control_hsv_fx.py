from tiny_fx import TinyFX
from picofx import ColourPlayer
from picofx.colour import HSVFX, H_RED, H_GREEN, H_BLUE, H_CYAN, H_MAGENTA, H_YELLOW, H_WARM, H_WHITE, H_COOL, H_BLACK

import aye_arr.logging as logging
from aye_arr.nec import NECRemoteReceiver
from aye_arr.nec.remotes import PimoroniRemote

"""
Set the colour of Tiny FX's onboard RGB LED using the number buttons
on the Pimoroni Aye Arr Remote, and change its hue, saturation, and value
using the directional buttons. This version uses the effects system
to interact with the LED.

Actions:
- (1)-(9) Buttons [Press + Hold] = Set Colour
- OK Button [Press + Hold] = Set Black

An IR Stick should be connected to the Sensor port on Tiny FX.

Press "Boot" to exit the program.
"""

# Constants
HUE_STEP = 0.01         # The amount that hue will change by with each press / repeat
SAT_STEP = 0.01         # The amount that saturation will change by with each press / repeat
VAL_STEP = 0.05         # The amount that value will change by with each press / repeat

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
player = ColourPlayer(tiny.rgb)     # Create a new effect player to control TinyFX's RGB output

# Create and set up a static colour effect to "play"
hsv = HSVFX(*H_BLACK)
player.effects = hsv


# Function called when a colour button is pressed
def set_hsv(colour):
    global hsv
    hsv.hue, hsv.sat, hsv.val = colour
    print(f"H = {hsv.hue:.2}, S = {hsv.sat:.2}, V = {hsv.val:.2}")


# Function called to change the hue of the colour
def cycle_hue(amount):
    global hsv
    hsv.hue = (hsv.hue + amount) % 1.0
    print(f"H = {hsv.hue:.2}, S = {hsv.sat:.2}, V = {hsv.val:.2}")


# Function called to change the saturation of the colour
def adjust_sat(amount):
    global hsv
    hsv.sat = max(min(hsv.sat + amount, 1.0), 0.0)
    print(f"H = {hsv.hue:.2}, S = {hsv.sat:.2}, V = {hsv.val:.2}")


# Function called to change the value (brightness) of the colour
def adjust_val(amount):
    global hsv
    hsv.val = max(min(hsv.val + amount, 1.0), 0.0)
    print(f"H = {hsv.hue:.2}, S = {hsv.sat:.2}, V = {hsv.val:.2}")


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.bind("1_RED", (set_hsv, H_RED))
remote.bind("2_GREEN", (set_hsv, H_GREEN))
remote.bind("3_BLUE", (set_hsv, H_BLUE))
remote.bind("4_CYAN", (set_hsv, H_CYAN))
remote.bind("5_MAGENTA", (set_hsv, H_MAGENTA))
remote.bind("6_YELLOW", (set_hsv, H_YELLOW))
remote.bind("7_WARM", (set_hsv, H_WARM))
remote.bind("8_WHITE", (set_hsv, H_WHITE))
remote.bind("9_COOL", (set_hsv, H_COOL))
remote.bind("OK_STOP", (set_hsv, H_BLACK))
remote.bind("CLOCKWISE", (cycle_hue, HUE_STEP))
remote.bind("ANTICLOCK", (cycle_hue, -HUE_STEP))
remote.bind("RIGHT", (adjust_sat, SAT_STEP))
remote.bind("LEFT", (adjust_sat, -SAT_STEP))
remote.bind("UP", (adjust_val, VAL_STEP))
remote.bind("DOWN", (adjust_val, -VAL_STEP))

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
