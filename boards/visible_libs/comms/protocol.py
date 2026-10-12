import struct
from machine import I2CTarget, disable_irq, enable_irq
from picofx import PseudoLED, RGBLED

# Register Constants. The device ID says which board is answering
DEVICE_TINY_FX = 0x2f
DEVICE_MIGHTY_FX = 0x30
VERSION = 0x01


# Host Side (transmission). A board of the kind named by DEVICE_ID, reached over I2C
class FXControl:
    DEVICE_ID = None
    NAME = ""

    def __init__(self, i2c, address, channels, debug=True):
        try:
            device, version = i2c.readfrom_mem(address, 0, 2)
        except OSError:
            raise RuntimeError(f"No {self.NAME} found at I2C address {hex(address)}") from None

        if device != self.DEVICE_ID:
            raise RuntimeError(f"I2C device found at address {hex(address)} is not a {self.NAME}") from None

        if debug:
            print(f"{self.NAME} found at I2C address {hex(address)}")

        if version != VERSION:
            raise RuntimeError(f"{self.NAME} not running matching version of I2C code. Expected {VERSION}, found {version}")

        # The order the target applies them in
        self.__leds = channels

        self.__buf = bytearray(4 * len(channels))
        self.__i2c = i2c
        self.__addr = address
        self.__paired = None    # The end of an EffectPlayer's chain, which start() walks

        self.__tick()

    def clear(self):
        for led in self.__leds:
            led.off()

        self.__tick()

    def shutdown(self):
        self.clear()

    # Called by the EffectPlayer this is paired with, after its effects have updated
    def __tick(self, _=None):
        for index, led in enumerate(self.__leds):
            struct.pack_into("f", self.__buf, index * 4, led.__brightness)
        try:
            self.__i2c.writeto_mem(self.__addr, 2, self.__buf)
        except OSError:
            pass


class TinyFXControl(FXControl):
    DEVICE_ID = DEVICE_TINY_FX
    NAME = "Tiny FX"

    def __init__(self, i2c, address, debug=True):
        self.outputs = [PseudoLED() for _ in range(6)]
        self.rgb = RGBLED(PseudoLED(), PseudoLED(), PseudoLED())

        # Six outputs, then the RGB's three channels
        super().__init__(i2c, address,
                         self.outputs + [self.rgb.led_r, self.rgb.led_g, self.rgb.led_b],
                         debug)

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


class MightyFXControl(FXControl):
    DEVICE_ID = DEVICE_MIGHTY_FX
    NAME = "Mighty FX"

    def __init__(self, i2c, address, debug=True):
        # Seven RGB outputs, the same shape the board itself offers, and their 21 channels
        self.outputs = [RGBLED(PseudoLED(), PseudoLED(), PseudoLED()) for _ in range(7)]
        self.monos = [led for output in self.outputs for led in output.leds]

        super().__init__(i2c, address, self.monos, debug)

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


# Device Side (receive). The board offering itself up to whoever is driving the bus
class FXTarget:
    DEVICE_ID = None

    def __init__(self, board, address, channels):
        # The order a control sends them in
        self.__leds = channels

        # Create a byte array for the I2C memory
        size = struct.calcsize("bb")
        for _ in range(len(self.__leds)):
            size += struct.calcsize("f")
        self.__mem = bytearray(size)

        # A write is copied out whole as it ends, and the board's loop takes its own copy of
        # that, so neither reads a frame the next write has started to overwrite
        self.__received = bytearray(size)
        self.__frame = bytearray(size)

        # Initialise the read-only registers. The ID is held on the instance, which the
        # interrupt reads faster than the class
        self.__device_id = self.DEVICE_ID
        self.__mem[0] = self.__device_id
        self.__mem[1] = VERSION

        # Set up the I2C for receiving commands
        self.__i2c = I2CTarget(addr=address, mem=self.__mem, sda=board.I2C_SDA_PIN, scl=board.I2C_SCL_PIN)
        self.__changed = False

        self.__i2c.irq(self.__i2c_handler, hard=True)     # Hard needed to reset read-only memory addresses quickly

    def __i2c_handler(self, i2c_target):
        flags = i2c_target.irq().flags()
        if flags & I2CTarget.IRQ_END_WRITE:
            # Reload all read-only registers
            self.__mem[0] = self.__device_id
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
