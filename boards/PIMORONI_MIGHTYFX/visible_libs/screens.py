# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# The screens a MightyFX SP/CE port can drive. A screen type is a class carrying
# its panel's settings, so a new size is a subclass setting a few attributes and a
# one-off is a keyword override. PROFILES carries the measured tuning per wire, so
# a construction naming only a baud rate lands on settings profiling chose.
# CONTROLLER names the module supplying the bringup sequence, so the chip stays an
# independent axis from the panel size.

from machine import Pin

import picovector
import spidisplay
import st7789


def __code_for(table, value, what):
    """Look a panel setting up in one of the controller's code tables."""
    try:
        return table[value]
    except KeyError as e:
        items = [str(key) for key in table]
        expected = items[0] if len(items) == 1 else ", ".join(items[:-1]) + f", or {items[-1]}"
        raise ValueError(f"{value} is not a valid {what}. Expected {expected}.") from e


class ScreenMux:
    """Panels addressed by index through switched CS, and optionally DC, lines.

    select is the GPIOs driving the switch, least significant first, so three lines
    reach eight channels. count defaults to all of them, and is worth setting when
    fewer are wired.

    switch_dc needs an analog mux, since TE travels back along that line, and is
    what makes v_sync available. With CS alone switched a plain decoder serves, but
    DC stays shared and v_sync does not.
    """

    def __init__(self, select, switch_dc=False, count=None):
        self.__select = tuple(select)
        if not self.__select:
            raise ValueError("a selector needs at least one select line")

        for pin in self.__select:
            pin.init(Pin.OUT, value=False)

        self.__switch_dc = switch_dc

        channels = 1 << len(self.__select)
        if count is None:
            count = channels
        elif not 1 <= count <= channels:
            raise ValueError(f"{len(self.__select)} select lines address 1 to {channels} channels, not {count}.")

        self.__count = count
        self.__channel = None

    @property
    def count(self):
        return self.__count

    @property
    def switch_dc(self):
        return self.__switch_dc

    def select_channel(self, index):
        """Point the switch at one channel, which holds until the next call."""
        if not 0 <= index < self.__count:
            raise ValueError(f"{index} is not a valid channel. Expected 0 to {self.__count - 1}.")

        if index != self.__channel:
            for bit, pin in enumerate(self.__select):
                pin.value((index >> bit) & 1)
            self.__channel = index


