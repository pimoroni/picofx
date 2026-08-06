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

import logging
import time

from machine import Pin

import picovector
import spidisplay
import st7789


def update_pair(first, second, v_sync=None):
    """Stream a frame to two screens at once, each starting on its own TE edge.

    Both screens must have prepare()d a frame, sit on different SP/CE ports since
    one port is one stream, and agree on reserve. Presenting a pair this way takes
    about the time one of them alone would, instead of the two in turn, and the
    panels change together.

    v_sync=None waits on the tearing-effect signal when both screens were built
    for it.
    """
    if first is second:
        raise ValueError("update_pair needs two different screens")
    if first.port is second.port:
        raise ValueError("update_pair needs a screen on each SP/CE port, since one port is one stream; broadcast() shares a port")
    # One reservation is shared out across the pair, so it leaves both screens short
    # rather than protecting the one that made it.
    if first.reserve != second.reserve:
        raise ValueError("update_pair needs both screens built with the same reserve, since a reservation is shared out across the pair: set it on both, or on neither")

    if v_sync is None:
        v_sync = first.v_sync and second.v_sync
    elif v_sync and not (first.v_sync and second.v_sync):
        raise ValueError("v_sync needs both screens created with te, since each waits on its own panel's tearing-effect signal")

    spidisplay.update_all(first.display, second.display, v_sync=v_sync)
    first.drawn()
    second.drawn()


def __code_for(table, value, what):
    """Look a panel setting up in one of the controller's code tables."""
    try:
        return table[value]
    except KeyError as e:
        items = [str(key) for key in table]
        expected = items[0] if len(items) == 1 else ", ".join(items[:-1]) + f", or {items[-1]}"
        raise ValueError(f"{value} is not a valid {what}. Expected {expected}.") from e


def __for_cores(row, dual, required, what):
    """A PROFILES or FULL_IMAGE_RESERVE row, taking its dual-core override if any.

    A row's "dual" entry is the whole row again for a firmware that converts on
    both cores, not the settings that differ from the single-core ones. So reading
    one states its configuration outright, and changing a single-core value cannot
    move the other case by accident. A row without one is used for both.
    """
    if not dual or "dual" not in row:
        return row

    override = row["dual"]
    missing = [key for key in required if key not in override]
    if missing:
        raise ValueError(f"the dual-core {what} row names {', '.join(missing)} nowhere. It replaces the single-core row rather than amending it, so it needs every setting that row has.")

    return override


def __pair_values(value, name):
    """One value for both screens, or a 2-tuple giving one each."""
    if isinstance(value, (tuple, list)):
        if len(value) != 2:
            raise ValueError(f"a per-screen {name} is two values, one for each screen, not {len(value)}")
        return value
    return (value, value)


def __pair_offsets(offset):
    """offset resolved to one (x, y) or None per screen.

    Shared unless either element is itself a pair, offset being an (x, y) pair
    already. Every shape that is neither form is rejected, since the two
    readings differ silently: (5, None) is the one quiet case, and only because
    both readings mean the same frame.
    """
    if offset is None:
        return (None, None)
    if not isinstance(offset, (tuple, list)) or len(offset) != 2:
        raise ValueError("offset is (x, y) for both screens, or two of them for one screen each")

    if any(isinstance(element, (tuple, list)) for element in offset):
        # Per screen: each element an (x, y) pair, or None for centred
        for element in offset:
            if element is None:
                continue
            if not isinstance(element, (tuple, list)) or len(element) != 2:
                raise ValueError(f"{offset} reads as a per-screen offset, so each element is an (x, y) pair or None; a shared offset is (x, y) with plain coordinates")
            for coordinate in element:
                if coordinate is not None and not isinstance(coordinate, int):
                    raise ValueError(f"{element} is not an (x, y) pair: each coordinate is a number, or None for centred on that axis")
        return offset

    # Shared: one (x, y) applied to both screens
    for coordinate in offset:
        if coordinate is not None and not isinstance(coordinate, int):
            raise ValueError(f"{offset} is not an (x, y) pair: each coordinate is a number, or None for centred on that axis. A per-screen offset is two such pairs.")
    return (offset, offset)


def __fold(delta, period):
    """Signed fold of a difference into half a period."""
    d = delta % period
    if d > period // 2:
        d -= period
    return d


def __signed_mod(delta, period):
    """Signed difference between two of the C module's 32-bit microsecond stamps.

    The difference folds to signed 32 bits before the period reduction: 2**32 is
    not a multiple of a TE period, so reducing an unsigned wrap biases every
    negative skew by (2**32 % period), 130-odd lines at these rates.
    """
    return __fold(((delta + 0x80000000) & 0xFFFFFFFF) - 0x80000000, period)


