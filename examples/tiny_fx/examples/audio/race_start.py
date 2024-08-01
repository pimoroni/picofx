import time
from tiny_fx import TinyFX
from audio import WavPlayer

"""
Plays a simple boop, boop, boop, beeep countdown sound effect when
you presss BOOT. Great for counting down to a race start.

Plug a red LED into port 1 and a green LED into port 2.
"""

tiny = TinyFX()
wav = WavPlayer(0, tiny.I2S_BCLK, tiny.I2S_LRCLK, tiny.I2S_DATA, tiny.AMP_EN_PIN)

tones = [440, 440, 440, 880, 0]
durations = [0.5, 0.5, 0.5, 1.5, 2.0]
leds = [1, 1, 1, 2, 0]

n = 0

try:
    while True:
        while not tiny.boot_pressed():
            pass

        for n in range(len(tones)):
            tone = tones[n]
            duration = durations[n]
            led = leds[n]
            if tone:
                wav.play_tone(tone, 1.0, wav.TONE_SQUARE)

            tiny.clear()
            if led:
                tiny.outputs[led - 1].on()

            time.sleep(duration)
            wav.stop()

            if tone:
                time.sleep(0.1)

finally:
    tiny.clear()
    wav.deinit()
