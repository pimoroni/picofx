# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import gc
import time

from machine import PWM, Pin
from pimoroni_i2c import PimoroniI2C
from picofx import PWMLED, RGBLED
from ports import ScreenPort
from spidisplay import release_buffers


# What wake() lit, kept alive: a PWM object that is collected stops driving
__waking = []


class SPCE:
    """What the SP/CE connector carries, declared when the board is built."""

    SCREEN = 0          # A screen, over the connector's own SPI bus and backlight


class SPCEPort(ScreenPort):
    """The board's SP/CE connector, built by the board and handed out.

    Declared SPCE.SCREEN it is a screen port and is built as one. Undeclared, it
    leaves the bus and the pins alone and only says what it is.
    """

    def __init__(self, name, mode, pins):
        if mode not in (None, SPCE.SCREEN):
            raise ValueError(f"{mode} is not a valid SP/CE mode. Expected SPCE.SCREEN or None.")

        self.name = name
        self.mode = mode

        if mode == SPCE.SCREEN:
            super().__init__(pins, label=f"SP/CE {name}")
        else:
            self.label = f"SP/CE {name}"


class PlasmaFX:
    LED_DATA_PIN = 15
    LED_CLK_PIN = 14

    RGB_PINS = (16, 17, 18)

    I2C_SDA_PIN = 20
    I2C_SCL_PIN = 21

    SW_A_PIN = 12
    USER_SW_PIN = 22

    # How long after a press its own contact bounce is ignored for
    BOOT_DEBOUNCE_MS = 40

    SPCE_DC_PIN = 8
    SPCE_CS_PIN = 9
    SPCE_SCK_PIN = 10
    SPCE_MOSI_PIN = 11
    SPCE_BL_PIN = 7

    # The one connector, its port lettered A, which a file names screen
    SPCE_A_PINS = (SPCE_DC_PIN, SPCE_CS_PIN, SPCE_SCK_PIN, SPCE_MOSI_PIN, SPCE_BL_PIN)

    STRIP_PIO = 0

    # LEDs built past the length asked for and driven dark: a flash write pauses the
    # transfer sending a frame partway, breaking it apart, and the overrun lands on these
    STRIP_FLUSH_LEDS = 2

    # The order a WS2812 strip takes its red, green and blue in where its declaration names
    # none, which is most WS2812 strips'
    STRIP_ORDER = "grb"

    # The top of an APA102's brightness, which each LED holds in five bits. Where a
    # declaration names none the plasma module's own 15 stands, about half
    APA102_BRIGHTEST = 31

    # The strips in order, each by the name it is written as and the property handing its strip
    # back. The APA102 takes a brightness after its length where a WS2812 takes a colour order,
    # and takes both terminals, so it cannot play beside either WS2812
    STRIPS = (("stripDat", "strip_dat"), ("stripClk", "strip_clk"), ("stripApa", "strip_apa"))
    STRIP_BRIGHTNESS = ("stripApa",)
    STRIP_TAKES = (("stripApa", ("stripDat", "stripClk")),)

    # The screen port, by the name it is written as and the attribute holding its SPCEPort.
    # Emptied by detect() on a 2350 W, which has no SP/CE connector
    SCREENS = (("screen", "spce_a"),)

    # Whether the board has a wireless module, so the FX drive offers the WiFi credentials and
    # the programs that go online. Set by detect() on a 2350 W
    WIRELESS = False

    # The 2350 W's wireless module: power enable, data, chip select and clock. None of these
    # pins is connected on the 2350
    WIRELESS_PINS = (23, 24, 25, 29)

    # How long the module has to answer after power-up. It answers within 20ms; its driver
    # allows 250ms, which every 2350 would wait out
    WIRELESS_START_MS = 100

    # What the module's test register reads once it has started, 0xFEEDBEAD with its halves
    # swapped as its 16-bit words arrive
    WIRELESS_TEST_PATTERN = 0xBEADFEED

    # A read of 32 bits at the test register, 0x14, with the command's halves swapped for the
    # 16-bit words the module takes from power-up
    WIRELESS_TEST_READ = 0xA0044000

    RGB_GAMMA = 2.2         # sRGB, for even hues, chosen by eye on a rainbow

    # What wake() lights the board's LED to: dim enough to read as alive, not as an effect
    WAKE_LEVEL = 0.1

    def __init__(self, spce_a=None, strip_dat=None, strip_clk=None, strip_apa=None,
                 init_i2c=True, i2c_freq=100000):
        # A canvas claim has no object to finalise it, so a run that skipped shutdown()
        # leaves the SRAM held. Nothing of this program holds any yet.
        release_buffers()

        # No outputs of its own: the board's RGB LED, active low, is the one light every
        # file can reach
        self.outputs = []
        self.rgb = RGBLED(*self.RGB_PINS, invert=True, gamma=self.RGB_GAMMA)

        # The port owns its bus and pins; a screen is created against it
        self.spce_a = SPCEPort("A", spce_a, self.SPCE_A_PINS)

        # Set up the i2c for Qw/st, if the user wants
        self.__i2c = None
        if init_i2c:
            self.__i2c = PimoroniI2C(self.I2C_SDA_PIN, self.I2C_SCL_PIN, i2c_freq)

        # A press is caught by interrupt as well as read, so a tap inside a long frame is not missed
        self.__switch = Pin(self.USER_SW_PIN, Pin.IN, Pin.PULL_UP)
        self.__taps = 0
        self.__tapped_at = 0
        self.__switch.irq(trigger=Pin.IRQ_FALLING, handler=self.__switch_pressed)

        # A WS2812 strip takes a data line, so each terminal can carry one, strip_dat and
        # strip_clk. An APA102 strip takes both terminals, data and clock, as strip_apa.
        # A strip is sent a frame only by update(). A refresh of its own would resend it
        # through every flash write, and a frame sent during one is torn
        self.__strips = {}
        if strip_apa is not None:
            if strip_dat is not None or strip_clk is not None:
                raise ValueError("An APA102 strip takes both terminals, data and clock, so "
                                 "strip_apa cannot sit beside strip_dat or strip_clk. "
                                 "Declare strip_apa alone.")
            from plasma import APA102
            length, brightness = self.__apa_declared(strip_apa)
            strip = APA102(length + self.STRIP_FLUSH_LEDS, self.STRIP_PIO, 0,
                           self.LED_DATA_PIN, self.LED_CLK_PIN)
            if brightness is not None:
                strip.set_brightness(brightness)
            self.__strips["apa"] = strip

        for name, pin, strip in (("dat", self.LED_DATA_PIN, strip_dat),
                                 ("clk", self.LED_CLK_PIN, strip_clk)):
            if strip is not None:
                from plasma import WS2812
                length, order = self.__strip_declared(name, strip)
                self.__strips[name] = WS2812(length + self.STRIP_FLUSH_LEDS, self.STRIP_PIO,
                                             len(self.__strips), pin, color_order=order)

    @classmethod
    def __strip_declared(cls, name, strip):
        # A WS2812 strip is declared as its length, or as (length, order) with the letters in
        # the order the strip takes its colours, returned as the plasma module's colour order
        length, order = strip if isinstance(strip, (tuple, list)) else (strip, cls.STRIP_ORDER)
        if not isinstance(order, str) or sorted(order.lower()) != ["b", "g", "r"]:
            raise ValueError(f"strip_{name}'s colour order is {order!r}, so give the letters r, g and b in the order the strip takes them, such as (60, \"rgb\")")

        import plasma
        return length, getattr(plasma, "COLOR_ORDER_" + order.upper())

    @classmethod
    def __apa_declared(cls, strip):
        # An APA102 strip is declared as its length, or as (length, brightness) with the
        # brightness from 0 to 1, returned in the strip's own steps, or None to leave the
        # plasma module's. Anything above nothing keeps a step, so a dim strip stays lit
        length, brightness = strip if isinstance(strip, (tuple, list)) else (strip, None)
        if brightness is None:
            return length, None
        if isinstance(brightness, bool) or not isinstance(brightness, (int, float)) or \
                not 0 <= brightness <= 1:
            raise ValueError(f"strip_apa's brightness is {brightness!r}, so give it from 0 to 1, such as (144, 0.5)")
        steps = int(brightness * cls.APA102_BRIGHTEST)
        return length, max(1, steps) if brightness > 0 else 0

    @classmethod
    def wake(cls):
        """Light the board's LED dim white before there is a board, so seconds of importing do not read as a dead one."""
        duty = int(65535 * cls.WAKE_LEVEL)
        # Held at module level, since a PWM that is collected stops driving its pin
        for pin in cls.RGB_PINS:
            __waking.append(PWM(Pin(pin), freq=PWMLED.FREQUENCY, duty_u16=duty, invert=True))

    @classmethod
    def detect(cls):
        """Narrow the declared parts to this board's, before anything reads them. A 2350 W carries its wireless module where the 2350 has its SP/CE connector, so it has no screen port."""
        if cls.__wireless_fitted():
            cls.SCREENS = ()
            cls.WIRELESS = True

    @classmethod
    def __wireless_fitted(cls):
        # Once something has brought the wireless driver up, the module may be in use and is left
        # powered. The driver read the module's own MAC address where it found one
        try:
            import network
        except ImportError:
            return cls.__wireless_answers()
        wlan = network.WLAN(network.STA_IF)
        if wlan.active():
            return wlan.config("mac") != bytes(6)
        return cls.__wireless_answers()

    @classmethod
    def __wireless_answers(cls):
        # Driven from plain pins, so no state machine or DMA channel is claimed, and powered
        # down after for its driver to start afresh
        power_pin, data_pin, select_pin, clock_pin = cls.WIRELESS_PINS
        power = Pin(power_pin, Pin.OUT, value=0)
        select = Pin(select_pin, Pin.OUT, value=1)
        clock = Pin(clock_pin, Pin.OUT, value=0)
        data = Pin(data_pin, Pin.OUT, value=0)
        time.sleep_ms(20)
        power.value(1)
        powered = time.ticks_ms()
        answered = False
        while not answered and time.ticks_diff(time.ticks_ms(), powered) < cls.WIRELESS_START_MS:
            # Read back to back from power-up, the module can stop answering until powered again
            time.sleep_ms(5)
            answered = cls.__wireless_test_read(data, select, clock) == cls.WIRELESS_TEST_PATTERN
        power.value(0)
        data.init(Pin.IN, Pin.PULL_DOWN)
        return answered

    @classmethod
    def __wireless_test_read(cls, data, select, clock):
        # The command out on the data line, then the line turned round and the reply read in,
        # a bit to each clock pulse
        select.value(0)
        data.init(Pin.OUT, value=0)
        for bit in range(31, -1, -1):
            data.value(cls.WIRELESS_TEST_READ >> bit & 1)
            clock.value(1)
            clock.value(0)
        data.init(Pin.IN, Pin.PULL_DOWN)
        word = 0
        for _ in range(32):
            word = word << 1 | data.value()
            clock.value(1)
            clock.value(0)
        select.value(1)
        return word

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

    @property
    def i2c(self):
        if self.__i2c is None:
            raise RuntimeError("i2c is only accessible if the board was created with init_i2c=True")
        return self.__i2c

    @property
    def strip_dat(self):
        """The WS2812 strip on the DAT terminal, declared as PlasmaFX(strip_dat=60), or PlasmaFX(strip_dat=(60, "rgb")) for one taking its colours in another order. Shown by update()."""
        return self.__declared("dat")

    @property
    def strip_clk(self):
        """The WS2812 strip on the CLK terminal, declared as PlasmaFX(strip_clk=60), or PlasmaFX(strip_clk=(60, "rgb")) for one taking its colours in another order. Shown by update()."""
        return self.__declared("clk")

    @property
    def strip_apa(self):
        """The APA102 strip across both terminals, declared as PlasmaFX(strip_apa=144), or PlasmaFX(strip_apa=(144, 0.5)) for a brightness from 0 to 1. Shown by update()."""
        return self.__declared("apa")

    def __declared(self, name):
        made = self.__strips.get(name)
        if made is None:
            raise RuntimeError(f"strip_{name} is only accessible if the board was created with "
                               f"its LED count, strip_{name}=60 for example")
        return made

    def clear(self):
        self.rgb.off()

        for strip in self.__strips.values():
            strip.clear()
            strip.update()

    def shutdown(self):
        self.clear()

        # Hand each strip's state machine and DMA channel back now, so the next board's
        # strips can take the same slots. Left to the collector, a stale reference to a
        # strip, a stopped player's or one still on the C stack, keeps them claimed
        for strip in self.__strips.values():
            strip.__del__()
        self.__strips.clear()
        gc.collect()

        # The next board's interrupt replaces this one's, which otherwise keeps it alive
        self.__switch.irq(handler=None)

        if self.spce_a.mode == SPCE.SCREEN:
            self.spce_a.backlight_off()

            # A panel keeps scanning its frame, so anything later driving the backlight
            # would show it again. After the light is out, so nothing is seen going dark.
            self.spce_a.stop_panels()

            # Give the DMA channel back now, so repeated screens do not exhaust the 16
            self.spce_a.release()

        # No screen draws from a canvas now, so the SRAM goes back
        release_buffers()