class Reserve:
    """What a screen sets its share of the fast SRAM aside for.

    CANVAS_SPACE claims only what a frame needs, leaving the region for canvas().
    FULL_SIZE_IMAGES claims enough for two screens to each convert their own
    full-size image out of the GC heap at once, which is the one case that cannot
    keep up otherwise; a full-size canvas no longer fits alongside it, half-size
    ones still do. Drawing to canvas(), or halving an image and passing
    pixel_double, needs neither.

    It buys a frame that does not tear, not a faster one: the conversion moves into
    prepare(), ahead of the frame, so the wire never starves but the pair takes
    longer to come round. Measured on a 240x240 pair, 61ms a pair against 54ms
    untorn at rotation 0, and 76ms against 66ms at rotation 90.

    Both screens of a pair need the same value, which update_pair() checks: a
    reservation is shared out across the pair, so one on its own leaves both short
    rather than protecting the screen that made it.

    FULL_SIZE_IMAGES is only available where a screen type has measured a recipe for
    the wire, in its FULL_IMAGE_RESERVE, and refuses elsewhere rather than guessing.
    """
    CANVAS_SPACE = 0
    FULL_SIZE_IMAGES = 1


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

    def __init__(self, port, display, width, height, bitdepth, backlight, te, v_sync, index, reserve, members=None):
        self.__port = port
        self.__display = display
        self.__width = width
        self.__height = height
        self.__bitdepth = bitdepth
        self.__backlight = backlight
        self.__te = te
        self.__v_sync = v_sync
        self.__index = index
        self.__reserve = reserve
        self.__members = members
        self.__canvases = {}
        self.__pair = None      # The ScreenPair holding panel state on this screen

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
    def reserve(self):
        """What this screen's share of the fast SRAM was set aside for."""
        return self.__reserve

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

    def canvas(self, width=None, height=None, offset=None):
        """An SRAM-backed image, by default sized to this screen.

        The GC heap is PSRAM, so a plain image() is read over XIP and costs about
        twice as much per pixel to convert. Each size is claimed once from this
        screen's own part of the region and handed back on every later call, so two
        screens never share pixels.

        Half the panel's width and height, drawn with pixel_double=True, is a
        quarter of the bytes: two screens can hold one each where one full-size
        canvas already fills the region. offset places a canvas by hand instead,
        outside the claims.
        """
        width = self.__width if width is None else width
        height = self.__height if height is None else height
        if width < 1 or height < 1:
            raise ValueError("a canvas needs a positive width and height")

        nbytes = width * height * 4    # RGBA8888
        if offset is not None:
            return picovector.image(width, height, spidisplay.buffer(nbytes, offset))

        canvas = self.__canvases.get((width, height))
        if canvas is None:
            canvas = picovector.image(width, height, spidisplay.buffer(nbytes))
            self.__canvases[(width, height)] = canvas

        return canvas

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

    def __check_rotation(self, rotation):
        r_index = rotation // 90
        if r_index < 0 or r_index > 3 or rotation % 90:     # Modulo check ensures rotation is exactly a multipe of 90
            raise ValueError(f"{rotation} is not a valid angle. Expected 0, 90, 180, or 270.")

    @micropython.native
    def update(self, image, rotation=0, mirror=False, v_sync=None, bg_color=picovector.color.black, pixel_double=False, offset=None):
        # A frame outside the pair first hands back the panel state alignment
        # holds, since the narrowed TE pulse is only safe under the pair's poll
        if self.__pair is not None:
            self.__pair.__restore_panel()

        # v_sync=None follows the screen, so only a frame that differs says so
        if v_sync is None:
            v_sync = self.__v_sync
        elif v_sync and not self.__te:
            if self.__members is not None:
                raise ValueError("a broadcast group cannot v_sync: its panels' scans are unsynchronised, so no edge is safe for all of them")

            raise ValueError("v_sync needs a screen created with te, since it waits on the panel's tearing-effect signal")

        bg = bg_color.p & 0xffffffff

        self.__check_rotation(rotation)
        self.__select()

        # The C module handles the transform, transfer, and TE wait
        self.__display.update(image,
                              rotation=rotation,
                              mirror=1 if mirror else 0,
                              pixel_double=1 if pixel_double else 0,
                              bg=bg, offset=offset, v_sync=v_sync)
        self.drawn()

    @micropython.native
    def prepare(self, image, rotation=0, mirror=False, bg_color=picovector.color.black, pixel_double=False, offset=None):
        """Stage a frame for update_pair(), converting as far ahead as it can.

        Placement is per screen, so a pair can differ in rotation, mirroring and
        offset to suit how each panel is mounted. Nothing reaches the panel until
        update_pair() runs, and a staged frame refuses command() until it does.
        """
        bg = bg_color.p & 0xffffffff

        self.__check_rotation(rotation)
        self.__select()

        self.__display.prepare(image,
                               rotation=rotation,
                               mirror=1 if mirror else 0,
                               pixel_double=1 if pixel_double else 0,
                               bg=bg, offset=offset)


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

    A row's "dual" entry, where it has one, replaces it on a firmware that converts
    frames on both cores, some wires reaching a higher rate once one core is no
    longer what the wire waits for. dual_profiles=True or False chooses that set by
    hand, for measuring one against the other; by default the firmware decides, and
    a build without a second core to convert on never sees the dual rows. Turning
    spidisplay.dual_convert() off after a screen is built leaves it holding a rate
    chosen for two cores, so that setting is for diagnostics.

    reserve says what the screen's share of the fast SRAM is for, and is the setting
    to reach for rather than the three below: Reserve.FULL_SIZE_IMAGES buys the one
    case that cannot keep up otherwise, two screens each converting their own
    full-size image out of the GC heap through update_pair().

    band_lines and cache_columns spend SRAM from the same region canvases come
    from: at least two band buffers plus cache_columns * width * 4 bytes, claimed
    for as long as the screen lives and reported by display.sram_bytes().
    stage_lines deepens the band buffers into a ring of that many rows, which
    prepare() converts up front so the wire starts with that much of a head start.
    Any of the three overrides what reserve chose, for profiling a new panel or
    wire.
    """

    CONTROLLER = st7789      # bringup, framerate and bitdepth code tables, RAMWR
    WIDTH = HEIGHT = None
    BITDEPTH = 16
    FRAMERATE = 60
    BAUDRATE = 24_000_000
    BAND_LINES = 12          # With CACHE_COLUMNS, the fallback tuning for a wire
    CACHE_COLUMNS = 12       # PROFILES does not cover: the measured sweet spot
    DEPTHS = (16, 12)        # Default bit depth preference, first row wins

    # What Reserve.FULL_SIZE_IMAGES asks for, per (baudrate, bitdepth) as PROFILES
    # is: the shallowest ring measured to hold a pair wire-bound while both convert
    # a full-size heap image, and the cache width that ring needs. A wire with no
    # row here refuses the reserve rather than guessing, since the sums move with
    # the wire: a faster one shortens the row the conversion has to keep up with,
    # so a deeper ring is not always the answer.
    FULL_IMAGE_RESERVE = {}

    # Measured tuning per (baudrate, bitdepth), from the 21,600-cell sweep in
    # .claude/results/ANALYSIS.md "Full PSRAM rerun": the band and cache holding
    # the rotation-90 floor, and the highest controller rate that floor sustains
    # (capped at the useful 60fps). A row may carry a "dual" replacement for a
    # firmware converting on both cores, which is a rate its wire could not hold
    # while one core was what it waited for.
    PROFILES = {}

    def __init__(self, port, cs=None, dc=None, te=True, v_sync=None, bl=True,
                 width=None, height=None, bitdepth=None, framerate=None,
                 baudrate=None, reserve=Reserve.CANVAS_SPACE, band_lines=None,
                 cache_columns=None, stage_lines=None, dual_profiles=None):

        width = self.WIDTH if width is None else width
        height = self.HEIGHT if height is None else height
        self.__baudrate = self.BAUDRATE if baudrate is None else baudrate

        # Which set of measured settings this wire gets. The firmware answers it:
        # dual_convert() is off in any build without a second core to convert on.
        if dual_profiles is None:
            dual_profiles = spidisplay.dual_convert()

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
        else:
            profile = __for_cores(profile, dual_profiles,
                                  ("band_lines", "cache_columns", "framerate"),
                                  "PROFILES")

        # reserve picks the measured recipe; a named band, cache or stage still wins,
        # so a profiling run can construct anything.
        if reserve == Reserve.FULL_SIZE_IMAGES:
            recipe = self.FULL_IMAGE_RESERVE.get((self.__baudrate, bitdepth))
            if recipe is None:
                raise ValueError(f"Reserve.FULL_SIZE_IMAGES has no measured recipe for {type(self).__name__} at {self.__baudrate}Hz {bitdepth}-bit. Measure one, or name stage_lines and cache_columns.")

            recipe = __for_cores(recipe, dual_profiles,
                                 ("stage_lines", "cache_columns"),
                                 "FULL_IMAGE_RESERVE")

            if stage_lines is None:
                stage_lines = recipe["stage_lines"]
            if cache_columns is None:
                cache_columns = recipe["cache_columns"]
        elif reserve != Reserve.CANVAS_SPACE:
            raise ValueError(f"{reserve} is not a valid reserve. Expected Reserve.CANVAS_SPACE, or Reserve.FULL_SIZE_IMAGES.")

        band_lines = profile["band_lines"] if band_lines is None else band_lines
        cache_columns = profile["cache_columns"] if cache_columns is None else cache_columns
        self.__framerate = profile["framerate"] if framerate is None else framerate
        stage_lines = 0 if stage_lines is None else stage_lines

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

        # The line TE is read from, which a pair's excursion scheduler watches
        self.__te_line = (te_pin if te_pin is not None else dc) if te_used else None

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

        super().__init__(port, display, width, height, bitdepth, backlight, te_used, v_sync, index, reserve)

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

    # Measured on two of these panels: 120 rows is the shallowest ring holding a
    # pair wire-bound at either rotation, 80 still starving rotation 90 by 5.8ms.
    # No column cache, which changes the rotation-90 conversion by 4us a row and the
    # frame not at all, so it is 11.5KB a screen for nothing here.
    FULL_IMAGE_RESERVE = {
        (24_000_000, 12): {"stage_lines": 120, "cache_columns": 0},
    }


class Screen280(Screen):
    WIDTH, HEIGHT = 240, 320
    # No 12-bit row at 75MHz, for the same beam-overtake reason as the 1.54"
    # The 24MHz rate is 45, not the 46 the two-refresh budget nominally allows:
    # panel oscillators run the set rate fast by up to ~1.5% (one measured unit
    # scanned 46.35fps at setting 46, leaving 1.1ms of margin and a marginal
    # tear), and the step down restores ~2ms of margin on a fast unit.
    # The two dual rows are the wires one core could not keep fed: 60fps needs a
    # 33,333us budget and one core spent 34,697us at 37.5MHz 12-bit, so those rates
    # were never available before conversion ran on both cores. Both hold 2.5 to
    # 2.8ms of margin, more than the 24MHz row runs clean on, and 62fps above them
    # is clean too, so each ships a full controller step below anything measured
    # marginal. 37.5MHz 16-bit gets no dual row: it reaches 53 by arithmetic but on
    # 728us, which the panel oscillator's own ~1.5% spread can spend by itself.
    PROFILES = {
        (24_000_000, 12): {"band_lines": 4, "cache_columns": 4, "framerate": 45},
        (37_500_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 52},
        (37_500_000, 12): {"band_lines": 12, "cache_columns": 12, "framerate": 55,
                           "dual": {"band_lines": 12, "cache_columns": 12, "framerate": 60}},
        (75_000_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 53,
                           "dual": {"band_lines": 12, "cache_columns": 12, "framerate": 60}},
    }

    # Measured on two of these panels: a pair converting full-size heap images runs
    # 42.0ms wire-bound against 46.4ms unreserved, claiming 70,560B each. The cache
    # width earns its space here, rotation 90 converting at 148us a row without one
    # against a 131us wire row; 4 columns is the least that keeps up and 12 also buys
    # 6% on the pair rate. The faster wires have no row because they are not merely
    # unmeasured: shortening the wire row below the pair's conversion rate makes the
    # frame conversion-bound whatever the ring holds, so those want their own answer
    # rather than a deeper ring.
    FULL_IMAGE_RESERVE = {
        (24_000_000, 12): {"stage_lines": 160, "cache_columns": 12},
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
                         first.backlight, False, False, None, first.reserve,
                         members=tuple(screens))


class ScreenPair:
    """Two screens on their own SP/CE ports, presented together as one.

    update() streams a frame to both panels at once and, with align on, holds
    their TE phases together so the two change as one: the faster panel
    follows, its edge delayed with TESCAN inside the measured tear margin and
    its rate pulled with FRCTRL2 when TESCAN cannot absorb the error, one
    correction per pair frame. After a pause long enough for the pair to drift
    apart, the next update() first spends a frame-counted rate excursion on
    both panels while the stale content hides it, so resuming costs one late
    frame instead of seconds of visible catching up.

    align defaults to aligning where the pair can, calibrating at construction:
    about four seconds of period probes which it says it is doing, from which the
    pair predicts the steady skew it can hold, align_floor_us. A pair too
    mismatched to hold any says why and runs unaligned, is_aligned() then
    reporting False. align=True refuses such a pair instead, and align=False
    leaves the panels alone; start_aligning() takes the four seconds later, and
    stop_aligning() stops.

    Alignment holds panel state on the following screen, a non-zero TESCAN and
    at times a slower rate code. Both are restored whenever that screen is
    updated outside its pair, and by stop_aligning(). update_pair() stays
    underneath as the stateless entry, which is what the diagnostics use.
    """

    # The fine loop, as tools/check_te_align.py measured it
    DEADBAND_LINES = 2
    KP = 1.0
    MAX_STEP = 8
    SLIP_FRACTION = 0.6         # of the tear margin: the walk's ceiling
    DITHER_FRACTION = 0.4       # of the margin: steady dither pulls the walk back here
    ASSIST_LINES = 4            # slower-code assist when the need exceeds the walk room

    # The resync, as tools/check_te_resync.py measured it
    DEPTHS = (1, 2)             # rate steps a plan may move a panel: deeper buys latency, costs aim
    MAX_FRAMES = 3              # frames of excursion a plan may spend on one panel
    ACCURACY_LINES = 5          # close enough to hand over, so a plan stops paying for better
    ABSORB_US = 1430            # handover error the fine loop hides without looking worse than usual
    TARGET_US = -300            # aim slightly negative, drift closing that side for free
    FLOOR_FRACTION = 0.7        # of the rate quantum: where both measured pairs settle
    PROBE_MS = 250              # settled period probe
    CAPTURE_EDGES = 2           # TE falls per panel per phase capture
    CAPTURE_TIMEOUT_MS = 500
    SCHEDULE_TIMEOUT_MS = 250   # an excursion spans at most MAX_FRAMES + 1 periods

    def __init__(self, first, second, align=None):
        if first is second:
            raise ValueError("a pair needs two different screens")
        if first.port is second.port:
            raise ValueError("a pair needs a screen on each SP/CE port, since one port is one stream; broadcast() shares a port")
        if first.reserve != second.reserve:
            raise ValueError("a pair needs both screens built with the same reserve, since a reservation is shared out across the pair: set it on both, or on neither")

        self.__screens = (first, second)
        self.__align = False
        self.__calibrated = False
        self.__last_frame_ms = None
        self.__walk = 0
        self.__walk_sent = 0
        self.__slow_on = False
        self.__timeouts_seen = 0
        self.__n_hi = None
        self.__dither_hi = 0

        if align is None:
            # A request rather than a requirement: every reason a pair cannot hold
            # alignment is a fact about the panels, so saying so and streaming
            # unaligned still leaves the caller the interleaving, which is the larger
            # part of what a pair buys. Nothing needs undoing on the way out, since
            # start_aligning() raises before it changes anything and calibration hands
            # both panels back their nominal rate whichever way it ends.
            try:
                self.start_aligning()
            except ValueError as e:
                logging.info(f"> Screen pair could not align: {e}")
        elif align:
            self.start_aligning()

    @property
    def screens(self):
        return self.__screens

    def is_aligned(self):
        """Whether the pair is holding its panels' TE phases together.

        The state alignment reached rather than what was asked of it, so False
        where a request went unmet and False again after stop_aligning().
        """
        return self.__align

    def start_aligning(self):
        """Start holding the panels' TE phases together, measuring them first.

        The first call spends about four seconds probing both panels' periods,
        which it says it is doing; later calls resume from those measurements.
        Raises where this pair cannot hold alignment, saying which reason.
        """
        if self.__align:
            return

        first, second = self.__screens
        if not (first.v_sync and second.v_sync):
            raise ValueError("alignment waits on both panels' tearing-effect signals, so it needs both screens created with te and v_sync")
        if not self.__calibrated:
            self.__calibrate()
        self.__walk = 0
        self.__slow_on = False
        self.__timeouts_seen = self.__f_disp.te_timeouts() + self.__l_disp.te_timeouts()
        self.__last_frame_ms = None
        self.__f_screen.__pair = self
        self.__align = True

    def stop_aligning(self):
        """Stop correcting, handing the following panel its TESCAN and rate back."""
        if not self.__align:
            return

        self.__align = False
        if self.__calibrated:
            self.__restore_panel()
            self.__f_screen.__pair = None

    @property
    def align_floor_us(self):
        """The steady skew alignment is predicted to settle at, in microseconds.

        About 0.7 of the follower's one-step rate quantum, which is where both
        measured pair types land. Construction already refused a pair whose
        drift exceeds the quantum outright.
        """
        if not self.__calibrated:
            raise ValueError("align has never been on, so the pair is uncalibrated")

        return self.__floor_us

    def update(self, image, second=None, *, rotation=0, mirror=False, v_sync=None,
               bg_color=picovector.color.black, pixel_double=False, offset=None):
        """Stream a frame to both screens, aligned when align is on.

        One image reaches both panels, or a second positional image gives each
        its own. Every placement keyword takes one value for both screens, or a
        2-tuple for one each, so a pair mounted opposite ways is
        rotation=(90, 270). offset is the exception, being an (x, y) pair
        itself: it is shared unless an element is itself a pair.

            offset=(5, 10)              both screens at (5, 10)
            offset=(5, None)            both screens: x=5, y centred
            offset=(None, (5, 10))      first centred, second at (5, 10)
            offset=((0, 0), (5, 10))    one each

        v_sync=None waits on the tearing-effect signal when both screens were
        built for it. An aligned pair refuses v_sync=False, the signal being
        what alignment measures by.
        """
        first_screen, second_screen = self.__screens
        if second is None:
            second = image
        rotations = __pair_values(rotation, "rotation")
        mirrors = __pair_values(mirror, "mirror")
        doubles = __pair_values(pixel_double, "pixel_double")
        backgrounds = __pair_values(bg_color, "bg_color")
        offsets = __pair_offsets(offset)

        if self.__align:
            if v_sync is False:
                raise ValueError("an aligned pair waits on the tearing-effect signal every frame, since that is what alignment measures by. Call stop_aligning() for free-running frames.")

            # A pause leaves the pair drifted apart. Once the expected error
            # passes what the fine loop can hide, spend a resync on it while
            # the content is still stale; below that the loop absorbs it.
            last = self.__last_frame_ms
            if last is not None and \
                    time.ticks_diff(time.ticks_ms(), last) * self.__drift_us_per_ms > self.ABSORB_US:
                self.__resync()

        first_screen.prepare(image, rotation=rotations[0], mirror=mirrors[0],
                             bg_color=backgrounds[0], pixel_double=doubles[0],
                             offset=offsets[0])
        second_screen.prepare(second, rotation=rotations[1], mirror=mirrors[1],
                              bg_color=backgrounds[1], pixel_double=doubles[1],
                              offset=offsets[1])
        update_pair(first_screen, second_screen, v_sync=v_sync)

        if self.__align:
            self.__correct()
            self.__last_frame_ms = time.ticks_ms()

    def __calibrate(self):
        """Probe both panels' periods, nominal and four codes each, and derive the rest.

        The excursion shifts are derived from the probed periods,
        LINE_SLOTS * (P_code / P_nominal - 1) signed by which panel it is, which
        tracks a frame-counted measurement to a few lines and is the stabler
        number. The nominal rate labels are not derivable from: they are not
        linear in the divider, so every code is probed.
        """
        # Said at the default level: four seconds of a mute constructor reads as a hung
        # board. The figure is fixed work, so unlike a folder of images it can be quoted.
        logging.info("> Calibrating the screen pair, about four seconds ...")
        started = time.ticks_ms()

        screens = self.__screens
        displays = tuple(screen.display for screen in screens)

        # The first probe after a panel's bringup reads about 3.4% long and
        # settles within a second, so each panel's first reading is discarded.
        periods = []
        for display in displays:
            display.te_probe(self.PROBE_MS)
            periods.append(display.te_probe(self.PROBE_MS)[0])
        if not (periods[0] and periods[1]):
            raise ValueError("no tearing-effect signal from one of the panels, which alignment measures by")

        fi = 0 if periods[0] <= periods[1] else 1      # the faster panel follows
        li = 1 - fi
        f_screen = screens[fi]
        controller = f_screen.CONTROLLER
        line_slots = controller.LINE_SLOTS
        s_line = periods[fi] / line_slots

        # Per panel: the sorted rate table, the built rate's index, and a probed
        # settled period at one and two steps each way where the table has them.
        tables = []
        rates = []
        nominals = []
        sweep = [{}, {}]
        for i, screen in enumerate(screens):
            table = screen.CONTROLLER.FRAME_RATE_CONTROL
            ordered = sorted(table)
            nominal = ordered.index(screen.framerate)
            tables.append(table)
            rates.append(ordered)
            nominals.append(nominal)
            for depth in self.DEPTHS:
                for rate_index in (nominal - depth, nominal + depth):
                    if not 0 <= rate_index < len(ordered):
                        continue
                    screen.command(screen.CONTROLLER.REG_FRCTRL2, table[ordered[rate_index]])
                    time.sleep_ms(100)
                    period = screen.display.te_probe(self.PROBE_MS)[0]
                    if period:
                        sweep[i][rate_index] = period
            screen.command(screen.CONTROLLER.REG_FRCTRL2, table[ordered[nominal]])
            time.sleep_ms(100)

        if nominals[fi] - 1 not in sweep[fi]:
            raise ValueError(f"the faster panel is already at {f_screen.framerate}fps, the slowest rate it has, so alignment has no slower one to pull it with")

        # The rate quantum bounds what the loop can hold: one slow-code frame
        # removes quantum lines while every frame adds the drift, so a pair
        # drifting faster than its quantum has no duty that holds it.
        natural = line_slots * (1.0 / periods[fi] - 1.0 / periods[li])  # lines per us
        drift = natural * periods[fi]                                   # lines per period
        quantum = line_slots * (sweep[fi][nominals[fi] - 1] / periods[fi] - 1.0)
        logging.debug(f"> Pair drift {drift:.1f} lines a period, against {quantum:.1f} lines a one-step rate change buys back")
        if drift >= quantum:
            # Panels of different types take their rate from their own PROFILES and
            # so can disagree on a wire where both are tuned well. That has a fix
            # from here, unlike two panels already on one rate.
            if screens[0].framerate != screens[1].framerate:
                remedy = f"Set both screens to the same framerate, {screens[0].framerate}fps and {screens[1].framerate}fps being too far apart"
            else:
                remedy = "Pair better-matched panels"
            raise ValueError(f"these panels' refreshes drift apart faster than alignment can pull them back. {remedy}, or create the pair with align=False.")

        # Excursion options per panel: the no-op, then each probed code held for
        # one to MAX_FRAMES of that panel's own frames. A slower follower or a
        # faster leader closes a positive error, so the shift carries the sign
        # of the panel.
        options = ([(None, 0, 0.0)], [(None, 0, 0.0)])
        for i in (0, 1):
            for rate_index, period in sweep[i].items():
                stretch = line_slots * (period / periods[i] - 1.0)
                per_frame = -stretch if i == fi else stretch
                code = tables[i][rates[i][rate_index]]
                for frames in range(1, self.MAX_FRAMES + 1):
                    options[i].append((code, frames, per_frame * frames))

        # Every plan a resync could want, priced once. A plan pays the drift
        # over its own execution, half a period of average wait for the first
        # fall plus one per counted frame, and only codes pushing the way the
        # error needs are worth pairing.
        settling = natural * periods[fi]
        plans = {}
        for want_negative in (False, True):
            entries = []
            for f_code, f_frames, f_lines in options[fi]:
                if f_frames and (f_lines < 0) != want_negative:
                    continue
                for l_code, l_frames, l_lines in options[li]:
                    if l_frames and (l_lines < 0) != want_negative:
                        continue
                    cost = max(f_frames, l_frames)
                    shift = f_lines + l_lines + settling * (cost + 0.5)
                    schedule = [None, None]
                    schedule[fi] = (f_code, f_frames)
                    schedule[li] = (l_code, l_frames)
                    entries.append((shift, cost, tuple(schedule)))
            plans[want_negative] = entries

        self.__f_screen = f_screen
        self.__f_disp = displays[fi]
        self.__l_disp = displays[li]
        self.__period_f = periods[fi]
        self.__line_slots = line_slots
        self.__s_line = s_line
        self.__natural = natural
        self.__drift_us_per_ms = abs(natural) * s_line * 1000.0
        self.__target_lines = self.TARGET_US / s_line
        self.__floor_us = self.FLOOR_FRACTION * quantum * s_line
        self.__reg_tescan = controller.REG_TESCAN
        self.__reg_frctrl2 = controller.REG_FRCTRL2
        self.__code_norm = tables[fi][rates[fi][nominals[fi]]]
        self.__code_slow = tables[fi][rates[fi][nominals[fi] - 1]]
        self.__nominal_codes = tuple(tables[i][rates[i][nominals[i]]] for i in (0, 1))
        self.__te_lines = tuple(screen.__te_line for screen in screens)
        self.__plans = plans
        self.__calibrated = True

        logging.debug(f"> Calibrated in {time.ticks_diff(time.ticks_ms(), started)}ms, predicted skew floor {self.__floor_us:.0f}us")

    def __send_walk(self, walk):
        if walk != self.__walk_sent:
            self.__f_screen.command(self.__reg_tescan, bytes((walk >> 8, walk & 0xFF)))
            self.__walk_sent = walk

    def __send_slow(self, want_slow):
        if want_slow != self.__slow_on:
            self.__f_screen.command(self.__reg_frctrl2,
                                    self.__code_slow if want_slow else self.__code_norm)
            self.__slow_on = want_slow

    def __restore_panel(self):
        """Hand the follower's panel back: TESCAN wide, nominal rate.

        A non-zero TESCAN narrows the TE pulse to about one line time, which a
        pair frame's tight poll absorbs but a screen updated on its own is not
        promised to, so this runs before any frame outside the pair.
        """
        self.__send_walk(0)
        self.__send_slow(False)
        self.__walk = 0

    def __correct(self):
        """One proportional correction from the last pair frame's write starts."""
        stats_f = self.__f_disp.stats()
        stats_l = self.__l_disp.stats()
        if self.__n_hi is None:
            # The tear margin needs a streamed frame's length, so the walk's
            # bounds wait for the first one
            margin = self.__line_slots + self.__f_screen.height - stats_f.frame_us / self.__s_line
            self.__n_hi = max(4, int(margin * self.SLIP_FRACTION))
            self.__dither_hi = max(2, int(margin * self.DITHER_FRACTION))

        timeouts = self.__f_disp.te_timeouts() + self.__l_disp.te_timeouts()
        if timeouts != self.__timeouts_seen:
            self.__timeouts_seen = timeouts     # a timeout fired, so the skew is not a phase
            return

        err_us = __signed_mod(stats_f.write_start_us - stats_l.write_start_us,
                              self.__period_f)
        need = -err_us / self.__s_line          # positive: the follower must be delayed
        walk = self.__walk
        if abs(need) >= self.DEADBAND_LINES:
            step = round(self.KP * need)
            step = max(-self.MAX_STEP, min(self.MAX_STEP, step))
            walk = max(0, min(self.__n_hi, walk + step))
        self.__walk = walk
        self.__send_walk(walk)
        self.__send_slow(need > (self.__n_hi - walk) + self.ASSIST_LINES
                         or walk > self.__dither_hi)

    def __resync(self):
        """Measure the drift a pause left, and spend an excursion cancelling it.

        The walk holds TESCAN non-zero and a capture wants the wide V-porch
        pulse, so the two never run concurrently: zero the walk, measure,
        correct, and let the loop rebuild it. Runs between frames, while the
        panels still show stale content, so it costs one late frame.
        """
        self.__restore_panel()
        captured = spidisplay.te_phase(self.__f_disp, self.__l_disp, self.__period_f,
                                       self.CAPTURE_EDGES, self.CAPTURE_TIMEOUT_MS)
        if captured is None:
            return          # too few edges, so let the fine loop walk it out
        skew_us, age_us = captured
        if abs(skew_us) <= self.ABSORB_US:
            return
        aged = -skew_us / self.__s_line + self.__natural * age_us
        self.__run_schedule(self.__plan_for(aged - self.__target_lines))

    def __plan_for(self, error):
        """The cheapest plan landing within ACCURACY_LINES, else the closest at any cost."""
        cheapest = None
        closest = None
        for shift, cost, schedule in self.__plans[error > 0]:
            left = abs(error + shift)
            if closest is None or left < closest[0]:
                closest = (left, cost, schedule)
            if left > self.ACCURACY_LINES:
                continue
            if cheapest is None or (cost, left) < (cheapest[1], cheapest[0]):
                cheapest = (left, cost, schedule)
        best = cheapest if cheapest is not None else closest
        return best[2]

    def __set_rate(self, index, code):
        """Set one panel's rate, and hand its TE line back to the schedule's watch."""
        screen = self.__screens[index]
        screen.command(screen.CONTROLLER.REG_FRCTRL2,
                       self.__nominal_codes[index] if code is None else code)
        self.__te_lines[index].init(Pin.IN, pull=Pin.PULL_DOWN)

    def __run_schedule(self, schedule):
        """Hold each panel's code across a counted number of that panel's own frames.

        schedule[i] is (code, frames), frames of 0 leaving that panel alone. A
        panel latches its frame length at a frame boundary, so each code goes on
        just after one of that panel's TE falls and comes off after a counted
        number of later ones, making the frames it spans whole ones. Both panels
        count at once, so a correction costs the longer of the two.
        """
        pins = self.__te_lines
        for pin in pins:
            pin.init(Pin.IN, pull=Pin.PULL_DOWN)
        waiting, counting, done = 0, 1, 2
        state = [done if schedule[i][1] <= 0 else waiting for i in range(2)]
        counts = [0, 0]
        levels = [pin.value() for pin in pins]
        start = time.ticks_ms()
        while state[0] != done or state[1] != done:
            if time.ticks_diff(time.ticks_ms(), start) >= self.SCHEDULE_TIMEOUT_MS:
                break
            for i in range(2):
                if state[i] == done:
                    continue
                value = pins[i].value()
                if value == levels[i]:
                    continue
                levels[i] = value
                if value:
                    continue                # only the falls bound a frame
                if state[i] == waiting:
                    self.__set_rate(i, schedule[i][0])
                    state[i] = counting
                else:
                    counts[i] += 1
                    if counts[i] >= schedule[i][1]:
                        self.__set_rate(i, None)
                        state[i] = done
                levels[i] = pins[i].value()     # the command drove DC, so resync
        for i in range(2):
            if state[i] != done:
                self.__set_rate(i, None)
