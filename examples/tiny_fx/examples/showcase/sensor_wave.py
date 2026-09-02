from timing import Pacer
from sensor import ANALOG
from tiny_fx import TinyFX

from picofx import MonoPlayer
from picofx.mono import PulseWaveFX

"""
Play a wave of pulses on TinyFX's outputs, who's speed is controlled by a sensor.

Press "Boot" to exit the program.
"""

# Constants
MIN_VOLTAGE = 0     # The min voltage, in volts, the sensor returns
MAX_VOLTAGE = 3.3   # The max voltage, in volts, the sensor returns
MAX_SPEED = 2       # The max speed to play the wave effect at, in either direction
SAMPLES = 50        # The number of measurements to take per reading, to reduce noise
INTERVAL = 0.1      # How often to take a voltage measurement, in seconds


# Variables
tiny = TinyFX(sensor=ANALOG)            # Create a new TinyFX object, with an analog sensor on its connector
player = MonoPlayer(tiny.outputs)       # Create a new effect player to control TinyFX's mono outputs


# Create a PulseWaveFX effect
wave = PulseWaveFX(speed=0.0,           # The speed to pulse at, with 1.0 being 1 second
                   length=6.0,          # The length of the wave before positions repeat. Usually the number of outputs (6)
                   phase=0.0)           # How far through the blink to start the effect (from 0.0 to 1.0)


# Set up the wave effect to play. Each output has a different position
# along the wave, with the value being related to the effect's length
player.effects = [
    wave(0),
    wave(1),
    wave(2),
    wave(3),
    wave(4),
    wave(5)
]


# Reading a sensor takes time of its own, so a pacer holds the readings to the
# interval rather than adding it to each one, as sleeping the whole interval would
pacer = Pacer(INTERVAL)

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()   # Start the effects running

    # Loop until the effect stops or the "Boot" button is pressed
    while player.is_running() and not tiny.boot_pressed():
        # Read the voltage output by the sensor
        voltage = tiny.sensor.read_voltage(SAMPLES)

        # Print out the sensor value to a sensible number of decimal places
        print("Voltage =", round(voltage, 2))

        # Convert the voltage to a percentage of the min to max we want to show
        percent = (voltage - MIN_VOLTAGE) / (MAX_VOLTAGE - MIN_VOLTAGE)

        # Apply the percentage, centred around its middle to the wave
        wave.speed = (percent - 0.5) * 2 * MAX_SPEED

        pacer.hold()

# Stop any running effects and turn off all the outputs
finally:
    player.stop()
    tiny.shutdown()