class ScreenBase:
    """The frame path shared by a single screen and a broadcast group.

    te says whether the panel drives its tearing-effect line at all, and v_sync
    whether a frame waits on it by default. members is the screens a broadcast
    group stands for, and None for a screen standing for itself.

    Not built directly: construct a Screen subclass, or ask a port to broadcast().
    """

    def __init__(self, port, display, width, height, bitdepth, backlight, te, v_sync, index, members=None):
        self.__port = port
        self.__display = display
        self.__width = width
        self.__height = height
        self.__bitdepth = bitdepth
        self.__backlight = backlight
        self.__te = te
        self.__v_sync = v_sync
        self.__index = index
        self.__members = members

    @property
    def port(self):
        return self.__port

    @property
    def display(self):
        """The spidisplay.SPIDisplay a frame streams over, for its diagnostics."""
        return self.__display

    @property
    def backlight(self):
        return self.__backlight

    @property
    def screens(self):
        """The screens a broadcast group stands for, or just this one."""
        return self.__members if self.__members is not None else (self,)

    @property
    def width(self):
        return self.__width

    @property
    def height(self):
        return self.__height

    @property
    def bitdepth(self):
        return self.__bitdepth

    @property
    def v_sync(self):
        """Whether a frame waits on the tearing-effect signal unless told otherwise."""
        return self.__v_sync

    @property
    def brightness(self):
        """How bright the backlight looks, from 0.0 to 1.0.

        Against perceived brightness, so equal steps look equal. The lowest
        settings are dark, the backlight driver having a floor of its own.
        """
        if self.__backlight is None:
            raise ValueError("this screen has no backlight to set, so its brightness is whatever the assembly ties it to")

        return self.__backlight.brightness

    @brightness.setter
    def brightness(self, value):
        if self.__backlight is None:
            raise ValueError("this screen has no backlight to set, so its brightness is whatever the assembly ties it to")

        self.__backlight.brightness = value

    def canvas(self, offset=0):
        """An SRAM-backed image sized to this screen.

        The GC heap is PSRAM, so a plain image() is read over XIP and costs about
        twice as much per pixel to convert. offset places the canvas within the SRAM
        region, for a second buffer that has to coexist with the first.
        """
        nbytes = self.__width * self.__height * 4    # RGBA8888
        return picovector.image(self.__width, self.__height,
                                spidisplay.buffer(nbytes, offset))

    def drawn(self):
        """Note that a frame has landed, which the backlight waits for."""
        if self.__members is not None:
            for screen in self.__members:
                screen.drawn()

        elif self.__backlight is not None:
            self.__backlight.__first_frame(self)

    def __select(self):
        if self.__index is not None:
            self.__port.selector.select_channel(self.__index)

    def command(self, command, data=None):
        self.__select()
        self.__display.command(command, data)

    @micropython.native
    def update(self, image, rotation=0, mirror=False, v_sync=None, bg_color=picovector.color.black, pixel_double=False, offset=None):
        # v_sync=None follows the screen, so only a frame that differs says so
        if v_sync is None:
            v_sync = self.__v_sync
        elif v_sync and not self.__te:
            if self.__members is not None:
                raise ValueError("a broadcast group cannot v_sync: its panels' scans are unsynchronised, so no edge is safe for all of them")

            raise ValueError("v_sync needs a screen created with te, since it waits on the panel's tearing-effect signal")

        bg = bg_color.p & 0xffffffff

        r_index = rotation // 90
        if r_index < 0 or r_index > 3 or rotation % 90:     # Modulo check ensures rotation is exactly a multipe of 90
            raise ValueError(f"{rotation} is not a valid angle. Expected 0, 90, 180, or 270.")

        self.__select()

        # The C module handles the transform, transfer, and TE wait
        self.__display.update(image,
                              rotation=rotation,
                              mirror=1 if mirror else 0,
                              pixel_double=1 if pixel_double else 0,
                              bg=bg, offset=offset, v_sync=v_sync)
        self.drawn()


