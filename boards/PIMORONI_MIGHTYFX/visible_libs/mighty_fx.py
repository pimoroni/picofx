# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import gc

from machine import ADC, Pin
from pimoroni_i2c import PimoroniI2C
from motor import Motor
from picofx import RGBLED, DisabledLED
from audio import WavPlayer
from spidisplay import release_buffers
from spce import SPCE, SPCEPort


# The RP2350 shares its 24 PWM channels between GPIO pairs: pins 16 apart below
# GPIO 32 and 8 apart above it drive the same channel, and both emit the same
# signal whenever both select PWM. Used to keep LED outputs off channels that
# an SP/CE role is driving.
def __pwm_channel(gpio):
    if gpio < 32:
        return gpio % 16
    return 16 + ((gpio - 32) % 8)


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
    SERVO_STRIP_L = 44
    SERVO_STRIP_R = 45

    # A strip takes a state machine of its own, and they are taken from PIO 1 so the
    # I2S audio every board builds by default keeps PIO 0 to itself
    STRIP_PIO = 1

    SENSOR_PIN = 46
    V_SENSE_PIN = 47

    V_SENSE_GAIN = 2
    V_SENSE_DIODE_CORRECTION = 0.3

    RGB_GAMMA = 2.2

    RGB_COLOUR_NAMES = ("red", "green", "blue")

    # A hub reaches the screen port's own chip select and the other connector's five,
    # and each of those six is named on the board as well as indexed on the hub
    HUB_PORT_NAMES = ("a", "b", "c", "d", "e", "f")

    def __init__(self, spce_a=None, spce_b=None, strip_l=None, strip_r=None,
                 servo_l=None, servo_r=None, init_i2c=True, init_wav=True, wav_root="/"):
        # A canvas claim has no object to finalise it, so one outlives the program
        # that made it where a screen's own workspace does not: a soft reset after a
        # run that skipped shutdown() leaves the SRAM held and the next program short
        # of it. Nothing of this program holds any yet, so anything outstanding here
        # belongs to the last one.
        release_buffers()

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

        # Every output's three channels in one list, since each drives on its own: a mono LED
        # in the right end of an output connector reaches that output's red channel, and the
        # adapter pack brings all three out
        self.monos = [led for output in self.outputs for led in output.leds]

        # Each port owns its bus and pins. Screens are the user's to create against
        # them, from the classes in screens.py
        self.spce_a = SPCEPort("A", spce_a, 0, self.SPCE_A_PINS)
        self.spce_b = SPCEPort("B", spce_b, 1, self.SPCE_B_PINS)

        # One connector given over to chip selects makes the other's panels several
        # rather than one, so the pairing is checked here and the hub built for the
        # user. Imported only where a board asked for one, a program with no screens
        # having no reason to load the package.
        self.hub = None
        for screen_port, lines_port in ((self.spce_a, self.spce_b), (self.spce_b, self.spce_a)):
            if lines_port.mode != SPCE.HUB_LINES:
                continue

            if screen_port.mode != SPCE.SCREEN:
                raise ValueError(f"SP/CE {lines_port.name} is declared SPCE.HUB_LINES, which are the chip selects for panels on the other connector, so declare SP/CE {screen_port.name} as SPCE.SCREEN")

            from screens import ScreenHub
            self.hub = ScreenHub(screen_port, extra_cs=lines_port.hub_lines)
            for name, port in zip(self.HUB_PORT_NAMES, self.hub.ports):
                setattr(self, f"hub_{name}", port)

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

        # Set up the enable for the rail the L and R connectors share
        self.__rail_en = Pin(self.SERVO_STRIP_EN, Pin.OUT, value=False)

        # What each of those connectors was declared as. A strip carries its length
        # and a servo its calibration, so one setting says both which role and what
        # it needs. Anything else is left alone: no pin claimed and no object made,
        # so the connector is the caller's to use as they like.
        self.__strips = {}
        self.__servos = {}
        for letter, pin, strip, servo, port, backlight in (
                ("L", self.SERVO_STRIP_L, strip_l, servo_l, self.spce_a, self.SPCE_A_BL_PIN),
                ("R", self.SERVO_STRIP_R, strip_r, servo_r, self.spce_b, self.SPCE_B_BL_PIN)):
            if strip and servo:
                raise ValueError(f"The {letter} connector carries one signal, so it cannot be a strip and a servo at once. Declare strip_{letter.lower()} or servo_{letter.lower()}.")

            if strip:
                from plasma import WS2812
                built = WS2812(strip, self.STRIP_PIO, len(self.__strips), pin)
                built.start()
                self.__strips[letter] = built

            elif servo:
                # Each connector shares a PWM channel with one screen port's backlight,
                # and both pins emit the same signal once both select PWM
                if port.mode == SPCE.SCREEN:
                    raise ValueError(f"A servo on {letter} cannot run while SP/CE {port.name} drives a screen. GPIO {pin} shares a PWM channel with GPIO {backlight}, which is that port's backlight, so put the servo on the other connector.")

                from servo import Servo
                self.__servos[letter] = Servo(pin) if servo is True else Servo(pin, calibration=servo)

        # Whatever was declared still needs power: one rail serves both connectors,
        # and it stays down until enable_rail() is called, so nothing on the header
        # is live before the caller starts driving it

    def boot_pressed(self):
        return self.__switch.value() == 0

    def enable_rail(self):
        """Power the L and R connectors. One rail serves both, so a load on
        either is live from here.
        """
        self.__rail_en.on()

    def disable_rail(self):
        """Take the power off both connectors."""
        self.__rail_en.off()

    def is_rail_enabled(self):
        """Whether the L and R connectors are powered."""
        return self.__rail_en.value() == 1

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

    @property
    def strip_l(self):
        """The LED strip on the L connector, declared as MightyFX(strip_l=60)."""
        return self.__declared(self.__strips, "strip", "L")

    @property
    def strip_r(self):
        """The LED strip on the R connector, declared as MightyFX(strip_r=60)."""
        return self.__declared(self.__strips, "strip", "R")

    @property
    def servo_l(self):
        """The servo on the L connector, declared as MightyFX(servo_l=True)."""
        return self.__declared(self.__servos, "servo", "L")

    @property
    def servo_r(self):
        """The servo on the R connector, declared as MightyFX(servo_r=True)."""
        return self.__declared(self.__servos, "servo", "R")

    def __declared(self, built, role, letter):
        """One connector's strip or servo, or why there is none to hand back."""
        made = built.get(letter)
        if made is not None:
            return made

        other = "servo" if role == "strip" else "strip"
        if letter in (self.__servos if role == "strip" else self.__strips):
            raise RuntimeError(f"The {letter} connector is set up as a {other}, so it has no {role}")

        asked = "60" if role == "strip" else "True"
        raise RuntimeError(f"{role}_{letter.lower()} is only there where the board was started with {role}_{letter.lower()}={asked}")

    @property
    def hub_ports(self):
        """The hub's ports, one per panel its chip selects reach, and empty without
        a hub. Each is named as hub_a through hub_f as well.
        """
        return () if self.hub is None else self.hub.ports

    def __getattr__(self, name):
        # Only reached where the attribute is absent, which for a hub port means the
        # board was never declared for a hub
        if name.startswith("hub_") and name[4:] in self.HUB_PORT_NAMES:
            raise AttributeError(f"{name} needs a hub, which is built where one SP/CE port is declared SPCE.SCREEN and the other SPCE.HUB_LINES")

        raise AttributeError(name)

    def clear(self):
        for out in self.outputs:
            out.set_rgb(0, 0, 0)

        for strip in self.__strips.values():
            strip.clear()

    def shutdown(self):
        self.clear()

        # A servo holds its position while it is driven, so it stops being driven
        # before the rail goes: the two together leave it limp rather than pushing
        for servo in self.__servos.values():
            servo.disable()

        self.disable_rail()

        # The strips hand back their state machines, DMA and PIO program as they
        # are collected, so drop them and collect now: a board built after this
        # takes the same slots.
        self.__strips.clear()
        gc.collect()

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
