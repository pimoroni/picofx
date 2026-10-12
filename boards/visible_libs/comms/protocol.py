import struct
from picofx import PseudoLED, RGBLED

# Register Constants. The device ID says which board is answering
DEVICE_TINY_FX = 0x2f
DEVICE_MIGHTY_FX = 0x30
VERSION = 0x01


# Host Side (transmission). A Tiny FX reached over I2C, from any board
class TinyFXControl:
    def __init__(self, i2c, address, debug=True):
        try:
            device, version = i2c.readfrom_mem(address, 0, 2)
        except OSError:
            raise RuntimeError(f"No Tiny FX found at I2C address {hex(address)}") from None

        if device != DEVICE_TINY_FX:
            raise RuntimeError(f"I2C device found at address {hex(address)} is not a Tiny FX") from None

        if debug:
            print(f"Tiny FX found at I2C address {hex(address)}")

        if version != VERSION:
            raise RuntimeError(f"Tiny FX not running matching version of I2C code. Expected {VERSION}, found {version}")

        self.outputs = [PseudoLED() for _ in range(6)]
        self.rgb = RGBLED(PseudoLED(), PseudoLED(), PseudoLED())

        self.__buf = bytearray(4 * 9)
        self.__i2c = i2c
        self.__addr = address
        self.__paired = None    # The end of an EffectPlayer's chain, which start() walks

        self.__tick()

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

        self.__tick()

    def shutdown(self):
        self.clear()

    # Called by the EffectPlayer this is paired with, after its effects have updated
    def __tick(self, _=None):
        struct.pack_into("f" * 9, self.__buf, 0,
                         self.outputs[0].__brightness, \
                         self.outputs[1].__brightness, \
                         self.outputs[2].__brightness, \
                         self.outputs[3].__brightness, \
                         self.outputs[4].__brightness, \
                         self.outputs[5].__brightness, \
                         self.rgb.led_r.__brightness, \
                         self.rgb.led_g.__brightness, \
                         self.rgb.led_b.__brightness)
        try:
            self.__i2c.writeto_mem(self.__addr, 2, self.__buf)
        except OSError:
            pass


# Host Side (transmission). A MightyFX reached over I2C, from any board
class MightyFXControl:
    def __init__(self, i2c, address, debug=True):
        try:
            device, version = i2c.readfrom_mem(address, 0, 2)
        except OSError:
            raise RuntimeError(f"No Mighty FX found at I2C address {hex(address)}") from None

        if device != DEVICE_MIGHTY_FX:
            raise RuntimeError(f"I2C device found at address {hex(address)} is not a Mighty FX") from None

        if debug:
            print(f"Mighty FX found at I2C address {hex(address)}")

        if version != VERSION:
            raise RuntimeError(f"Mighty FX not running matching version of I2C code. Expected {VERSION}, found {version}")

        self.outputs = [RGBLED(PseudoLED(), PseudoLED(), PseudoLED()) for _ in range(7)]
        self.monos = [led for output in self.outputs for led in output.leds]

        self.__buf = bytearray(4 * len(self.monos))
        self.__i2c = i2c
        self.__addr = address
        self.__paired = None    # The end of an EffectPlayer's chain, which start() walks

        self.__tick()

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
            out.off()

        self.__tick()

    def shutdown(self):
        self.clear()

    # Called by the EffectPlayer this is paired with, after its effects have updated
    def __tick(self, _=None):
        for index, led in enumerate(self.monos):
            struct.pack_into("f", self.__buf, index * 4, led.__brightness)
        try:
            self.__i2c.writeto_mem(self.__addr, 2, self.__buf)
        except OSError:
            pass
