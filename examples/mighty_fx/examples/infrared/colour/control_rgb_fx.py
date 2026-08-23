from aye_arr.nec.remotes import PimoroniRemote
from mighty_fx import MightyFX
from sensor import IR

from picofx import ColourPlayer
from picofx.colour import BLACK, BLUE, COOL, CYAN, GREEN, MAGENTA, RED, RGBFX, WARM, WHITE, YELLOW

"""
Set the colour of Mighty FX's seven RGB outputs using the number buttons on the
Pimoroni Aye Arr Remote. This version uses the effects system to interact with
them. One effect drives every output, so they change together.

Actions:
- (1)-(9) Buttons [Press + Hold] = Set Colour
- OK Button [Press + Hold] = Set Black

An IR Stick should be connected to the Sensor port on Mighty FX.

Press "Boot" to exit the program.
"""

# Variables
mighty = MightyFX(sensor=IR)        # Create a new MightyFX object, with the infrared receiver on its sensor connector
player = ColourPlayer(mighty.outputs)   # Create a new effect player to control MightyFX's RGB outputs


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
