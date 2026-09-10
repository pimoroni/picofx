# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# A SP/CE connector, holding what it was declared as, the five GPIOs it carries, and
# for a screen port the SPI bus and backlight its screens share. A board owns two and
# hands them out. The double-underscore methods are the contract a screen is built
# through, forwarded to here by a hub's ports, and each line is checked before a screen
# is built and claimed once it is, so a refusal partway leaves nothing behind.

import logging
import time

from machine import Pin
from picofx import PWMLED
from spidisplay import SPIDisplayBus


class SPCE:
    """What a SP/CE connector can be declared as, which decides what it hands out."""
    SCREEN = 0          # Screens, over the connector's own SPI bus and backlight
    MOTOR_DRIVER = 1    # Two motors and the enable they share
    GPIO = 2            # The five pins, free to borrow through io
    HUB_LINES = 3       # The five pins, as the chip selects a hub addresses panels with


class Backlight(PWMLED):
    """A screen backlight, driven as any other LED on the board is.

    Dark from power-on until a screen on its port has shown a frame, so no panel lights
    on what bringup left it holding, and reveal_together holds it until every screen
    asking has drawn. 0.0 is off and every setting above it lands somewhere the panel
    answers, so the range a caller is given is the range they can see. Screens on one
    port share the line and so the setting.
    """

    # Duty follows the setting raised to this, since perceived brightness goes as
    # roughly the cube root of light output. Chosen on the panel against 2.2 and 3.0.
    GAMMA = 2.8

    # Where a setting above zero starts, measured on holding a steady level rather than
    # on lighting at all, which fails later. The worst of six 2.8" units was unsteady at
    # 17.7us and the worst of four 1.54" at 13.3us. One figure whatever the panel, a
    # port's one BL line serving every screen on it.
    MINIMUM_PULSE_US = 20

    # That rate is audible and kept so, leaving the band costing most of the range,
    # since the same pulse is 40% duty at 20kHz. A clk_sys change after this moves it.
    MINIMUM_DUTY = MINIMUM_PULSE_US * PWMLED.FREQUENCY / 1_000_000

    def __init__(self, port, pin):
        super().__init__(pin, gamma=self.GAMMA)
        self.__port = port
        self.__level = 1.0     # What a frame lights to, and what on() restores
        self.__control = 0.0   # The setting as it was asked for, which toggle inverts
        self.__lit = False
        self.__waiting = True  # Dark until a frame lands, against dark by choice
        self.__shown = []      # The screens asking to reveal together that have drawn
        self.__said = False    # Whether the wait has already explained itself

        # The minimum in the terms the gamma reads, so a setting maps onto it there
        self.__lowest = pow(self.MINIMUM_DUTY, 1.0 / self.GAMMA)

    def brightness(self, value):
        """Set the level and light to it, which also ends any wait for a frame.

        0.0 is off and keeps the level for the next on(), so a caller can use either
        spelling. Everything above it spans MINIMUM_DUTY to full.
        """
        value = min(1.0, max(0.0, value))
        if self.__waiting:
            self.__waiting = False
            self.__shown = []   # Nothing left to count, so the screens are let go

        self.__control = value
        self.__lit = value > 0.0
        if self.__lit:
            self.__level = value

        # Folded into the curve the gamma reads and not into the duty, since that curve
        # is what steps evenly to the eye. Offsetting the duty instead would spend the
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

    def __frame_shown(self, source=None, to=None, keep_dark=False):
        # Note a frame reaching the glass, which is what a dark line waits for. Only from
        # power-on, a line taken dark by off() staying dark until asked for again. source
        # is what was written and to the panels it reached, and with neither the first
        # frame lights the line whatever any screen asked for. keep_dark leaves the line
        # unlit and hands back the scan to spend before __reveal_now(), None saying the
        # line is not ready and nothing is owed.
        if not self.__waiting:
            return None

        if source is not None:
            asked = False
            fresh = False
            for screen in (source.screens if to is None else to):
                if screen.reveal_together:
                    asked = True
                    if screen not in self.__shown:
                        self.__shown.append(screen)
                        fresh = True

            waiting_for = self.__waiting_for()
            if waiting_for:
                # Said once, and only where a frame covered panels already counted, which
                # is a loop not reaching the rest and the one shape a caller cannot see
                if asked and not fresh and not self.__said:
                    self.__said = True
                    logging.info(f"screens: the backlight is waiting for {waiting_for} more"
                                 f" screen{'' if waiting_for == 1 else 's'} to show a frame"
                                 f" before it lights. Update {'it' if waiting_for == 1 else 'them'},"
                                 f" call backlight.on() to light it now, or create the screens"
                                 f" without reveal_together.")
                return None

        if keep_dark:
            return self.__scan_ms

        self.__wait_a_scan()
        self.brightness(self.__level)
        return None

    def __forget_screens(self):
        # Let go of the screens counted so far, their port having released them. The wait
        # itself stays where it is, re-arming it would blink a line already up
        self.__shown = []

    def __waiting_for(self):
        # How many screens asking to reveal together have yet to show a frame
        return sum(1 for screen in self.__port.__screens
                   if screen.backlight is self and screen.reveal_together
                   and screen not in self.__shown)

    @property
    def __scan_ms(self):
        # One full scan of the slowest screen on the port, in milliseconds. A finished
        # transfer is not a presented frame, each row keeping what the scan last painted
        # there until the scan passes again
        slowest = self.__port.__slowest_framerate
        return 0 if slowest is None else 1000 // slowest + 3

    def __reveal_now(self):
        # Light at the held level, for a caller that has already spent the scan
        self.brightness(self.__level)

    def __wait_a_scan(self):
        # Hold for one full scan before the light comes up
        time.sleep_ms(self.__scan_ms)


