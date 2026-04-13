# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from machine import ADC, Pin
from pimoroni_i2c import PimoroniI2C
from picofx import RGBLED
from audio import WavPlayer


class MightyFX:
    OUT_PINS = (
        (3, 0, 1),
        (4, 5, 2),
        (9, 6, 7),
        (10, 11, 8),
        (15, 12, 13),
        (38, 39, 14),
        (42, 40, 41),
    )

    I2C_SDA_PIN = 16
    I2C_SCL_PIN = 17

    USER_SW_PIN = 18

    I2S_DATA_PIN = 20
    I2S_BCLK_PIN = 21
    I2S_LRCLK_PIN = 22
    AMP_EN_PIN = 23

    SPCE_A_DC_PIN = 32
    SPCE_A_CS_PIN = 33
    SPCE_A_SCK_PIN = 34
    SPCE_A_MOSI_PIN = 35
    SPCE_A_BL_PIN = 36

    SPCE_B_DC_PIN = 24
    SPCE_B_CS_PIN = 25
    SPCE_B_SCK_PIN = 26
    SPCE_B_MOSI_PIN = 27
    SPCE_B_BL_PIN = 37

    SERVO_STRIP_EN = 43
    SERVO_STRIP_A = 44
    SERVO_STRIP_B = 45

    SENSOR_PIN = 46
    V_SENSE_PIN = 47

    V_SENSE_GAIN = 2
    V_SENSE_DIODE_CORRECTION = 0.3

    RGB_GAMMA = 2.2

    def __init__(self, init_i2c=True, init_wav=True, wav_root="/"):
        # Set up the mono and RGB LED outputs
        self.outputs = [RGBLED(*out, invert=False, gamma=self.RGB_GAMMA) for out in self.OUT_PINS]

        # Set up the i2c for Qw/st, if the user wants
        if init_i2c:
            self.i2c = PimoroniI2C(self.I2C_SDA_PIN, self.I2C_SCL_PIN, 100000)

        # Set up the user switch
        self.__switch = Pin(self.USER_SW_PIN, Pin.IN, Pin.PULL_UP)

        # Set up the internal voltage sensor
        self.__v_sense = ADC(Pin(self.V_SENSE_PIN))

        # Set up the wav (and tone) player, if the user wants
        if init_wav:
            self.wav = WavPlayer(0, self.I2S_BCLK_PIN, self.I2S_LRCLK_PIN, self.I2S_DATA_PIN, self.AMP_EN_PIN, root=wav_root)

        # Set up the user switch
        self.__servo_strip_en = Pin(self.SERVO_STRIP_EN, Pin.OUT, value=False)

    def boot_pressed(self):
        return self.__switch.value() == 0

    def enable_servo_strip(self):
        self.__servo_strip_en.on()

    def disable_servo_strips(self):
        self.__servo_strip_en.off()

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

    @property
    def seven(self):
        return self.outputs[6]

    def clear(self):
        for out in self.outputs:
            out.set_rgb(0, 0, 0)

    def shutdown(self):
        self.clear()
        self.disable_servo_strips()
        self.wav.deinit()
