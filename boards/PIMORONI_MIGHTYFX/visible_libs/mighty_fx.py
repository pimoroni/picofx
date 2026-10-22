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
from ports import ScreenPort


# The PWM objects wake() lit, held here since one that is collected stops driving its pin
__waking = []


class SPCE:
    """What a SP/CE connector carries, declared when the board is built."""

    SCREEN = 0          # Screens, over the connector's own SPI bus and backlight
    GPIO = 1            # The five pins, free to borrow through pins
    GPIO_PWM = 2        # The same, where the four data lines will be driven by PWM
    HUB_SELECTS = 3     # The five pins, as the chip selects a hub addresses panels with
    MOTOR_DRIVER = 4    # A motor driver breakout, built by the board and handed out as driver


class SPCEPort(ScreenPort):
    """One of the board's SP/CE connectors, built by the board and handed out.

    A screen connector is a screen port and is built as one. Every other declaration
    leaves the bus and the pins alone and hands the five GPIOs out through the property
    that names what they are for, so spending a connector is visible in the call that
    declared it.
    """

    def __init__(self, name, mode, pins, pio=None, sm=None):
        if mode not in (None, SPCE.SCREEN, SPCE.GPIO, SPCE.GPIO_PWM, SPCE.HUB_SELECTS, SPCE.MOTOR_DRIVER):
            raise ValueError(f"{mode} is not a valid SP/CE mode. Expected SPCE.SCREEN, "
                             "SPCE.GPIO, SPCE.GPIO_PWM, SPCE.HUB_SELECTS, SPCE.MOTOR_DRIVER, or None.")

        self.name = name
        self.mode = mode

        if mode == SPCE.SCREEN:
            super().__init__(pins, label=f"SP/CE {name}")
            return

        self.label = f"SP/CE {name}"

        # An undeclared connector is left alone, so it makes no Pins
        self.__pins = (tuple(Pin(pin) for pin in pins)
                       if mode is not None else None)

        # What a screen port holds, so a board's shutdown runs over any declaration
        self.__screens = []
        self.__backlight = None
        self.__spi_bus = None
        self.__cs_claimed = []
        self.__dc_claimed = []
        self.__panels_reset = False

        # The PIO and state machine a motor driver takes are the board's to give, as it
        # knows what else holds them
        self.__driver = None
        if mode == SPCE.MOTOR_DRIVER:
            from spce import MotorDriver
            self.__driver = MotorDriver(self.__pins, pio, sm)

    @property
    def pins(self):
        """The connector's five GPIOs, in the order DC, CS, SCK, MOSI, BL.

        What a breakout plugged in here is built from. Only a connector declared SPCE.GPIO
        or SPCE.GPIO_PWM offers them.
        """
        if self.mode not in (SPCE.GPIO, SPCE.GPIO_PWM):
            raise ValueError(f"SP/CE {self.name} is not declared SPCE.GPIO or "
                             "SPCE.GPIO_PWM, so its pins are not free to borrow")

        return self.__pins

    @property
    def hub_selects(self):
        """The connector's five GPIOs, as the chip selects a hub addresses panels with.

        Only a connector declared SPCE.HUB_SELECTS offers them, as that declaration spends
        it on another port's screens.
        """
        if self.mode != SPCE.HUB_SELECTS:
            raise ValueError(f"SP/CE {self.name} is not declared SPCE.HUB_SELECTS, so its "
                             "pins are not a hub's chip selects")

        return self.__pins

    @property
    def driver(self):
        """The motor driver breakout on this connector, built where it is declared SPCE.MOTOR_DRIVER.

        Its motors are driven by a PIO, so no LED output loses its PWM channel to them.
        """
        if self.mode != SPCE.MOTOR_DRIVER:
            raise ValueError(f"SP/CE {self.name} is not declared SPCE.MOTOR_DRIVER, so it has "
                             "no motor driver")

        return self.__driver

    def __line(self, index):
        if self.mode != SPCE.SCREEN:
            raise ValueError(f"SP/CE {self.name} is not a screen port, so it has no "
                             f"{self.LINE_NAMES[index]} line")

        return self.__pins[index]

    # Only a screen connector has these. Pass dc or cs to a screen to share that line
    @property
    def dc(self):
        """The connector's data and command line, which the first screen on it takes."""
        return self.__line(0)

    @property
    def cs(self):
        """The connector's chip select, which the first screen on it takes."""
        return self.__line(1)

    @property
    def sck(self):
        """The connector's SPI clock, which its bus is made on."""
        return self.__line(2)

    @property
    def mosi(self):
        """The connector's SPI data line, which its bus is made on."""
        return self.__line(3)

    @property
    def bl(self):
        """The connector's backlight line, which every screen on it shares."""
        return self.__line(4)

    @property
    def __bus(self):
        # Refused on a port that is not a screen port, and made again after a release() as
        # the screen port's own bus is
        if self.mode != SPCE.SCREEN:
            raise ValueError(f"SP/CE {self.name} is not a screen port, so it has no display bus")

        if self.__spi_bus is None:
            self.__spi_bus = self.__make_bus()

        return self.__spi_bus

    def release(self):
        """Hand the connector's lines back, and a screen port's bus and SRAM with them."""
        if self.mode == SPCE.SCREEN:
            super().release()
            return

        # The driver's state machine and DMA channel go back now, as a stale reference
        # could keep them from the next board's
        if self.__driver is not None:
            self.__driver.deinit()
            self.__driver = None

        # Whatever is plugged in next meets the level these pins were left at, and high
        # on a motor input drives it before that thing's own code has run
        if self.__pins is not None:
            for pin in self.__pins:     # All five, another port's chip selects among them
                pin.init(Pin.IN, Pin.PULL_DOWN)


