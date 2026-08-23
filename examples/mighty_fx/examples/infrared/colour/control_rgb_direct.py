from aye_arr.nec.remotes import PimoroniRemote
from mighty_fx import MightyFX
from sensor import IR

from picofx.colour import BLACK, BLUE, COOL, CYAN, GREEN, MAGENTA, RED, WARM, WHITE, YELLOW

"""
Set the colour of Mighty FX's seven RGB outputs using the number buttons on the
Pimoroni Aye Arr Remote. This version interacts with the outputs directly.

Actions:
- (1)-(9) Buttons [Press + Hold] = Set Colour
- OK Button [Press + Hold] = Set Black

An IR Stick should be connected to the Sensor port on Mighty FX.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX(sensor=IR)        # Create a new MightyFX object, with the infrared receiver on its sensor connector


# Function called when a colour button is pressed
def set_outputs(colour):
    for output in mighty.outputs:
        output.set_rgb(*colour)
    print(f"Colour = #{colour[0]:02x}{colour[1]:02x}{colour[2]:02x}")


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.bind("1_RED", (set_outputs, RED))
remote.bind("2_GREEN", (set_outputs, GREEN))
remote.bind("3_BLUE", (set_outputs, BLUE))
remote.bind("4_CYAN", (set_outputs, CYAN))
remote.bind("5_MAGENTA", (set_outputs, MAGENTA))
remote.bind("6_YELLOW", (set_outputs, YELLOW))
remote.bind("7_WARM", (set_outputs, WARM))
remote.bind("8_WHITE", (set_outputs, WHITE))
remote.bind("9_COOL", (set_outputs, COOL))
remote.bind("OK_STOP", (set_outputs, BLACK))

# Take the receiver the board set up, and bind the remote to it.
receiver = mighty.sensor
receiver.bind(remote)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Loop until the effect stops or the "Boot" button is pressed
    while not mighty.boot_pressed():
        # Decode any IR pulses received since the last time this was called.
        # This should be done as frequently as possible to avoid inputs feeling sluggish
        receiver.decode()

# End the program by stopping any active systems
finally:
    mighty.shutdown()
