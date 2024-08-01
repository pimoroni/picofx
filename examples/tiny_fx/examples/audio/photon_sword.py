import time
from tiny_fx import TinyFX
from picofx.colour import WHITE
from breakout_msa301 import BreakoutMSA301

"""
Play sounds that react to motion with a TinyFX.
Grab yourself an MSA301 and attach it to the Qw/St connector.

This example needs the directory `photon_sword` copied over to your TinyFX.

Absolutely definitely not a l&%t s&^@*r.

Press Boot to power up, swing to make do sounds! SWOOSH SWOOOOSH!!! and press Boot to power down
"""

# Constants
TRIGGER_DELTA = 1.0                         # How much movement change is needed to trigger a swinging sound
ANIMATION_SLEEP = 0.05                      # The time to sleep between each step of the start and finish animations

# Variables
tiny = TinyFX(wav_root="/photon_sword")     # Create a new TinyFX object and tell with where the wav files are located
msa = BreakoutMSA301(tiny.i2c)              # Create a new MSA301 object for reading acceleration data
last_axes = None                            # The last accelerometer values measured

# Set up the MSA301
msa.enable_interrupts(BreakoutMSA301.FREEFALL | BreakoutMSA301.ORIENTATION)


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Loop forever
    while True:
        tiny.rgb.set_rgb(*WHITE)    # Show that the program is ready

        # Wait for the Boot button to be pressed
        while not tiny.boot_pressed():
            pass
        tiny.clear()                # Show that the program is running

        # Play the start sound and wait for it to finish
        tiny.wav.play_wav("ps-start.wav")
        while tiny.wav.is_playing():
            # Whilst playing animate the outputs
            for i in range(len(tiny.outputs)):
                tiny.outputs[i].on()
                time.sleep(0.05)

        # Loop forever, again
        while True:

            # If nothing is playing, play a looping idle sound
            if not tiny.wav.is_playing():
                tiny.wav.play_wav("ps-idle.wav", True)

            # Read acceleration data from the MSA301
            this_axes = msa.get_x_axis(), msa.get_y_axis(), msa.get_z_axis()
            if last_axes is not None:
                deltas = [abs(this_axes[n] - last_axes[n]) for n in range(3)]
                delta = max(deltas)
                # If the delta is above the threshold
                if delta > TRIGGER_DELTA:
                    # Select a swing sound to play
                    swing = deltas.index(delta) + 1
                    file = f"ps-swing{swing}.wav"
                    tiny.wav.play_wav(file)
                    print(file)

            # Record the last acceleration, for calculating the next deltas
            last_axes = this_axes
            time.sleep(0.05)

            # Check if the boot button has been pressed
            if tiny.boot_pressed():
                tiny.wav.play_wav("ps-finish.wav")
                while tiny.wav.is_playing():
                    # Whilst playing animate the outputs
                    for i in range(len(tiny.outputs)):
                        tiny.outputs[len(tiny.outputs) - i - 1].off()
                        time.sleep(0.05)

                # Break out of the inner loop
                break

# Turn off all the outputs and audio
finally:
    tiny.shutdown()