class Screen(ScreenBase):
    """One panel on an SP/CE port.

    The first screen on a port names no pins and takes the port's own DC, CS and
    backlight. Every further screen names its cs, and its dc unless it is
    deliberately sharing the port's, which only panels with te=False may do. With a
    selector set on the port the screens name no pins and take a channel each, in
    creation order.

    te reads the tearing-effect signal from the shared DC line, which is how
    MightyFX wires it; pass a Pin for a dedicated input, or False to send TEOFF.
    v_sync follows te, and False keeps the signal without waiting on it. bl=False
    declines the port's backlight, for a panel whose own is tied on at the assembly.

    Settings resolve as: explicit keyword, then the PROFILES row for the
    (baudrate, bitdepth) pair, then the class constants. With no bitdepth named,
    the first depth in DEPTHS that has a row for the baud wins, so higher rates
    default to 16-bit colour and bitdepth=12 buys their last few frames per
    second. Every resolved value is validated against the controller's tables, so
    a bad experiment fails where the mistake is.

    band_lines and cache_columns spend SRAM from the same region canvases come
    from: at least two band buffers plus cache_columns * width * 4 bytes, claimed
    for as long as the screen lives and reported by display.sram_bytes().
    stage_lines deepens the band buffers into a ring of that many rows, which
    prepare() converts up front so the wire starts with that much of a head
    start. About 80 rows keeps two update_all() screens wire-bound from a PSRAM
    source at rotation 0; the rotation 90 pair needs stage_lines=160 with
    cache_columns=12, measured wire-bound at 70KB claimed per screen.
    """

    CONTROLLER = st7789      # bringup, framerate and bitdepth code tables, RAMWR
    WIDTH = HEIGHT = None
    BITDEPTH = 16
    FRAMERATE = 60
    BAUDRATE = 24_000_000
    BAND_LINES = 12          # With CACHE_COLUMNS, the fallback tuning for a wire
    CACHE_COLUMNS = 12       # PROFILES does not cover: the measured sweet spot
    DEPTHS = (16, 12)        # Default bit depth preference, first row wins

    # Measured tuning per (baudrate, bitdepth), from the 21,600-cell sweep in
    # .claude/results/ANALYSIS.md "Full PSRAM rerun": the band and cache holding
    # the rotation-90 floor, and the highest controller rate that floor sustains
    # (capped at the useful 60fps).
    PROFILES = {}

    def __init__(self, port, cs=None, dc=None, te=True, v_sync=None, bl=True,
                 width=None, height=None, bitdepth=None, framerate=None,
                 baudrate=None, band_lines=None, cache_columns=None,
                 stage_lines=0):

        width = self.WIDTH if width is None else width
        height = self.HEIGHT if height is None else height
        self.__baudrate = self.BAUDRATE if baudrate is None else baudrate

        if bitdepth is None:
            for depth in self.DEPTHS:
                if (self.__baudrate, depth) in self.PROFILES:
                    bitdepth = depth
                    break
            else:
                bitdepth = self.BITDEPTH

        # Off-table pairs fall back to the class constants, since profiling a new
        # panel or wire has to be able to construct anything.
        profile = self.PROFILES.get((self.__baudrate, bitdepth))
        if profile is None:
            profile = {"band_lines": self.BAND_LINES,
                       "cache_columns": self.CACHE_COLUMNS,
                       "framerate": self.FRAMERATE}

        band_lines = profile["band_lines"] if band_lines is None else band_lines
        cache_columns = profile["cache_columns"] if cache_columns is None else cache_columns
        self.__framerate = profile["framerate"] if framerate is None else framerate

        if width is None or height is None:
            raise ValueError(f"{type(self).__name__} sets no WIDTH and HEIGHT. Subclass Screen and set them, or pass them here.")

        controller = self.CONTROLLER
        bd_code = __code_for(controller.PIXEL_FORMAT, bitdepth, "bit depth")
        fr_code = __code_for(controller.FRAME_RATE_CONTROL, self.__framerate, "frame rate")

        te_used = te is not False
        te_pin = None if isinstance(te, bool) else te

        if v_sync is None:
            v_sync = te_used
        elif v_sync and not te_used:
            raise ValueError("v_sync waits on the panel's tearing-effect signal, which te=False turns off")

        selector = port.selector
        if selector is not None:
            if cs is not None or dc is not None:
                raise ValueError("a selector addresses screens by index, so name no cs or dc")

            if te_used and not selector.switch_dc:
                raise ValueError("a selector that leaves DC shared cannot carry TE, so its screens need te=False")

            index = port.__next_index()
        else:
            index = None

        cs = port.__claim_cs(cs)
        dc = port.__claim_dc(dc, te_used)

        backlight = None
        if bl:
            backlight = port.__claim_backlight()
            backlight.__register(self)

        display = spidisplay.SPIDisplay(bus=port.bus, cs=cs, dc=dc, te=te_pin,
                                        width=width, height=height,
                                        ram_write=controller.RAM_WRITE,
                                        bitdepth=bitdepth, baudrate=self.__baudrate,
                                        band_lines=band_lines, cache_columns=cache_columns,
                                        stage_lines=stage_lines)

        # The divider only reaches clk_peri/(2*n), so a request above what the
        # clock affords comes back rounded down and the profile's tuning would
        # drive a slower wire than it was measured on. Refuse rather than let a
        # 37.5MHz row quietly run at 24.
        achieved = display.baudrate()
        if achieved < self.__baudrate:
            raise ValueError(f"this wire reached {achieved} baud of the {self.__baudrate} requested."
                             f" Raise clk_peri first, machine.freq(150_000_000, 150_000_000),"
                             f" or request a rate the current clock reaches.")

        super().__init__(port, display, width, height, bitdepth, backlight, te_used, v_sync, index)

        port.__register(self)

        # Bringup goes through this screen's command(), so a selector is pointed at
        # the panel for every register write as well as every frame
        controller.setup(self, width, height, bd_code, fr_code, te_used)

    @property
    def framerate(self):
        """The panel's own refresh rate, which bounds the tearing margin."""
        return self.__framerate

    @property
    def requested_baudrate(self):
        """The rate this panel asked for, against display.baudrate()'s achieved one."""
        return self.__baudrate

    def group_with(self, *screens):
        """A broadcast group over this screen and the others named."""
        return Broadcast((self,) + screens)