class __ClusterServo:
    # One servo of a ServoCluster, offering the methods of a Servo

    def __init__(self, cluster, index):
        self.__cluster = cluster
        self.__index = index

    def pin(self):
        return self.__cluster.pin(self.__index)

    def enable(self):
        self.__cluster.enable(self.__index)

    def disable(self):
        self.__cluster.disable(self.__index)

    def is_enabled(self):
        return self.__cluster.is_enabled(self.__index)

    # These read with no argument and set with one, as a Servo's methods do
    def pulse(self, *args):
        return self.__cluster.pulse(self.__index, *args)

    def value(self, *args):
        return self.__cluster.value(self.__index, *args)

    def calibration(self, *args):
        return self.__cluster.calibration(self.__index, *args)

    # The cluster's, so setting it on either servo sets both
    def frequency(self, *args):
        return self.__cluster.frequency(*args)

    def min_value(self):
        return self.__cluster.min_value(self.__index)

    def mid_value(self):
        return self.__cluster.mid_value(self.__index)

    def max_value(self):
        return self.__cluster.max_value(self.__index)

    def to_min(self):
        self.__cluster.to_min(self.__index)

    def to_mid(self):
        self.__cluster.to_mid(self.__index)

    def to_max(self):
        self.__cluster.to_max(self.__index)

    def to_percent(self, *args):
        self.__cluster.to_percent(self.__index, *args)


