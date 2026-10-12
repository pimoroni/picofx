import struct
from machine import I2CTarget
from comms.protocol import DEVICE_TINY_FX, VERSION

# Imported so a board driving the bus finds it beside the target
from comms.protocol import MightyFXControl, TinyFXControl  # noqa: F401


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
        self.__mem[0] = DEVICE_TINY_FX
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
            self.__mem[0] = DEVICE_TINY_FX
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
