import time

from mighty_fx import MightyFX, SPCE
from motor_driver import MotorDriver

"""
Play an evocative musical melody on MightyFX's motors, on a driver on SP/CE port A.
Any resemblance to music you might have heard elsewhere is purely coincidental.

A motor is switched on and off thousands of times a second, and that switching is
audible if it happens slowly enough. Setting the frequency to a note's frequency makes
the coils sing it, which is the same melody the audio example plays through the
speaker, played by the machinery instead.

The motors alternate direction within each note rather than driving one way, so they
sing without turning. Set STATIONARY to False to hear it while they run.

Press "Boot" to exit the program.
"""

# Constants
TONES = (588, 658, 524, 262, 384, 0)            # The tones to play in order (0 means silence)
DURATIONS = (0.6, 0.6, 0.6, 0.6, 0.6 * 4, 2.0)  # The duration of each tone (in seconds)
VOLUME = 0.5            # The duty to switch at, which is how loud a coil sings
STATIONARY = True       # Whether to sing without turning, by alternating direction
TOGGLE_US = 2000        # How long to hold each direction when singing stationary

# Variables
mighty = MightyFX(spce_a=SPCE.MOTOR_DRIVER)
driver = MotorDriver(mighty.spce_a)
index = 0

driver.enable()         # Power the driver, which the board leaves off until asked


# Function to play one note for its duration, by switching the motors at its frequency
def play(tone, duration):
    if not tone:
        for motor in driver.motors:
            motor.stop()
        time.sleep(duration)
        return

    for motor in driver.motors:
        motor.frequency(tone)

    if STATIONARY:
        # A note is held by driving one way and then the other, each too briefly to
        # turn the motor, so the coil sings where the shaft stays put
        held = 0
        while held < duration * 1000000:
            for motor in driver.motors:
                motor.duty(VOLUME)
            time.sleep_us(TOGGLE_US)
            for motor in driver.motors:
                motor.duty(-VOLUME)
            time.sleep_us(TOGGLE_US)
            held += TOGGLE_US * 2
    else:
        for motor in driver.motors:
            motor.duty(VOLUME)
        time.sleep(duration)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        print("Tone =", TONES[index], "Hz")
        play(TONES[index], DURATIONS[index])

        # Move on to the next tone
        index += 1
        index %= len(TONES)

# Stop the motors, take the driver's power away and turn off all the outputs
finally:
    mighty.shutdown()
