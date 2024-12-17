import time
from tiny_fx import TinyFX
from picofx import ColourPlayer, MonoPlayer
from picofx.colour import RGBBlinkFX, RED, YELLOW, GREEN, CYAN, BLUE, MAGENTA
from picofx.mono import FlashSequenceFX, StaticFX

"""
Play an alternating flashing sequence on two of TinyFX's outputs,
and the RGB channel, recreating the effect of rescue vehicle beacons.
The other outputs are static for illuminated head and tail lights.

Press "Boot" to exit the program, or long press to toggle RGB effects.
"""

# Constants
EMERGENCY = COLOURS = [RED,RED,RED,RED,BLUE,BLUE,BLUE,BLUE]
EMERGENCY_BLINK_SPEED = 8
ORANGE = (228,114,28)
HAZARD = [ORANGE]
HAZARD_BLINK_SPEED = 1.8

# Variables
tiny = TinyFX()                         # Create a new TinyFX object to interact with the board
player = ColourPlayer(tiny.rgb)         # Create a new effect player to control TinyFX's RGB output
monoplayer = MonoPlayer(tiny.outputs)

# Create and set up an red blue flashing effect to play, and a hazard one for later
rgbEffect = RGBBlinkFX(colour=COLOURS,  # The colour (or colours to blink in sequence)
                       phase=0.0,       # The start time in the cycle (0-1)
                       speed=EMERGENCY_BLINK_SPEED, # The speed to cycle through colours at, with 1.0 being 1 second (1/T)
                       duty=0.5) 	    # Amount of the cycle to be "on"

hazardEffect = RGBBlinkFX(colour=HAZARD,  # The colour (or colours to blink in sequence)
                       phase=0.0,       # The start time in the cycle (0-1)
                       speed=HAZARD_BLINK_SPEED, # The speed to cycle through colours at, with 1.0 being 1 second (1/T)
                       duty=0.4) 	    # Amount of the cycle to be "on"

player.effects = [rgbEffect]



# Create a FlashSequenceFX effect for the beacon lights
flashing = FlashSequenceFX(speed=1.0,   # The speed to flash at, with 1.0 being 1 second
                           length=2.0,  # The length of the sequence before positions repeat. Usually the number of outputs (6)
                           flashes=4,   # The number of flashes to do within that time
                           window=0.5)  # How much of the flash time to perform the flashes in

# Create StaticFX for the head and tail lights
headlights = StaticFX(brightness=0.7)
taillights = StaticFX(brightness=0.5)


# Set up the mono effects to play. The first two are flashing, the rest are static
monoplayer.effects = [
    flashing(0),
    flashing(1),
    headlights,
    headlights,
    taillights,
    taillights
]

player.pair(monoplayer)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    t = 0	# keep track of boot press duration
    dont_exit_yet = True
    while dont_exit_yet:
        player.start()   # Start the effects running
        
        # Loop until the effect stops or the "Boot" button is pressed
        while player.is_running() and not tiny.boot_pressed():
            pass
        t = time.ticks_ms()
        while player.is_running() and tiny.boot_pressed():
            pass
        if time.ticks_ms() - t > 500:  	# long press - toggle effect
            player.effects = [hazardEffect] if player.effects[0] is rgbEffect else [rgbEffect]
        else:                         	# short press - exit
            dont_exit_yet = False
# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    tiny.shutdown()

