import time
from tiny_fx import TinyFX
from audio import WavPlayer

"""
An evocative musical melody with accompanying lights.

Any resemblance to music you might have heard elsewhere is
purely coincidental.
"""

tiny = TinyFX()
wav = WavPlayer(0, tiny.I2S_BCLK, tiny.I2S_LRCLK, tiny.I2S_DATA, tiny.AMP_EN_PIN)

tones = [588, 658, 524, 262, 384, 0]
durations = [0.6, 0.6, 0.6, 0.6, 0.6 * 4, 2.0]
leds = [2, 3, 1, 6, 4, 0]

n = 0

try:
    while not tiny.boot_pressed():
        tone = tones[n]
        duration = durations[n]
        led = leds[n]
        if tone:
            wav.play_tone(tone, 1.0)
        tiny.clear()
        if led:
            tiny.outputs[led - 1].on()
        time.sleep(duration)
        wav.stop()
        time.sleep(0.1)
        n += 1
        n %= len(tones)

finally:
    tiny.clear()
    wav.deinit()
