# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import time

from machine import ADC, Pin
from pimoroni_i2c import PimoroniI2C
from motor import Motor
from picofx import RGBLED, DisabledLED, PWMLED
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
    HUB_LINES = 3


class Backlight(PWMLED):
    """A screen backlight, driven as any other LED on the board is.

    Dark from power-on until a screen on its port has shown a frame, so no panel
    lights on what bringup left it holding. off() takes it dark again and keeps the
    brightness, so on() brings the same level back, and both wait a scan so content
    written while dark is everywhere before the light returns.

    0.0 is off and every setting above it lands somewhere the panel answers, so the
    range a caller is given is the range they can see. Screens on one port share the
    line and so the setting.
    """

    # Duty follows the setting raised to this, since perceived brightness goes as
    # roughly the cube root of light output. Chosen on the panel against 2.2 and 3.0.
    GAMMA = 2.8

    # Where a setting above zero starts. What the driver needs is a pulse rather than a
    # duty, so it costs a larger share of a shorter period, and it is measured on
    # holding a steady level rather than on lighting at all, which fails later: the
    # worst of six 2.8" units was unsteady at 17.7us and the worst of four 1.54" at
    # 13.3us, and this clears both. One figure whatever the panel, a port's one BL line
    # serving every screen on it and a hub being free to mix sizes.
    MINIMUM_PULSE_US = 20

    # That rate is audible and kept so, leaving the band costing most of the range: the
    # same pulse is 40% duty at 20kHz. A clk_sys change after this is built moves it.
    MINIMUM_DUTY = MINIMUM_PULSE_US * PWMLED.FREQUENCY / 1_000_000

    def __init__(self, port, pin):
        super().__init__(pin, gamma=self.GAMMA)
        self.__port = port
        self.__level = 1.0     # What a frame lights to, and what on() restores
        self.__control = 0.0   # The setting as it was asked for, which toggle inverts
        self.__lit = False
        self.__waiting = True  # Dark until a frame lands, against dark by choice

        # The minimum in the terms the gamma reads, so a setting maps onto it there
        self.__lowest = pow(self.MINIMUM_DUTY, 1.0 / self.GAMMA)

    def brightness(self, value):
        """Set the level and light to it, which also ends any wait for a frame.

        0.0 is off and keeps the level for the next on(), so a caller can use either
        spelling. Everything above it spans MINIMUM_DUTY to full.
        """
        value = min(1.0, max(0.0, value))
        self.__waiting = False
        self.__control = value
        self.__lit = value > 0.0
        if self.__lit:
            self.__level = value

        # The minimum folds into the curve the gamma reads and not into the duty it
        # produces. That curve is what steps evenly to the eye, so offsetting it keeps
        # equal settings equally spaced, where offsetting the duty would spend the
        # first quarter of the range going nowhere anyone could see.
        if self.__lit:
            super().brightness(self.__lowest + value * (1.0 - self.__lowest))
        else:
            super().brightness(0.0)

    def toggle(self):
        """Invert the setting, as any other LED here does.

        Its own, not the curve the parent holds, which carries the minimum folded in.
        """
        self.brightness(1.0 - self.__control)

    def on(self):
        """Light the line at the level it last held."""
        if not self.__lit:
            self.__wait_a_scan()

        self.brightness(self.__level)

    def frame_shown(self):
        """Note a frame reaching the glass, which is what a dark line waits for.

        Only from power-on: a line taken dark by off() stays dark until it is asked
        for again, however much is drawn meanwhile.
        """
        if not self.__waiting:
            return

        self.__wait_a_scan()
        self.brightness(self.__level)

    def __wait_a_scan(self):
        """Hold for one full scan of the slowest screen on the port.

        A finished transfer is not a presented frame: each row keeps what the scan
        last painted there, so the panel needs a full pass before the new frame is
        everywhere.
        """
        slowest = self.__port.slowest_framerate
        if slowest is not None:
            time.sleep_ms(1000 // slowest + 3)


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
        if mode not in (None, SPCE.SCREEN, SPCE.MOTOR_DRIVER, SPCE.GPIO, SPCE.HUB_LINES):
            raise ValueError(f"{mode} is not a valid SP/CE mode. Expected SPCE.SCREEN, SPCE.MOTOR_DRIVER, SPCE.GPIO, SPCE.HUB_LINES, or None.")

        self.name = name
        self.mode = mode

        # A motor port's pins belong to its Motor objects, and an undeclared port is
        # left alone, so neither offers them up
        self.__pins = tuple(Pin(pin) for pin in pins) if mode in (SPCE.SCREEN, SPCE.GPIO, SPCE.HUB_LINES) else None

        self.__bus = SPIDisplayBus(spi=spi, sck=self.__pins[2], mosi=self.__pins[3]) if mode == SPCE.SCREEN else None
        self.__backlight = None
        self.__selector = None
        self.__screens = []
        self.__cs_claimed = []
        self.__dc_claimed = []
        self.__panels_reset = False

    @property
    def io(self):
        """The connector's five GPIOs, in the order DC, CS, SCK, MOSI, BL.

        Only a port declared SPCE.GPIO offers them, so spending a connector on pins
        is visible in the call that declared it.
        """
        if self.mode != SPCE.GPIO:
            raise ValueError(f"SP/CE {self.name} is not declared SPCE.GPIO, so its pins are not free to borrow")

        return self.__pins

    @property
    def hub_lines(self):
        """The connector's five GPIOs, as the chip selects a hub addresses panels
        with. Only a port declared SPCE.HUB_LINES offers them, the declaration being
        what says the connector is spent on another port's screens.
        """
        if self.mode != SPCE.HUB_LINES:
            raise ValueError(f"SP/CE {self.name} is not declared SPCE.HUB_LINES, so its pins are not a hub's chip selects")

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
    def connector(self):
        """The SP/CE connector a screen belongs to, which for a port is itself.

        A hub hands out ports of its own, so a screen asks whatever it was built
        against for the connector holding the bus, the backlight and the screens.
        """
        return self

    @property
    def screens(self):
        """The screens built on this port, in creation order."""
        return tuple(self.__screens)

    @property
    def slowest_framerate(self):
        """The lowest panel refresh rate on the port, which sets any wait for a
        frame to reach the glass. None before a screen is built.
        """
        if not self.__screens:
            return None

        return min(screen.framerate for screen in self.__screens)

    @property
    def default_te(self):
        """What a screen naming no te takes: its own DC line, one panel to a port
        being how MightyFX is wired.
        """
        return True

    @property
    def panels_reset(self):
        """Whether every panel on the port has already been reset and cleared, which
        a hub does for all of them at once and a screen otherwise does for itself.
        """
        return self.__panels_reset

    @panels_reset.setter
    def panels_reset(self, value):
        self.__panels_reset = bool(value)

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

    # The contract a screen is built through, which a ScreenHub port implements too by
    # passing each call along to here. Not for an application to call: each records a
    # claim the port validates later ones against, so a spurious call reserves a line
    # or a channel for no screen.
    def register(self, screen):
        self.__screens.append(screen)

    def next_index(self):
        """The next selector channel, handed out in screen creation order."""
        index = len(self.__screens)
        if index >= self.__selector.count:
            raise ValueError(f"SP/CE {self.name}'s selector has {self.__selector.count} channels, and all of them are taken")

        return index

    def claim_cs(self, pin=None):
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

    def claim_dc(self, pin=None, te=True, shared=False):
        """Register a screen's DC line and return it.

        None takes the port's own, which is the first screen's to have. Pass this
        port's dc to share that line deliberately. Panels using TE may share it only
        where every one of them names that same line as its te, which declares the
        diode that stops each panel's TEOFF pulling the line down; without one they
        divide the line through their series resistors and no asserted level
        survives. The firmware cannot see a diode, so the declaration is the
        caller's.
        """
        switched = self.__selector is not None
        if pin is None:
            pin = self.dc
            if not switched and any(claimed is pin for claimed, _, _ in self.__dc_claimed):
                raise ValueError(f"SP/CE {self.name}'s own DC line is taken. Give this screen a dc, or pass the port's dc to share that line.")

        if not switched:
            for claimed, claimed_te, claimed_shared in self.__dc_claimed:
                if claimed is not pin:
                    continue
                if (te and not shared) or (claimed_te and not claimed_shared):
                    raise ValueError(f"{pin} is carrying TE for another screen. Screens sharing a DC line all need te=False, or te set to that line on every one of them, which needs a diode fitted to each breakout.")

        self.__dc_claimed.append((pin, te, shared))
        return pin

    def claim_backlight(self):
        """The port's backlight, created for the first screen to ask for it.

        The connector carries one BL line, so every screen taking it shares the
        setting. If no screen claims it the pin is left alone, free to be a CS or DC.
        """
        if self.__backlight is None:
            self.__backlight = Backlight(self, self.bl)

        return self.__backlight

    def backlight_off(self):
        if self.__backlight is not None:
            self.__backlight.off()

    def release(self):
        """Hand back the bus's DMA channel and its screens' SRAM claims, which
        nothing else gives up early, and stop driving the connector's lines.

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

    # A hub reaches the screen port's own chip select and the other connector's five,
    # and each of those six is named on the board as well as indexed on the hub
    HUB_PORT_NAMES = ("a", "b", "c", "d", "e", "f")

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
