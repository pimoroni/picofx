# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import gc
import time

from machine import ADC, PWM, Pin
from pimoroni_i2c import PimoroniI2C
from picofx import PWMLED, RGBLED, DisabledLED
from sensor import build_sensor
from audio import WavPlayer
from spidisplay import release_buffers
from spce import SPCE, SPCEPort


# What wake() lit, kept alive: a PWM object that is collected stops driving
__waking = []


# The RP2350 shares its PWM channels between GPIO pairs, pins 16 apart below GPIO 32
# and 8 apart above it, so an LED output can land on a channel an SP/CE role drives
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

    # How long after a press its own contact bounce is ignored for
    BOOT_DEBOUNCE_MS = 40

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

    # Strips take PIO 1, leaving PIO 0 to the I2S audio every board builds
    STRIP_PIO = 1

    # LEDs built past the length asked for and driven dark: a flash write holds the
    # interrupts off long enough to break a frame apart, and the overrun lands on these
    STRIP_FLUSH_LEDS = 2

    SENSOR_PIN = 46

    # The receiver takes PIO 1's last state machine, the strips taking them from zero
    SENSOR_PIO = 1
    SENSOR_SM = 3
    V_SENSE_PIN = 47

    V_SENSE_GAIN = 2
    V_SENSE_DIODE_CORRECTION = 0.3

    RGB_GAMMA = 2.2

    RGB_COLOUR_NAMES = ("red", "green", "blue")

    # What wake() lights the outputs to: dim enough to read as alive, not as an effect
    WAKE_LEVEL = 0.1

    def __init__(self, spce_a=None, spce_b=None, strip_l=None, strip_r=None,
                 servo_l=None, servo_r=None, sensor=None, init_i2c=True, i2c_freq=100000,
                 init_wav=True, wav_root="/"):
        # A canvas claim has no object to finalise it, so a run that skipped shutdown()
        # leaves the SRAM held. Nothing of this program holds any yet.
        release_buffers()

        # A motor role drives PWM on its DC, CS, SCK and MOSI lines, holding channels
        # some LED outputs share. BL becomes a plain enable output, so it claims nothing.
        claimed = {}
        for port_name, mode, pins in (("A", spce_a, self.SPCE_A_PINS), ("B", spce_b, self.SPCE_B_PINS)):
            if mode == SPCE.MOTOR_DRIVER:
                for pin in pins[:4]:
                    claimed[__pwm_channel(pin)] = (port_name, pin)

        # A DisabledLED stands in for any channel a motor role holds, so lighting it
        # reports. It takes the pin too, held off, or the motor's signal would show on the LED.
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
                        pin,
                        reason=f"Output {index + 1}'s {colour} LED cannot light. GPIO {pin} shares a PWM channel with GPIO {motor_pin}, which SP/CE {port_name} is using to drive motors."))
            self.outputs.append(RGBLED(*leds, invert=False, gamma=self.RGB_GAMMA))

        # Every output's three channels, since a mono LED on an output connector reaches one of them
        self.monos = [led for output in self.outputs for led in output.leds]

        # Each port owns its bus and pins; screens are created against them
        self.spce_a = SPCEPort("A", spce_a, 0, self.SPCE_A_PINS)
        self.spce_b = SPCEPort("B", spce_b, 1, self.SPCE_B_PINS)

        # One connector given over to chip selects makes the other's panels a hub, built
        # here. Imported only where a board asked for one.
        self.__hub = None
        for screen_port, lines_port in ((self.spce_a, self.spce_b), (self.spce_b, self.spce_a)):
            if lines_port.mode != SPCE.HUB_LINES:
                continue

            if screen_port.mode != SPCE.SCREEN:
                raise ValueError(f"SP/CE {lines_port.name} is declared SPCE.HUB_LINES, which are the chip selects for panels on the other connector, so declare SP/CE {screen_port.name} as SPCE.SCREEN")

            from screens import ScreenHub
            self.__hub = ScreenHub(screen_port, extra_cs=lines_port.hub_lines)

        # Set up the i2c for Qw/st, if the user wants
        self.__i2c = None
        if init_i2c:
            self.__i2c = PimoroniI2C(self.I2C_SDA_PIN, self.I2C_SCL_PIN, i2c_freq)

        # A press is caught by interrupt as well as read, so a tap inside a long frame is not missed
        self.__switch = Pin(self.USER_SW_PIN, Pin.IN, Pin.PULL_UP)
        self.__taps = 0
        self.__tapped_at = 0
        self.__switch.irq(trigger=Pin.IRQ_FALLING, handler=self.__switch_pressed)

        # Set up the internal voltage sensor
        self.__v_sense = ADC(Pin(self.V_SENSE_PIN))

        # Nothing is claimed where nothing was asked for, leaving the pin free
        self.__sensor = build_sensor(sensor, self.SENSOR_PIN, self.SENSOR_PIO, self.SENSOR_SM)

        # Set up the wav (and tone) player, if the user wants
        self.__wav = None
        if init_wav:
            self.__wav = WavPlayer(0, self.I2S_BCLK_PIN, self.I2S_LRCLK_PIN, self.I2S_DATA_PIN, self.AMP_EN_PIN, root=wav_root)

        # Set up the enable for the rail the L and R connectors share
        self.__rail_en = Pin(self.SERVO_STRIP_EN, Pin.OUT, value=False)

        # A strip carries its length and a servo its calibration, so one setting names
        # the role and what it needs. Anything else is left alone, no pin claimed.
        self.__strips = {}
        self.__servos = {}
        for letter, pin, strip, servo, port, backlight in (
                ("L", self.SERVO_STRIP_L, strip_l, servo_l, self.spce_a, self.SPCE_A_BL_PIN),
                ("R", self.SERVO_STRIP_R, strip_r, servo_r, self.spce_b, self.SPCE_B_BL_PIN)):
            # Tested against None: ANGULAR is zero, so the commonest calibration reads as no servo
            if strip is not None and servo is not None:
                raise ValueError(f"The {letter} connector carries one signal, so it cannot be a strip and a servo at once. Declare strip_{letter.lower()} or servo_{letter.lower()}.")

            if strip is not None:
                from plasma import WS2812
                built = WS2812(strip + self.STRIP_FLUSH_LEDS, self.STRIP_PIO,
                               len(self.__strips), pin)
                built.start()
                self.__strips[letter] = built

            elif servo is not None:
                # Each connector shares a PWM channel with one screen port's backlight
                if port.mode == SPCE.SCREEN:
                    raise ValueError(f"A servo on {letter} cannot run while SP/CE {port.name} drives a screen. GPIO {pin} shares a PWM channel with GPIO {backlight}, which is that port's backlight, so put the servo on the other connector.")

                from servo import Servo
                self.__servos[letter] = Servo(pin) if servo is True else Servo(pin, calibration=servo)

        # The rail stays down until enable_rail(), so nothing on the header is live before then

    @classmethod
    def wake(cls):
        """Light every output dim white before there is a board, so seconds of importing do not read as a dead one."""
        duty = int(65535 * cls.WAKE_LEVEL)
        # Held at module level, since a PWM that is collected stops driving its pin
        for pins in cls.OUT_PINS:
            for pin in pins:
                __waking.append(PWM(Pin(pin), freq=PWMLED.FREQUENCY, duty_u16=duty))

    def boot_pressed(self):
        return self.__switch.value() == 0

    def boot_taps(self):
        """Presses since this was last asked, caught by interrupt so a tap inside one long frame counts."""
        taken = self.__taps
        self.__taps = 0
        return taken

    def __switch_pressed(self, _pin):
        # Each bounce is another falling edge; anything inside the window is the same press
        now = time.ticks_ms()
        if time.ticks_diff(now, self.__tapped_at) > self.BOOT_DEBOUNCE_MS:
            self.__tapped_at = now
            self.__taps += 1

    def enable_rail(self):
        """Power the L and R connectors; one rail serves both."""
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
    def hub(self):
        """The six-panel screen hub, built where the board's ports declare one."""
        if self.__hub is None:
            raise RuntimeError("hub is only accessible if the board was created with one SP/CE port as SPCE.SCREEN and the other as SPCE.HUB_LINES")
        return self.__hub

    @property
    def i2c(self):
        if self.__i2c is None:
            raise RuntimeError("i2c is only accessible if the board was created with init_i2c=True")
        return self.__i2c

    @property
    def wav(self):
        if self.__wav is None:
            raise RuntimeError("wav is only accessible if the board was created with init_wav=True")
        return self.__wav

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
        made = built.get(letter)
        if made is not None:
            return made

        other = "servo" if role == "strip" else "strip"
        if letter in (self.__servos if role == "strip" else self.__strips):
            raise RuntimeError(f"The {letter} connector is set up as a {other}, so it has no {role}")

        name = f"{role}_{letter.lower()}"
        asked = f"its LED count, {name}=60 for example" if role == "strip" else f"{name}=True"
        raise RuntimeError(f"{name} is only accessible if the board was created with {asked}")

    @property
    def sensor(self):
        """What the sensor connector was declared as, or why there is nothing to hand back."""
        if self.__sensor is None:
            raise RuntimeError("sensor is only accessible if the board was created with sensor=ANALOG, sensor=PIR or sensor=IR")

        return self.__sensor

    def clear(self):
        for out in self.outputs:
            out.off()

        for strip in self.__strips.values():
            strip.clear()

    def shutdown(self):
        self.clear()

        # Stop and collect the receiver now, so the next board's takes the same PIO slot
        if hasattr(self.__sensor, "stop"):
            self.__sensor.stop()
            self.__sensor = None
            gc.collect()

        # A motor left driving keeps going, so both stop before their shared power goes
        for port in (self.spce_a, self.spce_b):
            if port.driver is not None:
                for motor in port.driver.motors:
                    motor.disable()
                port.driver.disable()

        # A servo stops being driven before the rail goes, so it goes limp instead of pushing
        for servo in self.__servos.values():
            servo.disable()

        self.disable_rail()

        # Drop the strips and collect now, so the next board's take the same PIO slots
        self.__strips.clear()
        gc.collect()

        self.spce_a.backlight_off()
        self.spce_b.backlight_off()

        # A panel keeps scanning its frame, so anything later driving the backlight
        # would show it again. After the light is out, so nothing is seen going dark.
        self.spce_a.stop_panels()
        self.spce_b.stop_panels()

        # Give the DMA channels back now, so repeated screens do not exhaust the 16
        self.spce_a.release()
        self.spce_b.release()

        # No screen draws from a canvas now, so the SRAM goes back and a rebuilt screen
        # gets the same addresses
        release_buffers()

        if self.__wav:
            self.__wav.deinit()
