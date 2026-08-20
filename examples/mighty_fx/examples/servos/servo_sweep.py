import time
from mighty_fx import MightyFX

"""
Sweep a servo from end to end on the L connector.

Plug a servo into the connector marked L. Both L and R share one power rail, so
anything on R is live too as soon as a servo or a strip is declared. Press "Boot" to
exit the program.

L shares a PWM channel with SP/CE A's backlight and R shares one with SP/CE B's, so a
servo and a screen cannot have the same side. Declaring both is refused, and the
message names the other connector.
"""

# Constants
STEP_INTERVAL = 0.02    # The time (in seconds) between each step of the sweep
STEP = 2                # How far along the sweep each step moves, as a percentage


# Variables
mighty = MightyFX(servo_l=True)         # Create a new MightyFX object, with a servo on L
servo = mighty.servo_l                  # The servo itself, which the board built and powered
position = 0
heading = STEP

servo.enable()                          # Start driving it, which a servo waits for


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Somewhere between the ends of the servo's travel, as a percentage of it
        servo.to_percent(position)

        position += heading
        if position >= 100 or position <= 0:
            heading = -heading

        time.sleep(STEP_INTERVAL)

# Stop driving the servo, drop the connectors' power and turn off all the outputs
finally:
    mighty.shutdown()
