import time
from tiny_fx import TinyFX
from audio import WavPlayer
from machine import I2C
from breakout_msa301 import BreakoutMSA301

"""
Absolutely definitely not a l&%t s&^@*r.

Don't forget to copy the `photon_sword` directory.

Grab yourself an MSA301 and attach it to the Qw/St connector.

Press boot to power up, swing to make do sounds! SWOOSH SWOOOOSH!!!
"""

TRIGGER_DELTA = 1.0

tiny = TinyFX()
wav = WavPlayer(0, tiny.I2S_BCLK, tiny.I2S_LRCLK, tiny.I2S_DATA, tiny.AMP_EN_PIN, root="/photon_sword")

i2c = I2C(0, sda=tiny.I2C_SDA_PIN, scl=tiny.I2C_SCL_PIN)

msa = BreakoutMSA301(i2c)

msa.enable_interrupts(BreakoutMSA301.FREEFALL | BreakoutMSA301.ORIENTATION)

last_axes = None

try:
    while not tiny.boot_pressed():
        pass
    wav.play_wav("ps-start.wav")
    while wav.is_playing():
        pass
    while True:
        if not wav.is_playing():
            wav.play_wav("ps-idle.wav", True)
        this_axes = msa.get_x_axis(), msa.get_y_axis(), msa.get_z_axis()
        if last_axes is not None:
            deltas = [abs(this_axes[n] - last_axes[n]) for n in range(3)]
            delta = max(deltas)
            if delta > TRIGGER_DELTA:
                swing = deltas.index(delta) + 1
                file = f"ps-swing{swing}.wav"
                wav.play_wav(file)
                print(file)
        last_axes = this_axes
        time.sleep(0.05)

finally:
    wav.deinit()
