# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import time

from machine import ADC, PWM, Pin
from pimoroni_i2c import PimoroniI2C
from motor import Motor
from picofx import RGBLED, DisabledLED
from audio import WavPlayer
from spidisplay import SPIDisplayBus, release_buffers


# The RP2350 shares its 24 PWM channels between GPIO pairs: pins 16 apart below
# GPIO 32 and 8 apart above it drive the same channel, and both emit the same
# signal whenever both select PWM. Used to keep LED outputs off channels that
# an SP/CE role is driving.
def __pwm_channel(gpio):
    if gpio < 32:
        return gpio % 16
    return 16 + ((gpio - 32) % 8)


class SPCE:
    SCREEN = 0
    MOTOR_DRIVER = 1
    GPIO = 2


class Backlight:
    """A screen backlight on a PWM channel.

    Dark from power-on until every screen sharing it has shown a first frame, so no
    panel shows its power-on contents. After that brightness is the user's, from 0.0
    to 1.0 against perceived brightness rather than duty. Screens on one port share
    the line and so the setting.
    """

    FREQUENCY = 1000

    # Duty follows the setting raised to this, since perceived brightness goes as
    # roughly the cube root of light output. Chosen on the panel against 2.2 and 3.0.
    # The lowest settings are dark whatever this is, the driver having a floor that
    # varies between panels, so the bottom of the range is not worth reclaiming.
    GAMMA = 2.8

    def __init__(self, pin):
        self.__pwm = PWM(pin, freq=self.FREQUENCY, duty_u16=0)
        self.__brightness = 0.0
        self.__screens = []
        self.__drawn = set()
        self.__lit = False

    def __register(self, screen):
        self.__screens.append(screen)

    def __first_frame(self, screen):
        """Note a screen's first frame, coming on once every screen has shown one."""
        if self.__lit:
            return

        self.__drawn.add(screen)
        if len(self.__drawn) >= len(self.__screens):
            # A finished transfer is not a presented frame: each row keeps what the
            # scan last painted there, so the panel needs a full pass before the new
            # frame is everywhere. The slowest member sets the wait.
            slowest = min(member.framerate for member in self.__screens)
            time.sleep_ms(1000 // slowest + 3)
            self.brightness = 1.0

    @property
    def brightness(self):
        return self.__brightness

    @brightness.setter
    def brightness(self, value):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{value} is not a valid brightness. Expected 0.0 to 1.0.")

        self.__brightness = value
        self.__lit = True
        self.__pwm.duty_u16(int(pow(value, self.GAMMA) * 65535 + 0.5))

    def off(self):
        self.__pwm.duty_u16(0)
        self.__brightness = 0.0


class SPCEPort:
    """One SP/CE connector: what it was declared as, the five GPIOs it carries, and
    for a screen port the SPI bus and backlight its screens share.

    A screen port hands out its own DC, CS and BL lines through the named
    properties. A port declared SPCE.GPIO hands out all five through io instead, to
    serve as further screens' CS and DC lines, or a multiplexer's select lines.
    """

    # The connector's GPIOs, in the order io reports them
    IO_NAMES = ("dc", "cs", "sck", "mosi", "bl")

    def __init__(self, name, mode, spi, pins):
        if mode not in (None, SPCE.SCREEN, SPCE.MOTOR_DRIVER, SPCE.GPIO):
            raise ValueError(f"{mode} is not a valid SP/CE mode. Expected SPCE.SCREEN, SPCE.MOTOR_DRIVER, SPCE.GPIO, or None.")

        self.name = name
        self.mode = mode

        # A motor port's pins belong to its Motor objects, and an undeclared port is
        # left alone, so neither offers them up
        self.__pins = tuple(Pin(pin) for pin in pins) if mode in (SPCE.SCREEN, SPCE.GPIO) else None

        self.__bus = SPIDisplayBus(spi=spi, sck=self.__pins[2], mosi=self.__pins[3]) if mode == SPCE.SCREEN else None
        self.__backlight = None
        self.__selector = None
        self.__screens = []
        self.__cs_claimed = []
        self.__dc_claimed = []

    @property
    def io(self):
        """The connector's five GPIOs, in the order DC, CS, SCK, MOSI, BL.

        Only a port declared SPCE.GPIO offers them, so spending a connector on pins
        is visible in the call that declared it.
        """
        if self.mode != SPCE.GPIO:
            raise ValueError(f"SP/CE {self.name} is not declared SPCE.GPIO, so its pins are not free to borrow")

        return self.__pins

    def __line(self, index):
        if self.mode != SPCE.SCREEN:
            raise ValueError(f"SP/CE {self.name} is not a screen port, so it has no {self.IO_NAMES[index]} line")

        return self.__pins[index]

    @property
    def dc(self):
        return self.__line(0)

    @property
    def cs(self):
        return self.__line(1)

    @property
    def sck(self):
        return self.__line(2)

    @property
    def mosi(self):
        return self.__line(3)

    @property
    def bl(self):
        return self.__line(4)

    @property
    def bus(self):
        """The SPIDisplayBus every screen on this port streams over."""
        if self.__bus is None:
            raise ValueError(f"SP/CE {self.name} is not a screen port, so it has no display bus")

        return self.__bus

    @property
    def screens(self):
        return tuple(self.__screens)

    @property
    def selector(self):
        """The port's ScreenMux, if its screens are addressed by index."""
        return self.__selector

    @selector.setter
    def selector(self, value):
        if self.mode != SPCE.SCREEN:
            raise ValueError(f"SP/CE {self.name} is not a screen port, so it cannot have a selector")

        if self.__screens:
            raise ValueError(f"SP/CE {self.name} already has screens, and a selector changes how they are addressed, so set it first")

        self.__selector = value

    # Construction-time bookkeeping, reached from screens.py as a screen is built. Not
    # for a user to call: each records a claim the port validates later ones against,
    # so a spurious call reserves a line, a channel or a first frame for no screen.
    def __register(self, screen):
        self.__screens.append(screen)

    def __next_index(self):
        """The next selector channel, handed out in screen creation order."""
        index = len(self.__screens)
        if index >= self.__selector.count:
            raise ValueError(f"SP/CE {self.name}'s selector has {self.__selector.count} channels, and all of them are taken")

        return index

    def __claim_cs(self, pin=None):
        """Register a screen's CS line and return it.

        None takes the port's own, which is the first screen's to have. Every further
        screen needs its own, since CS is the only signal selecting one panel, unless
        a selector switches the port's single line between them.
        """
        switched = self.__selector is not None
        if pin is None:
            pin = self.cs

        if not switched and pin in self.__cs_claimed:
            raise ValueError(f"SP/CE {self.name} already has a screen on {pin}. Every further screen on a port needs a cs of its own.")

        self.__cs_claimed.append(pin)
        return pin

    def __claim_dc(self, pin=None, te=True):
        """Register a screen's DC line and return it.

        None takes the port's own, which is the first screen's to have. Pass this
        port's dc to share that line deliberately, which panels using TE may not do:
        TE travels back along DC through a series resistor on each breakout, so
        panels sharing the line divide it and no asserted level survives.
        """
        switched = self.__selector is not None
        if pin is None:
            pin = self.dc
            if not switched and any(claimed is pin for claimed, _ in self.__dc_claimed):
                raise ValueError(f"SP/CE {self.name}'s own DC line is taken. Give this screen a dc, or pass the port's dc to share that line.")

        if not switched:
            for claimed, claimed_te in self.__dc_claimed:
                if claimed is pin and (te or claimed_te):
                    raise ValueError(f"{pin} is carrying TE for another screen. Screens sharing a DC line all need te=False.")

        self.__dc_claimed.append((pin, te))
        return pin

    def __claim_backlight(self):
        """The port's backlight, created for the first screen to ask for it.

        The connector carries one BL line, so every screen taking it shares the
        setting. If no screen claims it the pin is left alone, free to be a CS or DC.
        """
        if self.__backlight is None:
            self.__backlight = Backlight(self.bl)

        return self.__backlight

    def backlight_off(self):
        if self.__backlight is not None:
            self.__backlight.off()

    def release(self):
        """Hand back the bus's DMA channel and its screens' SRAM claims, which
        nothing else gives up early.

        There are 16 channels and the bus takes one until it is collected, so a
        program that builds screens repeatedly runs out and the SDK panics; each
        screen likewise holds its band and cache SRAM until collected, and the GC
        heap is PSRAM so collection rarely comes. Screens on this port stop
        working, reporting rather than transferring, and a second call does
        nothing. Canvases outlive this, since the other port's screens may still be
        drawing to them; shutdown() is what gives them back.
        """
        for screen in self.__screens:
            screen.display.__del__()
        self.__screens.clear()

        if self.__bus is not None:
            self.__bus.__del__()

    def broadcast(self, *screens):
        """A group driving several of this port's screens with one frame."""
        if len(screens) < 2:
            raise ValueError("a broadcast group needs at least two screens")

        for screen in screens:
            if screen.port is not self:
                raise ValueError(f"that screen is not on SP/CE {self.name}, and two ports are two streams")

        return screens[0].group_with(*screens[1:])


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

    SPCE_A_PINS = (SPCE_A_DC_PIN, SPCE_A_CS_PIN, SPCE_A_SCK_PIN, SPCE_A_MOSI_PIN, SPCE_A_BL_PIN)
    SPCE_B_PINS = (SPCE_B_DC_PIN, SPCE_B_CS_PIN, SPCE_B_SCK_PIN, SPCE_B_MOSI_PIN, SPCE_B_BL_PIN)

    SERVO_STRIP_EN = 43
    SERVO_STRIP_A = 44
    SERVO_STRIP_B = 45

    SENSOR_PIN = 46
    V_SENSE_PIN = 47

    V_SENSE_GAIN = 2
    V_SENSE_DIODE_CORRECTION = 0.3

    RGB_GAMMA = 2.2

    RGB_COLOUR_NAMES = ("red", "green", "blue")

    def __init__(self, spce_a=None, spce_b=None, init_i2c=True, init_wav=True, wav_root="/"):
        # A motor role drives PWM on its DC, CS, SCK and MOSI lines, holding channels
        # some LED outputs share. BL becomes a plain enable output, so it claims nothing.
        claimed = {}
        for port_name, mode, pins in (("A", spce_a, self.SPCE_A_PINS), ("B", spce_b, self.SPCE_B_PINS)):
            if mode == SPCE.MOTOR_DRIVER:
                for pin in pins[:4]:
                    claimed[__pwm_channel(pin)] = (port_name, pin)

        # Set up the mono and RGB LED outputs, standing in a DisabledLED for any
        # channel a motor role holds, so lighting it reports instead of doing nothing
        self.outputs = []
        for index, rgb_pins in enumerate(self.OUT_PINS):
            leds = []
            for colour, pin in zip(self.RGB_COLOUR_NAMES, rgb_pins):
                holder = claimed.get(__pwm_channel(pin))
                if holder is None:
                    leds.append(pin)
                else:
                    port_name, motor_pin = holder
                    leds.append(DisabledLED(
                        f"Output {index + 1}'s {colour} LED cannot light. GPIO {pin} shares a PWM channel with GPIO {motor_pin}, which SP/CE {port_name} is using to drive motors."))
            self.outputs.append(RGBLED(*leds, invert=False, gamma=self.RGB_GAMMA))

        # Each port owns its bus and pins. Screens are the user's to create against
        # them, from the classes in screens.py
        self.spce_a = SPCEPort("A", spce_a, 0, self.SPCE_A_PINS)
        self.spce_b = SPCEPort("B", spce_b, 1, self.SPCE_B_PINS)

        self.motors_a = None
        if spce_a == SPCE.MOTOR_DRIVER:
            MOTOR_A_PINS = [(self.SPCE_A_DC_PIN, self.SPCE_A_CS_PIN), \
                            (self.SPCE_A_SCK_PIN, self.SPCE_A_MOSI_PIN)]
            self.motors_a = [Motor(pins) for pins in MOTOR_A_PINS]
            self.motors_a_en = Pin(self.SPCE_A_BL_PIN, Pin.OUT, value=True)

        self.motors_b = None
        if spce_b == SPCE.MOTOR_DRIVER:
            MOTOR_B_PINS = [(self.SPCE_B_DC_PIN, self.SPCE_B_CS_PIN), \
                            (self.SPCE_B_SCK_PIN, self.SPCE_B_MOSI_PIN)]
            self.motors_b = [Motor(pins) for pins in MOTOR_B_PINS]
            self.motors_b_en = Pin(self.SPCE_B_BL_PIN, Pin.OUT, value=True)

        # Set up the i2c for Qw/st, if the user wants
        if init_i2c:
            self.i2c = PimoroniI2C(self.I2C_SDA_PIN, self.I2C_SCL_PIN, 100000)

        # Set up the user switch
        self.__switch = Pin(self.USER_SW_PIN, Pin.IN, Pin.PULL_UP)

        # Set up the internal voltage sensor
        self.__v_sense = ADC(Pin(self.V_SENSE_PIN))

        # Set up the wav (and tone) player, if the user wants
        self.wav = None
        if init_wav:
            self.wav = WavPlayer(0, self.I2S_BCLK_PIN, self.I2S_LRCLK_PIN, self.I2S_DATA_PIN, self.AMP_EN_PIN, root=wav_root)

        # Set up the servo/strip enable
        self.__servo_strip_en = Pin(self.SERVO_STRIP_EN, Pin.OUT, value=False)

    def boot_pressed(self):
        return self.__switch.value() == 0

    def enable_servo_strips(self):
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

        self.spce_a.backlight_off()
        self.spce_b.backlight_off()

        # Give the DMA channels back rather than waiting for the GC, so a program
        # that builds screens repeatedly does not exhaust the 16 the chip has
        self.spce_a.release()
        self.spce_b.release()

        # Both ports are down, so no screen is drawing from a canvas any more and
        # the SRAM they claimed can go back. A rebuilt screen then gets the same
        # addresses instead of the region marching up.
        release_buffers()

        if self.motors_a:
            self.motors_a_en.off()
            for motor in self.motors_a:
                motor.disable()

        if self.motors_b:
            self.motors_b_en.off()
            for motor in self.motors_b:
                motor.disable()

        if self.wav:
            self.wav.deinit()
