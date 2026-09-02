# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Several panels sharing one SP/CE port's bus, each selected by a chip select of its
# own. The hub owns an ordering no screen can reach: every chip select has to be
# deasserted before the first panel is brought up, and the panels at risk are the
# ones with no object yet to speak for them.

import spidisplay
import st7789
from machine import Pin


class ScreenHubPort:
    """One panel's place on a hub: its own chip select, and the lines the hub shares.

    Handed to a screen in place of the connector, and answers the same construction
    calls. Anything that is not per-panel comes from the connector itself, so a
    screen built here is registered, backlit and released exactly as any other.
    """

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
    """Several panels on one SP/CE port, each addressed by a chip select of its own.

    ports[0] is the connector's own chip select and the rest follow extra_cs in the
    order given, so a screen is built against a port here exactly as it would be
    against the connector alone.

    te names the line the tearing-effect signal comes back on, and defaults to the
    shared DC line. That declares a diode on every breakout, which blocks each
    panel's TEOFF from pulling the line down; without them the panels divide it and
    no asserted level survives, so a build without diodes passes te=False. The
    firmware cannot see a diode, so the declaration is the caller's.

    Every panel the hub reaches is reset and cleared as the hub is built, whether a
    screen is created for it afterwards or not. A panel holds its last frame across
    a soft reset, so one the program leaves out would otherwise light showing the
    previous run.
    """

    # What the blind pass runs at. Nothing here reaches a shipped frame: every screen
    # writes its own depth, rate and window over these as it is built, and the panel
    # is cleared before that. The rate is the one every wire holds.
    BLIND_BAUDRATE = 24_000_000
    BLIND_BITDEPTH = 12
    BLIND_FRAMERATE = 60
    BLIND_BAND_LINES = 2

    def __init__(self, port, extra_cs=(), dc=None, te=None, controller=st7789):
        if port.__screens:
            raise ValueError(f"SP/CE {port.name} already has screens, and a hub has to reach every panel before the first one is built, so build it first")

        self.__connector = port
        self.__controller = controller

        # port.cs raises where the connector is not a screen port, which is the
        # refusal a hub wants anyway
        lines = [port.cs]
        for pin in extra_cs:
            pin = pin if isinstance(pin, Pin) else Pin(pin)
            if pin in lines:
                raise ValueError(f"{pin} is named twice, and each panel on a hub needs a chip select of its own")
            lines.append(pin)

        dc = port.dc if dc is None else dc
        te = dc if te is None else te

        # Every line high before any panel is spoken to. A display drives its own
        # chip select high, but not until it is constructed, so a panel with no
        # object yet reads its floating line as asserted and takes the bringup meant
        # for the panels ahead of it.
        for line in lines:
            line.init(Pin.OUT, value=True)

        self.__ports = tuple(ScreenHubPort(port, line, dc, te) for line in lines)
        self.__bring_panels_up(lines, dc)
        port.__panels_reset = True

    @property
    def ports(self):
        """One port per chip select the hub reaches, in the order they were named.

        Lettered as well as ordered: hub.a is ports[0] and each chip select takes
        the next letter, matching the lettering on the hub itself.
        """
        return self.__ports

    def __getattr__(self, name):
        # One letter a port, derived from the chip selects rather than fixed at
        # six, so a hub of any size letters every port it reaches and no more.
        if len(name) == 1 and "a" <= name <= "z":
            index = ord(name) - ord("a")
            if index < len(self.__ports):
                return self.__ports[index]
            raise ValueError(f"this hub reaches {len(self.__ports)} panels, so there is no port {name}")
        raise AttributeError(name)

    def __bring_panels_up(self, lines, dc):
        """Reset and clear every panel the hub reaches, in one pass over all of them.

        A display carries a mask of chip selects rather than a pin, so a broadcast
        writes every panel at once and the controller's reset settle is paid once
        instead of per panel. The window is the controller's whole memory, which is
        the same size whatever the glass shows, so one clear covers every panel size
        that can be on the port.
        """
        controller = self.__controller
        columns, rows = controller.CONTROLLER_COLUMNS, controller.CONTROLLER_ROWS

        # Thrown away at the end of this: they exist to carry the chip select masks
        # and the smallest workspace a frame can be streamed from, and each screen
        # claims its own measured one afterwards.
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
            # A hub of one is a plain screen port, which is what a board reaches with
            # nothing plugged into its second connector, and a group of one is refused
            every_panel = displays[0] if len(displays) == 1 else self.__connector.__bus.broadcast(*displays)
            controller.reset(every_panel)
            controller.setup(every_panel, columns, rows,
                             controller.PIXEL_FORMAT[self.BLIND_BITDEPTH],
                             controller.FRAME_RATE_CONTROL[self.BLIND_FRAMERATE],
                             te=False)
            every_panel.fill()
        finally:
            # The destructor leaves each chip select an output driven high, so the
            # deassert above outlives the displays that carried it.
            for display in displays:
                display.__del__()