class MightyFX:
    """The Mighty FX board, with its seven RGB outputs, its connectors and its audio."""

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

    # Motor drivers and servos take PIO 2 as clusters, one state machine for each SP/CE
    # port's driver and one the L and R servos share
    CLUSTER_PIO = 2
    SPCE_A_MOTOR_SM = 0
    SPCE_B_MOTOR_SM = 1
    SERVO_SM = 2

    # LEDs built past the length asked for and driven dark. A flash write pauses the transfer
    # partway through a frame, and the overrun lands on these
    STRIP_FLUSH_LEDS = 2

    # The order a strip takes its red, green and blue in where its declaration names none,
    # which is most WS2812 strips'
    STRIP_ORDER = "grb"

    # The strip connectors in order, each by the name it is written as and the property handing
    # its strip back
    STRIPS = (("stripL", "strip_l"), ("stripR", "strip_r"))

    # The screen ports in order, each by the name it is written as and the attribute holding its
    # SPCEPort
    SCREENS = (("screenA", "spce_a"), ("screenB", "spce_b"))

    # Whether the board has a wireless module, so the FX drive offers the WiFi credentials and
    # the programs that go online. Every Mighty FX carries one
    WIRELESS = True

    # How long a strip takes to power up once the rail is on, and miss any frame sent sooner.
    # A 64 LED panel took one after 5ms and not after 2ms, so this is double that
    RAIL_SETTLE_MS = 10

    SENSOR_PIN = 46

    # The receiver takes PIO 1's last state machine, the strips taking them from zero
    SENSOR_PIO = 1
    SENSOR_SM = 3
    V_SENSE_PIN = 47

    # The sense divider is 10k over 10k, so a reading is half the rail
    V_SENSE_GAIN = 2

    RGB_GAMMA = 2.2         # sRGB, for even hues, chosen by eye on a rainbow

    RGB_COLOUR_NAMES = ("red", "green", "blue")

    # What wake() lights the outputs to, dim enough to read as alive and not as an effect
    WAKE_LEVEL = 0.1

    def __init__(self, spce_a=None, spce_b=None, strip_l=None, strip_r=None,
                 servo_l=None, servo_r=None, sensor=None, init_i2c=True, i2c_freq=100000,
                 init_wav=True, wav_root="/"):
        # What a build claims starts empty, so one that raises partway hands back what it
        # took before the error reaches the caller. Left to the collector, the boot button's
        # handler would hold the board, and with it every state machine the board took
        self.spce_a = self.spce_b = None
        self.__switch = None
        self.__sensor = None
        self.__wav = None
        self.__rail_en = None
        self.__strips = {}
        self.__servos = {}
        self.__servo_cluster = None

        try:
            self.__build(spce_a, spce_b, strip_l, strip_r, servo_l, servo_r, sensor,
                         init_i2c, i2c_freq, init_wav, wav_root)
        except BaseException:
            self.__release()
            raise

    def __build(self, spce_a, spce_b, strip_l, strip_r, servo_l, servo_r, sensor,
                init_i2c, i2c_freq, init_wav, wav_root):
        # A canvas claim has no object to finalise it, so a run that skipped shutdown()
        # leaves the SRAM held. Nothing of this program holds any yet.
        release_buffers()

        # A connector declared for PWM drives its DC, CS, SCK and MOSI lines, holding
        # channels some LED outputs share. BL stays a plain line, so it claims nothing.
        claimed = {}
        for port_name, mode, pins in (("A", spce_a, self.SPCE_A_PINS), ("B", spce_b, self.SPCE_B_PINS)):
            if mode == SPCE.GPIO_PWM:
                for pin in pins[:4]:
                    claimed[self.__pwm_channel(pin)] = (port_name, pin)

        # A DisabledLED stands in for any channel a connector holds, so lighting it
        # reports. It takes the pin too, held off, or that signal would show on the LED.
        self.outputs = []
        for index, rgb_pins in enumerate(self.OUT_PINS):
            leds = []
            for colour, pin in zip(self.RGB_COLOUR_NAMES, rgb_pins):
                holder = claimed.get(self.__pwm_channel(pin))
                if holder is None:
                    leds.append(pin)
                else:
                    port_name, held_pin = holder
                    leds.append(DisabledLED(
                        pin,
                        reason=f"Output {index + 1}'s {colour} LED cannot light. GPIO {pin} shares a PWM channel with GPIO {held_pin}, which SP/CE {port_name} holds, being declared SPCE.GPIO_PWM."))
            self.outputs.append(RGBLED(*leds, invert=False, gamma=self.RGB_GAMMA))

        # Every output's three channels, since a mono LED on an output connector reaches one of them
        self.monos = [led for output in self.outputs for led in output.leds]

        # Set up the enable for the rail the L and R connectors share
        self.__rail_en = Pin(self.SERVO_STRIP_EN, Pin.OUT, value=False)

        # A strip carries its length and a servo its calibration, so one setting names
        # the role and what it needs. Anything else is left alone, no pin claimed.
        declared_servos = []
        for letter, pin, strip, servo in (
                ("L", self.SERVO_STRIP_L, strip_l, servo_l),
                ("R", self.SERVO_STRIP_R, strip_r, servo_r)):
            # Tested against None, as ANGULAR is zero and the commonest calibration would read as no servo
            if strip is not None and servo is not None:
                raise ValueError(f"The {letter} connector carries one signal, so it cannot be a strip and a servo at once. Declare strip_{letter.lower()} or servo_{letter.lower()}.")

            # A strip is sent a frame only by update(). A refresh of its own would resend it
            # through every flash write, and a frame sent during one is torn
            if strip is not None:
                from plasma import WS2812
                length, order = self.__strip_declared(letter, strip)
                self.__strips[letter] = WS2812(length + self.STRIP_FLUSH_LEDS, self.STRIP_PIO,
                                               len(self.__strips), pin, color_order=order)

            elif servo is not None:
                declared_servos.append((letter, pin, servo))

        # The servos share one cluster, leaving each connector's PWM channel to the backlight it
        # shares. It is built before the motor drivers, as the first cluster on the PIO sets the
        # 32 pins it reaches, and the servos' window holds either port's pins too
        if declared_servos:
            from servo import Calibration, ServoCluster
            self.__servo_cluster = ServoCluster(self.CLUSTER_PIO, self.SERVO_SM,
                                                [pin for _, pin, _ in declared_servos])
            for index, (letter, _, servo) in enumerate(declared_servos):
                # True keeps the cluster's default calibration, and anything else names one
                if servo is not True:
                    calibration = servo if isinstance(servo, Calibration) else Calibration(servo)
                    self.__servo_cluster.calibration(index, calibration)
                self.__servos[letter] = __ClusterServo(self.__servo_cluster, index)

        # The rail stays down until enable_rail(), so nothing on the header is live before then

        # Each port owns its bus and pins, and screens are created against them
        self.spce_a = SPCEPort("A", spce_a, self.SPCE_A_PINS, self.CLUSTER_PIO, self.SPCE_A_MOTOR_SM)
        self.spce_b = SPCEPort("B", spce_b, self.SPCE_B_PINS, self.CLUSTER_PIO, self.SPCE_B_MOTOR_SM)

        # One connector given over to chip selects makes the other's panels a hub, built
        # here. Imported only where a board asked for one.
        self.__hub = None
        for screen_port, selects_port in ((self.spce_a, self.spce_b), (self.spce_b, self.spce_a)):
            if selects_port.mode != SPCE.HUB_SELECTS:
                continue

            if screen_port.mode != SPCE.SCREEN:
                raise ValueError(f"SP/CE {selects_port.name} is declared SPCE.HUB_SELECTS, which are the chip selects for panels on the other connector, so declare SP/CE {screen_port.name} as SPCE.SCREEN")

            from screens import ScreenHub
            self.__hub = ScreenHub(screen_port, extra_cs=selects_port.hub_selects)

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

        # Set up whatever the sensor connector was declared as
        self.__sensor = build_sensor(sensor, self.SENSOR_PIN, self.SENSOR_PIO, self.SENSOR_SM)

        # Set up the wav (and tone) player, if the user wants. Its refills come from Python
        # between screen frames, which two screens playing GIFs held up by as much as 100ms,
        # so the ring holds twice that
        if init_wav:
            self.__wav = WavPlayer(0, self.I2S_BCLK_PIN, self.I2S_LRCLK_PIN, self.I2S_DATA_PIN, self.AMP_EN_PIN,
                                   root=wav_root, ibuf_ms=200)

    @classmethod
    def __strip_declared(cls, letter, strip):
        # A strip is declared as its length, or as (length, order) with the letters in the
        # order the strip takes its colours, returned as the plasma module's colour order
        length, order = strip if isinstance(strip, (tuple, list)) else (strip, cls.STRIP_ORDER)
        if not isinstance(order, str) or sorted(order.lower()) != ["b", "g", "r"]:
            raise ValueError(f"strip_{letter.lower()}'s colour order is {order!r}, so give the letters r, g and b in the order the strip takes them, such as (60, \"rgb\")")

        import plasma
        return length, getattr(plasma, "COLOR_ORDER_" + order.upper())

    @staticmethod
    def __pwm_channel(gpio):
        # The RP2350 shares its PWM channels between GPIO pairs, pins 16 apart below
        # GPIO 32 and 8 apart above it, so an LED output can land on a channel a SP/CE
        # role drives
        if gpio < 32:
            return gpio % 16
        return 16 + ((gpio - 32) % 8)

    @classmethod
    def wake(cls):
        """Light every output dim white before there is a board, so seconds of importing do not read as a dead one."""
        duty = int(65535 * cls.WAKE_LEVEL)
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
        # Each bounce is another falling edge, and anything inside the window is the same press
        now = time.ticks_ms()
        if time.ticks_diff(now, self.__tapped_at) > self.BOOT_DEBOUNCE_MS:
            self.__tapped_at = now
            self.__taps += 1

    def enable_rail(self):
        """Power the L and R connectors, returning once a strip on them can take a frame."""
        if not self.is_rail_enabled():
            self.__rail_en.on()
            time.sleep_ms(self.RAIL_SETTLE_MS)

    def disable_rail(self):
        """Take the power off both connectors."""
        self.__rail_en.off()

    def is_rail_enabled(self):
        """Whether the L and R connectors are powered."""
        return self.__rail_en.value() == 1

    def read_voltage(self, samples=1):
        """Read the supply voltage the board runs from, which on battery is the cell itself."""
        val = 0
        for _ in range(samples):
            val += self.__v_sense.read_u16()
        val /= samples

        return (val * 3.3 * self.V_SENSE_GAIN) / 65535

    @property
    def hub(self):
        """The six-panel screen hub, built where the board's ports declare one."""
        if self.__hub is None:
            raise RuntimeError("hub is only accessible if the board was created with one SP/CE port as SPCE.SCREEN and the other as SPCE.HUB_SELECTS")
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
        """The LED strip on the L connector, declared as MightyFX(strip_l=60), or MightyFX(strip_l=(60, "rgb")) for one taking its colours in another order. Shown by update()."""
        return self.__declared(self.__strips, "strip", "L")

    @property
    def strip_r(self):
        """The LED strip on the R connector, declared as MightyFX(strip_r=60), or MightyFX(strip_r=(60, "rgb")) for one taking its colours in another order. Shown by update()."""
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
            strip.update()

    def shutdown(self):
        self.clear()
        self.__release()

    def __release(self):
        # Hands back what a build claimed, in the order the hardware wants, and runs over a build
        # that stopped partway, which has no ports where it failed before them
        ports = [port for port in (self.spce_a, self.spce_b) if port is not None]

        # The handler holds this board, so once detached a board left behind can be collected
        if self.__switch is not None:
            self.__switch.irq(handler=None)

        # Stop and collect the receiver now, so the next board's takes the same PIO slot
        if hasattr(self.__sensor, "stop"):
            self.__sensor.stop()
            self.__sensor = None
            gc.collect()

        # A motor left driving keeps going, so each driver stops and lets go of its cluster first
        for port in ports:
            if port.mode == SPCE.MOTOR_DRIVER:
                port.release()

        # A servo stops being driven before the rail goes, so it goes limp instead of pushing
        for servo in self.__servos.values():
            servo.disable()

        if self.__rail_en is not None:
            self.disable_rail()

        # The servos' state machine and DMA channel go back now, as a stale reference could
        # keep them from the next board's
        if self.__servo_cluster is not None:
            self.__servo_cluster.__del__()
            self.__servo_cluster = None
        self.__servos.clear()

        # Hand each strip's state machine and DMA channel back now, so the next board's
        # strips can take the same slots. Left to the collector, a stale reference to a
        # strip, a stopped player's or one still on the C stack, keeps them claimed
        for strip in self.__strips.values():
            strip.__del__()
        self.__strips.clear()
        gc.collect()

        for port in ports:
            port.backlight_off()

        # A panel keeps scanning its frame, so anything later driving the backlight
        # would show it again. After the light is out, so nothing is seen going dark.
        for port in ports:
            port.stop_panels()

        # Give the DMA channels back now, so repeated screens do not exhaust the 16
        for port in ports:
            port.release()

        # No screen draws from a canvas now, so the SRAM goes back
        release_buffers()

        if self.__wav:
            self.__wav.deinit()
