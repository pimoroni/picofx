import struct
from machine import I2CTarget
from picofx import PseudoLED, RGBLED

# Register Constants
DEVICE_ID = 0x2f    # Tiny FX
VERSION = 0x01


# Host Side (transmission)
class TinyFXControl:
    def __init__(self, i2c, address, debug=True):
        try:
            device, version = i2c.readfrom_mem(address, 0, 2)
        except OSError:
            raise RuntimeError(f"No Tiny FX found at I2C address {hex(address)}") from None

        if device != DEVICE_ID:
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

        self.__update()

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

        self.rgb.set_rgb(0, 0, 0)

        self.__update()

    def shutdown(self):
        self.clear()

    def __update(self, _=None):
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

# Device Side (receive)
class TinyFXTarget:
    def __init__(self, tiny_fx, address):
        # Create a unified list of LEDs to control
        self.__leds = tiny_fx.outputs + [tiny_fx.rgb.led_r, tiny_fx.rgb.led_g, tiny_fx.rgb.led_b]

        # Create a byte array for the I2C memory
        size = struct.calcsize("bb")
        for _ in range(len(self.__leds)):
            size += struct.calcsize("f")
        self.__mem = bytearray(size)

        # Initialise the read-only registers
        self.__mem[0] = DEVICE_ID
        self.__mem[1] = VERSION

        # Set up the I2C for receiving commands
        self.__i2c = I2CTarget(addr=address, mem=self.__mem, sda=tiny_fx.I2C_SDA_PIN, scl=tiny_fx.I2C_SCL_PIN)
        self.__changed = False

        self.__i2c.irq(self.__i2c_handler, hard=True)     # Hard needed to reset read-only memory addresses quickly

    def __i2c_handler(self, i2c_target):
        flags = i2c_target.irq().flags()
        if flags & I2CTarget.IRQ_END_WRITE:
            self.__changed = True

            # Reload all read-only registers
            self.__mem[0] = DEVICE_ID
            self.__mem[1] = VERSION

    def process_i2c(self):
        # Check if the buffer has changed
        if self.__changed:
            self.__changed = False     # Immediately clear the flag to reduce race conditions

            # Update the LED brightnesses
            num_leds = len(self.__leds)
            brightnesses = struct.unpack_from("f" * num_leds, self.__mem, 2)
            for led in range(num_leds):
                self.__leds[led].brightness(brightnesses[led])

    def deinit(self):
        self.__i2c.deinit()
