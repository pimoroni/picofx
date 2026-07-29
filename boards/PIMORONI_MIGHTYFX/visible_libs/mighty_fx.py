# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from machine import ADC, Pin
from pimoroni_i2c import PimoroniI2C
from motor import Motor
from picofx import RGBLED
from audio import WavPlayer
from spidisplay import SPIDisplay
from st7789 import ST7789
from collections import namedtuple


class SPCE:
    SCREEN_154 = 0
    SCREEN_280 = 1
    MOTOR_DRIVER = 2


# baud is what the PL022 can actually reach: it divides clk_peri by an even
# prescale, so 24 MHz is the ceiling while MicroPython leaves clk_peri at 48 MHz.
# bands is destination rows per DMA band, capped at 16 by the band buffers; 16
# keeps the DMA fed across a column cache refresh, which one-row bands cannot.
# columns is the column cache width for 90/270 rotation, and spi_bits is the SPI
# data frame width for the pixel stream.
#
# fps sets the panel's own refresh, and raising it tightens the tearing margin:
# a frame must reach the bottom before the next scan does, which bounds fps to
# about 42 on the 280 and 55 on the 154 at 24 MHz. See DUAL_DISPLAY_STATUS.md.
ScreenDef = namedtuple("ScreenDef", ("baud", "bits", "fps", "bands", "width", "height",
                                     "columns", "spi_bits"))
screen_defs = {
    SPCE.SCREEN_154: ScreenDef(24_000_000, 12, 48, 16, 240, 240, 16, 16),
    SPCE.SCREEN_280: ScreenDef(24_000_000, 12, 42, 16, 240, 320, 16, 16),
}


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

    def __init__(self, spce_a=None, spce_b=None, init_i2c=True, init_wav=True, wav_root="/", sdef_a=None, sdef_b=None):
        # Set up the mono and RGB LED outputs
        self.outputs = [RGBLED(*out, invert=False, gamma=self.RGB_GAMMA) for out in self.OUT_PINS]

        self.screen_a = None
        self.motors_a = None
        if spce_a in [SPCE.SCREEN_154, SPCE.SCREEN_280]:
            sdef = screen_defs[spce_a] if sdef_a is None else sdef_a
            self.bl_a = Pin.board.SPCE_A_BL

            disp_a = SPIDisplay(spi=0, sck=self.SPCE_A_SCK_PIN, mosi=self.SPCE_A_MOSI_PIN,
                                cs=self.SPCE_A_CS_PIN, dc=self.SPCE_A_DC_PIN, baudrate=sdef.baud,
                                bitdepth=sdef.bits, band_lines=sdef.bands, cache_columns=sdef.columns,
                                spi_frame_bits=sdef.spi_bits)
            self.screen_a = ST7789(disp_a, self.bl_a, sdef.width, sdef.height, sdef.bits, sdef.fps)
            # Need to add some handling for LED conflicts

        elif spce_a == SPCE.MOTOR_DRIVER:
            MOTOR_A_PINS = [(self.SPCE_A_DC_PIN, self.SPCE_A_CS_PIN), \
                            (self.SPCE_A_SCK_PIN, self.SPCE_A_MOSI_PIN)]
            self.motors_a = [Motor(pins) for pins in MOTOR_A_PINS]
            self.motors_a_en = Pin(self.SPCE_A_BL_PIN, Pin.OUT, value=True)
            # Need to add some better handling for LED conflicts, to avoid output LEDs lighting
            _ = Pin(40, Pin.IN)
            _ = Pin(41, Pin.IN)
            _ = Pin(42, Pin.IN)

        self.screen_b = None
        self.motors_b = None
        if spce_b in [SPCE.SCREEN_154, SPCE.SCREEN_280]:
            sdef = screen_defs[spce_b] if sdef_b is None else sdef_b
            self.bl_b = Pin.board.SPCE_B_BL

            disp_b = SPIDisplay(spi=1, sck=self.SPCE_B_SCK_PIN, mosi=self.SPCE_B_MOSI_PIN,
                                cs=self.SPCE_B_CS_PIN, dc=self.SPCE_B_DC_PIN, baudrate=sdef.baud,
                                bitdepth=sdef.bits, band_lines=sdef.bands, cache_columns=sdef.columns,
                                spi_frame_bits=sdef.spi_bits)
            self.screen_b = ST7789(disp_b, self.bl_b, sdef.width, sdef.height, sdef.bits, sdef.fps)
            # Need to add some handling for LED conflicts

        elif spce_b == SPCE.MOTOR_DRIVER:
            MOTOR_B_PINS = [(self.SPCE_B_DC_PIN, self.SPCE_B_CS_PIN), \
                            (self.SPCE_B_SCK_PIN, self.SPCE_B_MOSI_PIN)]
            self.motors_b = [Motor(pins) for pins in MOTOR_B_PINS]
            self.motors_b_en = Pin(self.SPCE_B_BL_PIN, Pin.OUT, value=True)
            # Need to add some better handling for LED conflicts, to avoid output LEDs lighting
            _ = Pin(8, Pin.IN)
            _ = Pin(9, Pin.IN)
            _ = Pin(10, Pin.IN)
            _ = Pin(11, Pin.IN)

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

        if self.screen_a:
            self.bl_a.off()

        if self.screen_b:
            self.bl_b.off()

        if self.motors_a:
            self.motors_a_en.off()
            for motor in self.motors_a:
                motor.disable()

        if self.motors_b:
            self.motors_b_en.off()
            for motor in self.motors_b:
                motor.disable()

        self.wav.deinit()
