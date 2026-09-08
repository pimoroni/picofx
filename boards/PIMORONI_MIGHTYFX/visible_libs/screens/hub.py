# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Several panels sharing one SP/CE port's bus, each selected by a chip select of its
# own. The hub deasserts every chip select before the first panel is brought up,
# which no screen can do for the panels that have no object yet.

import spidisplay
import st7789
from machine import Pin


class ScreenHubPort:
    """One panel's place on a hub, answering a screen's construction calls as the connector would."""

    def __init__(self, connector, cs, dc, te):
        self.__connector = connector
        self.__cs = cs
        self.__dc_line = dc
        self.__default_te = te

    @property
    def __bus(self):
        return self.__connector.__bus

    @property
    def __panels_reset(self):
        return self.__connector.__panels_reset

    def __check_cs(self, pin=None):
        return self.__connector.__check_cs(self.__cs if pin is None else pin)

    def __claim_cs(self, pin):
        self.__connector.__claim_cs(pin)

    def __check_dc(self, pin=None, te=True, shared=False):
        return self.__connector.__check_dc(self.__dc_line if pin is None else pin, te, shared)

    def __claim_dc(self, pin, te, shared):
        self.__connector.__claim_dc(pin, te, shared)

    def __claim_backlight(self):
        return self.__connector.__claim_backlight()

    def __register(self, screen):
        self.__connector.__register(screen)


class ScreenHub:
    """Several panels on one SP/CE port, each addressed by a chip select of its own."""

    # What the bringup pass runs at, every screen writing its own settings over these
    BLIND_BAUDRATE = 24_000_000
    BLIND_BITDEPTH = 12
    BLIND_FRAMERATE = 60
    BLIND_BAND_LINES = 2

    def __init__(self, port, extra_cs=(), dc=None, te=None, controller=st7789):
        if port.__screens:
            raise ValueError(f"SP/CE {port.name} already has screens, and a hub has to reach every "
                             "panel before the first one is built, so build it first")

        self.__connector = port
        self.__controller = controller

        # port.cs raises where the connector is not a screen port
        lines = [port.cs]
        for pin in extra_cs:
            pin = pin if isinstance(pin, Pin) else Pin(pin)
            if pin in lines:
                raise ValueError(f"{pin} is named twice, and each panel on a hub needs a "
                                 "chip select of its own")
            lines.append(pin)

        dc = port.dc if dc is None else dc
        te = dc if te is None else te

        # Every line high before any panel is spoken to. A panel with no display yet
        # reads its floating chip select as asserted and takes another's bringup
        for line in lines:
            line.init(Pin.OUT, value=True)

        self.__ports = tuple(ScreenHubPort(port, line, dc, te) for line in lines)
        self.__bring_panels_up(lines, dc)
        port.__panels_reset = True

    @property
    def ports(self):
        """One port per chip select in the order named, hub.a being ports[0] and so on."""
        return self.__ports

    def __getattr__(self, name):
        # One letter a port, so a hub of any size letters every port it reaches
        if len(name) == 1 and "a" <= name <= "z":
            index = ord(name) - ord("a")
            if index < len(self.__ports):
                return self.__ports[index]
            raise ValueError(f"this hub reaches {len(self.__ports)} panels, so there is no port {name}")
        raise AttributeError(name)

    def __bring_panels_up(self, lines, dc):
        # One broadcast resets and clears every panel at once, so the reset settle is
        # paid once. The window is the controller's whole memory, so one clear covers
        # every panel size that can be on the port.
        controller = self.__controller
        columns, rows = controller.CONTROLLER_COLUMNS, controller.CONTROLLER_ROWS

        # Temporary displays carrying the chip select masks and the smallest workspace
        displays = [spidisplay.SPIDisplay(bus=self.__connector.__bus, cs=line, dc=dc, te=None,
                                          width=columns, height=rows,
                                          ram_write=controller.RAM_WRITE,
                                          te_on=controller.TE_ON, te_off=controller.TE_OFF,
                                          te_mode=controller.TE_MODE,
                                          bitdepth=self.BLIND_BITDEPTH,
                                          baudrate=self.BLIND_BAUDRATE,
                                          band_lines=self.BLIND_BAND_LINES,
                                          cache_columns=0, stage_lines=0)
                    for line in lines]
        try:
            # A hub of one is a plain screen port, and a broadcast of one is refused
            every_panel = displays[0] if len(displays) == 1 else self.__connector.__bus.broadcast(*displays)
            controller.reset(every_panel)
            controller.setup(every_panel, columns, rows,
                             controller.PIXEL_FORMAT[self.BLIND_BITDEPTH],
                             controller.FRAME_RATE_CONTROL[self.BLIND_FRAMERATE],
                             te=False)
            every_panel.fill()
        finally:
            # The destructor leaves each chip select an output driven high
            for display in displays:
                display.__del__()