class SPCEPort:
    """One of a board's SP/CE connectors, built by the board and handed out.

    A screen port hands out its own DC, CS and BL lines through the named
    properties. A port declared SPCE.GPIO hands out all five through io instead, to
    serve as further screens' CS and DC lines.
    """

    # The connector's GPIOs, in the order io reports them
    IO_NAMES = ("dc", "cs", "sck", "mosi", "bl")

    def __init__(self, name, mode, spi, pins):
        if mode not in (None, SPCE.SCREEN, SPCE.MOTOR_DRIVER, SPCE.GPIO, SPCE.HUB_LINES):
            raise ValueError(f"{mode} is not a valid SP/CE mode. Expected SPCE.SCREEN, "
                             "SPCE.MOTOR_DRIVER, SPCE.GPIO, SPCE.HUB_LINES, or None.")

        self.name = name
        self.mode = mode

        # A motor port's pins belong to its Motor objects and an undeclared port is left
        # alone, so neither offers Pins. The numbers stay for motor_pins, which wants them
        self.__pin_numbers = tuple(pins)
        self.__pins = (tuple(Pin(pin) for pin in pins)
                       if mode in (SPCE.SCREEN, SPCE.GPIO, SPCE.HUB_LINES) else None)

        self.driver = None      # The MotorDriver built here, so a board's shutdown can stop it

        # The contract a screen reads by attribute, uniform with a hub's port
        self.__connector = self
        self.__dc_line = self.__pins[0] if self.__pins is not None else None
        self.__default_te = True    # A lone panel reads TE from its own DC line, as MightyFX wires one

        self.__spi = spi        # Kept so the bus can be made again after a release()
        self.__spi_bus = self.__make_bus() if mode == SPCE.SCREEN else None
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
            raise ValueError(f"SP/CE {self.name} is not declared SPCE.GPIO, so its pins "
                             "are not free to borrow")

        return self.__pins

    @property
    def hub_lines(self):
        """The connector's five GPIOs, as the chip selects a hub addresses panels with.

        Only a port declared SPCE.HUB_LINES offers them, the declaration being what says
        the connector is spent on another port's screens.
        """
        if self.mode != SPCE.HUB_LINES:
            raise ValueError(f"SP/CE {self.name} is not declared SPCE.HUB_LINES, so its "
                             "pins are not a hub's chip selects")

        return self.__pins

    @property
    def motor_pins(self):
        """The four data pins as the two motors' pin pairs, then the shared enable.

        Only a port declared SPCE.MOTOR_DRIVER offers them, so spending a connector
        on motors is visible in the call that declared it.
        """
        if self.mode != SPCE.MOTOR_DRIVER:
            raise ValueError(f"SP/CE {self.name} is not declared SPCE.MOTOR_DRIVER, so "
                             "its pins are not a motor driver's")

        numbers = self.__pin_numbers
        return ((numbers[0], numbers[1]), (numbers[2], numbers[3])), numbers[4]

    def __line(self, index):
        if self.mode != SPCE.SCREEN:
            raise ValueError(f"SP/CE {self.name} is not a screen port, so it has no "
                             f"{self.IO_NAMES[index]} line")

        return self.__pins[index]

    # Only a screen port has these. Pass dc or cs to a screen to share that line
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

    def __make_bus(self):
        return SPIDisplayBus(spi=self.__spi, sck=self.__pins[2], mosi=self.__pins[3])

    @property
    def __bus(self):
        # The SPIDisplayBus every screen on this port streams over. Made again where
        # release() gave its DMA channel back, so a port built on a second time takes a
        # fresh channel instead of handing out a dead bus
        if self.mode != SPCE.SCREEN:
            raise ValueError(f"SP/CE {self.name} is not a screen port, so it has no display bus")

        if self.__spi_bus is None:
            self.__spi_bus = self.__make_bus()

        return self.__spi_bus

    @property
    def __slowest_framerate(self):
        # The lowest panel refresh rate on the port, which sets any wait for a frame to
        # reach the glass. None before a screen is built
        if not self.__screens:
            return None

        return min(screen.framerate for screen in self.__screens)

    def __register(self, screen):
        self.__screens.append(screen)

    def __check_cs(self, pin=None):
        # Resolve a screen's CS line and refuse a line already spoken for. None takes the
        # port's own, which is the first screen's to have, and every further screen needs
        # its own, since CS is the only signal selecting one panel
        if pin is None:
            pin = self.cs

        if pin in self.__cs_claimed:
            raise ValueError(f"SP/CE {self.name} already has a screen on {pin}. Every "
                             "further screen on a port needs a cs of its own.")

        return pin

    def __claim_cs(self, pin):
        self.__cs_claimed.append(pin)

    def __check_dc(self, pin=None, te=True, shared=False):
        # Resolve a screen's DC line and refuse a line whose TE it would spoil. None takes
        # the port's own, which is the first screen's to have, and passing this port's dc
        # shares that line deliberately. Panels using TE may share it only where every one
        # names that same line as its te, which declares the diode per breakout that the
        # firmware cannot see and without which no asserted level survives.
        if pin is None:
            pin = self.dc
            if any(claimed is pin for claimed, _, _ in self.__dc_claimed):
                raise ValueError(f"SP/CE {self.name}'s own DC line is taken. Give this "
                                 "screen a dc, or pass the port's dc to share that line.")

        for claimed, claimed_te, claimed_shared in self.__dc_claimed:
            if claimed is not pin:
                continue
            if (te and not shared) or (claimed_te and not claimed_shared):
                raise ValueError(f"{pin} is carrying TE for another screen. Screens "
                                 "sharing a DC line all need te=False, or te set to that "
                                 "line on every one of them, which needs a diode fitted "
                                 "to each breakout.")

        return pin

    def __claim_dc(self, pin, te, shared):
        self.__dc_claimed.append((pin, te, shared))

    def __claim_backlight(self):
        # The port's backlight, created for the first screen to ask for it. The connector
        # carries one BL line, so every screen taking it shares the setting, and where no
        # screen claims it the pin is left alone, free to be a CS or DC
        if self.__backlight is None:
            self.__backlight = Backlight(self, self.bl)

        return self.__backlight

    def backlight_off(self):
        """Take the port's backlight dark, doing nothing where no screen claimed it."""
        if self.__backlight is not None:
            self.__backlight.off()

    def stop_panels(self):
        """Take every panel on this port dark and asleep, each over its own chip select.

        Ahead of release(), a pin handed back being unable to carry a command. A frame
        left staged owns DC, so it is abandoned first, nothing being bound for the glass
        after this anyway.
        """
        for screen in self.__screens:
            screen.__display.abort_frame()
            screen.CONTROLLER.stop(screen.__display)

    def release(self):
        """Hand back the bus's DMA channel and its screens' SRAM claims, and stop
        driving the connector's lines.

        Nothing else gives these up early, and with 16 DMA channels and a PSRAM heap
        that is rarely collected, a program building screens repeatedly runs out and
        the SDK panics. Afterwards this port's screens report rather than transfer, a
        second call does nothing, and the port is free to be built on again, which is
        the case this exists for. Canvases are not given back, the other port's
        screens may still be drawing to them, so shutdown() does that.
        """
        for screen in self.__screens:
            screen.__display.__del__()
        self.__screens.clear()

        # The CS and DC claims name screens that are gone and lines handed back below,
        # so they go too and a port built on again starts from nothing
        self.__cs_claimed.clear()
        self.__dc_claimed.clear()

        # The backlight is holding those screens too. It keeps its level and its lit
        # state, a line that is up staying up rather than blinking over a rebuild
        if self.__backlight is not None:
            self.__backlight.__forget_screens()

        # Dropped as well as deleted, so the next screen on this port is made a fresh
        # bus with a channel of its own
        if self.__spi_bus is not None:
            self.__spi_bus.__del__()
            self.__spi_bus = None

        # A display leaves its chip select and DC driven high, which is right while
        # anything may still transmit and wrong once nothing will. Whatever is plugged in
        # next meets the level these connector pins were left at, and high on a screen's
        # BL lights its backlight or on a motor input drives it, before that thing's own
        # code has run. Pulled down is a cold boot's own state at the pin.
        if self.mode == SPCE.SCREEN:
            handed_back = self.__pins[:4]   # The BL stays, backlight_off() putting it out
        elif self.mode in (SPCE.GPIO, SPCE.HUB_LINES):
            handed_back = self.__pins       # All five, another port's chip selects among them
        else:
            handed_back = ()                # A motor port's belong to its Motor objects

        for pin in handed_back:
            pin.init(Pin.IN, Pin.PULL_DOWN)