class Screen154(Screen):
    WIDTH, HEIGHT = 240, 240
    # No 16-bit row at 24MHz: that frame outruns the controller's 39fps floor.
    # This panel shows 240 of the controller's ~320 scan lines, so its tear
    # budget is about 1.75 refreshes, not 2: at 24MHz the frame fits under
    # 55.5fps, and 53 is the step below the visually confirmed onset at 55.
    # No 12-bit row at 75MHz: that wire outruns the panel's scan during each
    # cache window's run of rows, so the write overtakes the beam near the top
    # of the frame and no band or cache choice avoids it.
    PROFILES = {
        (24_000_000, 12): {"band_lines": 2, "cache_columns": 0, "framerate": 53},
        (37_500_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 60},
        (37_500_000, 12): {"band_lines": 12, "cache_columns": 12, "framerate": 60},
        (75_000_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 60},
    }


class Screen280(Screen):
    WIDTH, HEIGHT = 240, 320
    # No 12-bit row at 75MHz, for the same beam-overtake reason as the 1.54"
    # The 24MHz rate is 45, not the 46 the two-refresh budget nominally allows:
    # panel oscillators run the set rate fast by up to ~1.5% (one measured unit
    # scanned 46.35fps at setting 46, leaving 1.1ms of margin and a marginal
    # tear), and the step down restores ~2ms of margin on a fast unit.
    PROFILES = {
        (24_000_000, 12): {"band_lines": 4, "cache_columns": 4, "framerate": 45},
        (37_500_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 52},
        (37_500_000, 12): {"band_lines": 12, "cache_columns": 12, "framerate": 55},
        (75_000_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 53},
    }


class Broadcast(ScreenBase):
    """Several of a port's screens driven as one, sharing a frame.

    One stream reaches every member, so a wall of panels renders in the time one of
    them takes. The members keep their identity, so each can still be brought up and
    updated on its own, which is what lets a group carry differing MADCTL.

    Built by a port's broadcast(), and only over panels agreeing on bit depth,
    dimensions, rate and tuning. Those are copied once, so a member that later
    re-rates itself moves only itself.
    """

    def __init__(self, screens):
        if len(screens) < 2:
            raise ValueError("a broadcast group needs at least two screens")

        port = screens[0].port
        if port.selector is not None:
            raise ValueError("a selector reaches one screen at a time, so a port with one cannot broadcast")

        for screen in screens:
            if screen.port is not port:
                raise ValueError("a broadcast group has to be on one port, since two ports are two streams")

        first = screens[0]
        display = port.bus.broadcast(*[screen.display for screen in screens])

        # The backlight is the first member's, since screens on a port share the one
        # PWM. TE is never available, the members' scans being unsynchronised.
        super().__init__(port, display, first.width, first.height, first.bitdepth,
                         first.backlight, False, False, None, members=tuple(screens))
