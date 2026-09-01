# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# An SP/CE connector: what it was declared as, the five GPIOs it carries, and for a
# screen port the SPI bus and backlight its screens share. A board owns two of these
# and hands them out, so the contract a screen is built through lives here rather
# than beside the board class it has nothing to do with.

import time

from machine import Pin
from picofx import PWMLED
from spidisplay import SPIDisplayBus


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
    serve as further screens' CS and DC lines.
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

        self.__spi = spi        # Kept so the bus can be made again after a release()
        self.__bus = self.__make_bus() if mode == SPCE.SCREEN else None
        self.__backlight = None
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

    def __make_bus(self):
        return SPIDisplayBus(spi=self.__spi, sck=self.__pins[2], mosi=self.__pins[3])

    @property
    def bus(self):
        """The SPIDisplayBus every screen on this port streams over.

        Made again where release() gave its DMA channel back, so a port built on a
        second time takes a fresh channel instead of handing out a dead bus.
        """
        if self.mode != SPCE.SCREEN:
            raise ValueError(f"SP/CE {self.name} is not a screen port, so it has no display bus")

        if self.__bus is None:
            self.__bus = self.__make_bus()

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

    # The contract a screen is built through, which a ScreenHub port implements too by
    # passing each call along to here. Not for an application to call: each records a
    # claim the port validates later ones against, so a spurious call reserves a line
    # for no screen.
    #
    # A line is checked before the screen is built and recorded once it is, so a
    # construction that refuses partway leaves nothing behind. The refusals therefore
    # live in the check and the record only appends.
    def register(self, screen):
        self.__screens.append(screen)

    def check_cs(self, pin=None):
        """Resolve a screen's CS line and refuse a line already spoken for.

        None takes the port's own, which is the first screen's to have. Every further
        screen needs its own, since CS is the only signal selecting one panel.
        """
        if pin is None:
            pin = self.cs

        if pin in self.__cs_claimed:
            raise ValueError(f"SP/CE {self.name} already has a screen on {pin}. Every further screen on a port needs a cs of its own.")

        return pin

    def claim_cs(self, pin):
        self.__cs_claimed.append(pin)

    def check_dc(self, pin=None, te=True, shared=False):
        """Resolve a screen's DC line and refuse a line whose TE it would spoil.

        None takes the port's own, which is the first screen's to have. Pass this
        port's dc to share that line deliberately. Panels using TE may share it only
        where every one of them names that same line as its te, which declares the
        diode that stops each panel's TEOFF pulling the line down; without one they
        divide the line through their series resistors and no asserted level
        survives. The firmware cannot see a diode, so the declaration is the
        caller's.
        """
        if pin is None:
            pin = self.dc
            if any(claimed is pin for claimed, _, _ in self.__dc_claimed):
                raise ValueError(f"SP/CE {self.name}'s own DC line is taken. Give this screen a dc, or pass the port's dc to share that line.")

        for claimed, claimed_te, claimed_shared in self.__dc_claimed:
            if claimed is not pin:
                continue
            if (te and not shared) or (claimed_te and not claimed_shared):
                raise ValueError(f"{pin} is carrying TE for another screen. Screens sharing a DC line all need te=False, or te set to that line on every one of them, which needs a diode fitted to each breakout.")

        return pin

    def claim_dc(self, pin, te, shared):
        self.__dc_claimed.append((pin, te, shared))

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
        nothing. The port is free to be built on again afterwards, which is the
        case this exists for. Canvases outlive this, since the other port's screens
        may still be drawing to them; shutdown() is what gives them back, and one
        full-size canvas fills the region, so a program building repeatedly reuses
        the canvas it already has.
        """
        for screen in self.__screens:
            screen.display.__del__()
        self.__screens.clear()

        # The CS and DC claims name screens that are gone and lines handed back below,
        # so they go too and a port built on again starts from nothing
        self.__cs_claimed.clear()
        self.__dc_claimed.clear()

        # Dropped as well as deleted, so the next screen on this port is made a fresh
        # bus with a channel of its own
        if self.__bus is not None:
            self.__bus.__del__()
            self.__bus = None

        # A display leaves its chip select and DC driven high, which is right while
        # anything may still transmit and wrong once nothing will: these are connector
        # pins, and whatever is plugged in next meets the level they were left at. High
        # on a screen's BL line lights its backlight and on a motor input drives it,
        # both before that thing's own code has run. Left pulled down and driving
        # nothing, which is a cold boot's own state at the pin, so a rebuild starts
        # where a fresh boot would and nothing contends with a peripheral driving the
        # same line.
        #
        # A screen port keeps its BL, which the backlight owns and backlight_off()
        # puts out. A port spent on pins hands back all five, another port's chip
        # selects among them. A motor port's belong to its Motor objects.
        if self.mode == SPCE.SCREEN:
            handed_back = self.__pins[:4]
        elif self.mode in (SPCE.GPIO, SPCE.HUB_LINES):
            handed_back = self.__pins
        else:
            handed_back = ()

        for pin in handed_back:
            pin.init(Pin.IN, Pin.PULL_DOWN)


