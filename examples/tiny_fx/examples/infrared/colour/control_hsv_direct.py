from tiny_fx import TinyFX
from picofx.colour import H_RED, H_GREEN, H_BLUE, H_CYAN, H_MAGENTA, H_YELLOW, H_WARM, H_WHITE, H_COOL, H_BLACK

from aye_arr.nec import NECRemoteReceiver
from aye_arr.nec.remotes import PimoroniRemote

"""
Set the colour of Tiny FX's onboard RGB LED using the number buttons
on the Pimoroni Aye Arr Remote, and change its hue, saturation, and value
using the directional buttons. This version interacts with the LED directly.

Actions:
- (1)-(9) Button [Press + Hold] = Set Colour
- OK_STOP Button [Press + Hold] = Set Black
- UP Button [Press + Hold] = Increase Value
- DOWN Button [Press + Hold] = Decrease Value
- LEFT Button [Press + Hold] = Decrease Saturation
- RIGHT Button [Press + Hold] = Increase Saturation
- ANTICLOCK Button [Press + Hold] = Decrease Hue
- CLOCKWISE Button [Press + Hold] = Increase Hue

An IR Stick should be connected to the Sensor port on Tiny FX.

Press "Boot" to exit the program.
"""

# Constants
HUE_STEP = 0.01         # The amount that hue will change by with each press / repeat
SAT_STEP = 0.01         # The amount that saturation will change by with each press / repeat
VAL_STEP = 0.05         # The amount that value will change by with each press / repeat

# Variables
tiny = TinyFX()                     # Create a new TinyFX object to interact with the board
led = tiny.rgb                      # Get a reference to the RGB output of TinyFX
hue = 0
sat = 0
val = 0


# Function called when a colour button is pressed
def set_hsv(colour):
    global hue, sat, val
    hue, sat, val = colour
    led.set_hsv(hue, sat, val)
    print(f"H = {hue:.2}, S = {sat:.2}, V = {val:.2}")


# Function called to change the hue of the colour
def cycle_hue(amount):
    global hue
    hue = (hue + amount) % 1.0
    led.set_hsv(hue, sat, val)
    print(f"H = {hue:.2}, S = {sat:.2}, V = {val:.2}")

# Function called to change the saturation of the colour
def adjust_sat(amount):
    global sat
    sat = max(min(sat + amount, 1.0), 0.0)
    led.set_hsv(hue, sat, val)
    print(f"H = {hue:.2}, S = {sat:.2}, V = {val:.2}")


# Function called to change the value (brightness) of the colour
def adjust_val(amount):
    global val
    val = max(min(val + amount, 1.0), 0.0)
    led.set_hsv(hue, sat, val)
    print(f"H = {hue:.2}, S = {sat:.2}, V = {val:.2}")


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
receiver = NECRemoteReceiver(TinyFX.SENSOR_PIN, 1, 0)
receiver.bind(remote)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    receiver.start()

    # Loop forever
    while True:
        # Decode any IR pulses received since the last time this was called.
        # This should be done as frequently as possible to avoid feeling sluggish
        receiver.decode()

# End the program by stopping any active systems
finally:
    receiver.stop()
    led.set_rgb(0, 0, 0)
