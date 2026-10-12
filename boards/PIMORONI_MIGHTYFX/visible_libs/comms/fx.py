import struct
from machine import I2CTarget, disable_irq, enable_irq
from comms.protocol import DEVICE_MIGHTY_FX, VERSION

# Imported so a board driving the bus finds them beside the target
from comms.protocol import MightyFXControl, TinyFXControl  # noqa: F401


# Device Side (receive)
class MightyFXTarget:
    def __init__(self, mighty_fx, address):
        # Every output's three channels, in the order a MightyFXControl sends them
        self.__leds = mighty_fx.monos

        # Create a byte array for the I2C memory
        size = struct.calcsize("bb")
        for _ in range(len(self.__leds)):
            size += struct.calcsize("f")
        self.__mem = bytearray(size)

        # A write is copied out whole as it ends, and the board's loop takes its own copy of
        # that, so neither reads a frame the next write has started to overwrite
        self.__received = bytearray(size)
        self.__frame = bytearray(size)

        # Initialise the read-only registers
        self.__mem[0] = DEVICE_MIGHTY_FX
        self.__mem[1] = VERSION

        # Set up the I2C for receiving commands
        self.__i2c = I2CTarget(addr=address, mem=self.__mem, sda=mighty_fx.I2C_SDA_PIN, scl=mighty_fx.I2C_SCL_PIN)
        self.__changed = False

        self.__i2c.irq(self.__i2c_handler, hard=True)     # Hard needed to reset read-only memory addresses quickly

    def __i2c_handler(self, i2c_target):
        flags = i2c_target.irq().flags()
        if flags & I2CTarget.IRQ_END_WRITE:
            # Reload all read-only registers
            self.__mem[0] = DEVICE_MIGHTY_FX
            self.__mem[1] = VERSION

            # The slice is built on the stack for a bytearray, so the copy does not allocate
            self.__received[:] = self.__mem
            self.__changed = True

    def process_i2c(self):
        # Check if the buffer has changed
        if self.__changed:
            # Interrupts are held off only for the copy, so the next write cannot land part way through it
            state = disable_irq()
            self.__frame[:] = self.__received
            self.__changed = False
            enable_irq(state)

            # Update the LED brightnesses
            num_leds = len(self.__leds)
            brightnesses = struct.unpack_from("f" * num_leds, self.__frame, 2)
            for led in range(num_leds):
                self.__leds[led].brightness(brightnesses[led])

    def deinit(self):
        self.__i2c.deinit()
