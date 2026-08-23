# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import time

from audio import WavPlayer
from machine import ADC, Pin
from pimoroni_i2c import PimoroniI2C

from picofx import PWMLED, RGBLED


class TinyFX:
    OUT_PINS = (3, 2, 4, 5, 8, 9)
    RGB_PINS = (13, 14, 15)

    I2C_SDA_PIN = 16
    I2C_SCL_PIN = 17

    I2S_DATA_PIN = 18
    I2S_BCLK_PIN = 19
    I2S_LRCLK_PIN = 20
    AMP_EN_PIN = 21

    USER_SW_PIN = 22

    # How long after a press its own contact bounce is ignored for
    BOOT_DEBOUNCE_MS = 40

    SENSOR_PIN = 26
    V_SENSE_PIN = 28

    V_SENSE_GAIN = 2
    V_SENSE_DIODE_CORRECTION = 0.3

    OUTPUT_GAMMA = 2.8
    RGB_GAMMA = 2.2

    def __init__(self, init_i2c=True, i2c_freq=100000, init_wav=True, wav_root="/"):
        # Set up the mono and RGB LED outputs
        self.outputs = [PWMLED(out, gamma=self.OUTPUT_GAMMA) for out in self.OUT_PINS]
        self.rgb = RGBLED(*self.RGB_PINS, invert=False, gamma=self.RGB_GAMMA)

        # Set up the i2c for Qw/st, if the user wants
        if init_i2c:
            self.i2c = PimoroniI2C(self.I2C_SDA_PIN, self.I2C_SCL_PIN, i2c_freq)

        # Set up the user switch. A press is caught by interrupt as well as read as
        # a level, so a tap inside a long frame is not missed by a program that only
        # looks between them
        self.__switch = Pin(self.USER_SW_PIN, Pin.IN, Pin.PULL_UP)
        self.__taps = 0
        self.__tapped_at = 0
        self.__switch.irq(trigger=Pin.IRQ_FALLING, handler=self.__switch_pressed)

        # Set up the internal voltage sensor
        self.__v_sense = ADC(Pin(self.V_SENSE_PIN))

        # Set up the wav (and tone) player, if the user wants
        self.wav = None
        if init_wav:
            self.wav = WavPlayer(0, self.I2S_BCLK_PIN, self.I2S_LRCLK_PIN, self.I2S_DATA_PIN, self.AMP_EN_PIN, root=wav_root)

    def boot_pressed(self):
        return self.__switch.value() == 0

    def boot_taps(self):
        """
        How many times the button has been pressed since this was last asked, the
        presses taken as they are read. Caught by interrupt, so a tap that begins
        and ends inside one long frame still counts where boot_pressed() would
        miss it, and two inside one are two rather than one.
        """
        taken = self.__taps
        self.__taps = 0
        return taken

    def __switch_pressed(self, _pin):
        # Contacts bounce, and each bounce is another falling edge. Anything inside
        # the window is the same press, which matters where a caller reads two
        # presses in a row as a double
        now = time.ticks_ms()
        if time.ticks_diff(now, self.__tapped_at) > self.BOOT_DEBOUNCE_MS:
            self.__tapped_at = now
            self.__taps += 1

    def read_voltage(self, samples=1):
        val = 0
        for _ in range(samples):
            val += self.__v_sense.read_u16()
        val /= samples

        return ((val * 3.3 * self.V_SENSE_GAIN) / 65535) + self.V_SENSE_DIODE_CORRECTION

    @property
    def one(self):
        return self.outputs[0]

    @property
    def two(self):
        return self.outputs[1]

    @property
    def three(self):
        return self.outputs[2]

    @property
    def four(self):
        return self.outputs[3]

    @property
    def five(self):
        return self.outputs[4]

    @property
    def six(self):
        return self.outputs[5]

    def clear(self):
        for out in self.outputs:
            out.off()

        self.rgb.off()

    def shutdown(self):
        self.clear()
        if self.wav:
            self.wav.deinit()
