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

# te=SHARED_DC: the panel's tearing-effect signal arrives on a DC line other screens
# share. That works only where every breakout on the line carries a diode, which
# blocks each panel's TEOFF from pulling the line down; without one the screens
# divide it and no asserted level survives. The firmware cannot see a diode, so
# naming this is the caller declaring one is fitted. One panel at a time may assert,
# so the driver sends TEON as a frame's wait begins and TEOFF as it ends.
SHARED_DC = "shared_dc"

# time.ticks_us() wraps at 2**30 where the C module's stamps wrap at 2**32, and
# their low bits agree, so a group's hold reduces every stamp it keeps to 30 bits
# and takes every difference there. That lets a frame's own stamp and a plain
# clock reading serve the same arithmetic, and holds to about seventeen minutes.
TICKS_MASK = 0x3FFFFFFF


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

    te says whether a tearing-effect signal is reachable at all, and v_sync whether a
    frame waits on it by default. members is the screens a broadcast group stands
    for, and None for a screen standing for itself. shared_te says the signal arrives
    on a line other screens share, which is what makes the wait transient; sync names
    the screen whose signal a frame waits on.

    Not built directly: construct a Screen subclass or a ScreenGroup.
    """

    def __init__(self, port, display, width, height, bitdepth, backlight, te, v_sync, index, reserve, members=None, shared_te=False, sync=None):
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
        self.__group = None     # The ScreenGroup this screen is a member of, if any
        self.__subset_of = None  # The group a subset narrows, so it writes its members only
        self.__shared_te = shared_te  # Whether this panel's TE reaches a line others share
        self.__sync = sync      # The screen whose TE a frame waits on, None to leave TE alone
        self.__synced_frame = None  # The screen the last frame's wait ended on, if any
        self.__sync_delay_us = 0    # How long a write trails the wait, set by a holding group

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
    def sync(self):
        """The screen whose tearing-effect signal a frame waits on, or None.

        A single screen syncs on itself. A group syncs on the one member it
        nominated, the rest tearing, since panels on a hub scan independently and no
        edge is safe for all of them.
        """
        return self.__sync

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
    def __write_targets(self, to):
        """The displays a write drives, or None for every one this object holds.

        A subset narrows to its own members when the caller names none, which is
        what makes front.update(image) write only the panels front stands for.
        """
        if to is None:
            if self.__subset_of is None:
                return None
            to = self.__members

        members = self.screens
        for screen in to:
            if screen not in members:
                raise ValueError(f"{screen} is not one of these screens, so a frame cannot be sent to it")

        return tuple(screen.display for screen in to)

    def __sync_screen(self, v_sync, to):
        """The screen whose TE this write waits on, or None to leave TE alone.

        Only a screen sharing its DC line needs the transient discipline, a panel
        owning its own line keeping TEON from bringup. Waiting on a member outside
        the written set buys nothing, that panel being clean and not updated while
        every panel that is written tears, so a narrowed write falls to a member of
        its own set.
        """
        if not v_sync or self.__sync is None:
            return None

        written = self.screens if to is None else to
        if self.__sync is self or self.__sync in written:
            return self.__sync

        for screen in written:
            if screen.__shared_te:
                return screen
        return None

    def update(self, image, rotation=0, mirror=False, v_sync=None, bg_color=picovector.color.black, pixel_double=False, offset=None, to=None):
        # A frame outside the pair first hands back the panel state alignment
        # holds, since the narrowed TE pulse is only safe under the pair's poll
        if self.__pair is not None:
            self.__pair.__restore_panel()

        # v_sync=None follows the screen, so only a frame that differs says so
        if v_sync is None:
            v_sync = self.__v_sync
        elif v_sync and not self.__te:
            if self.__members is not None:
                raise ValueError("this broadcast group has no member to wait on: its panels' scans are unsynchronised, so build it with sync naming one of them, which needs every member built te=SHARED_DC")

            raise ValueError("v_sync needs a screen created with te, since it waits on the panel's tearing-effect signal")

        bg = bg_color.p & 0xffffffff

        self.__check_rotation(rotation)
        self.__select()

        synced = self.__sync_screen(v_sync, to)
        delay = (self.__subset_of or self).__sync_delay_us
        # The C module handles the transform, transfer, and TE wait
        self.__display.update(image,
                              rotation=rotation,
                              mirror=1 if mirror else 0,
                              pixel_double=1 if pixel_double else 0,
                              bg=bg, offset=offset, v_sync=v_sync,
                              to=self.__write_targets(to),
                              sync=None if synced is None else synced.display,
                              sync_delay_us=delay)
        self.__synced_frame = synced
        self.drawn()

        # A member updated on its own still scans, so its frames advance its
        # group's hold too; a run of them would otherwise walk the group apart.
        if self.__group is not None:
            self.__group.__frame_ticked(self.__display.stats(), synced, delay)

    @micropython.native
    def prepare(self, image, rotation=0, mirror=False, bg_color=picovector.color.black, pixel_double=False, offset=None, to=None):
        """Stage a frame for update_pair(), converting as far ahead as it can.

        Placement is per screen, so a pair can differ in rotation, mirroring and
        offset to suit how each panel is mounted. Nothing reaches the panel until
        update_pair() runs, and a staged frame refuses command() until it does.
        """
        bg = bg_color.p & 0xffffffff

        self.__check_rotation(rotation)
        self.__select()

        synced = self.__sync_screen(self.__v_sync, to)
        self.__display.prepare(image,
                               rotation=rotation,
                               mirror=1 if mirror else 0,
                               pixel_double=1 if pixel_double else 0,
                               bg=bg, offset=offset,
                               to=self.__write_targets(to),
                               sync=None if synced is None else synced.display)


class Screen(ScreenBase):
    """One panel on an SP/CE port.

    The first screen on a port names no pins and takes the port's own DC, CS and
    backlight. Every further screen names its cs, and its dc unless it is
    deliberately sharing the port's, which panels take te=False or te=SHARED_DC to
    do. With a selector set on the port the screens name no pins and take a channel
    each, in creation order.

    te reads the tearing-effect signal from this screen's own DC line, which is how
    MightyFX wires one panel to a port; SHARED_DC reads it from a line other screens
    share, which needs a diode on each breakout and asserts TE only for the frame
    waiting on it; a Pin is a dedicated input; False sends TEOFF and never waits.
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

        shared_te = te is SHARED_DC
        te_used = te is not False
        te_pin = None if shared_te or isinstance(te, bool) else te

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
        dc = port.__claim_dc(dc, te_used, shared_te)

        # The line TE is read from, which a pair's excursion scheduler watches
        self.__te_line = (te_pin if te_pin is not None else dc) if te_used else None

        backlight = None
        if bl:
            backlight = port.__claim_backlight()
            backlight.__register(self)

        display = spidisplay.SPIDisplay(bus=port.bus, cs=cs, dc=dc, te=te_pin,
                                        width=width, height=height,
                                        ram_write=controller.RAM_WRITE,
                                        te_on=controller.TE_ON, te_off=controller.TE_OFF,
                                        te_mode=controller.TE_MODE,
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

        super().__init__(port, display, width, height, bitdepth, backlight, te_used,
                         v_sync, index, reserve, shared_te=shared_te,
                         sync=self if shared_te else None)

        port.__register(self)

        # What setup() is about to write, and the slots that porch spends. A group's
        # trim moves both, so every margin sum reads them from the screen.
        self.__porch = controller.PORCH
        self.__line_slots = controller.LINE_SLOTS

        # Bringup goes through this screen's command(), so a selector is pointed at
        # the panel for every register write as well as every frame. A shared line
        # comes up at TEOFF: the driver asserts TE only for the frame that waits on
        # it, since one panel at a time may reach the line.
        controller.setup(self, width, height, bd_code, fr_code, te_used and not shared_te)

    @property
    def framerate(self):
        """The panel's own refresh rate, which bounds the tearing margin."""
        return self.__framerate

    @property
    def line_slots(self):
        """Scan slots this panel spends per refresh, porches included.

        A TE period over this is the line time. The porch sets it, so a member a
        group has trimmed reports its own count rather than the controller's
        default, and every margin sum reads it from here.
        """
        return self.__line_slots

    @property
    def porch(self):
        """The back and front porch, in scan lines, as PORCTRL holds them.

        A group's trim owns this while it holds its members in phase, so setting it
        by hand belongs to a diagnostic rather than to an application.
        """
        return self.__porch

    def __set_porch(self, back, front):
        """Move this panel's refresh period by whole scan lines.

        One porch line is one line time. The setting a caller reaches for is the
        group's align; this is the mechanism it moves a member with.
        """
        if back < 1 or front < 1:
            raise ValueError(f"a porch of ({back}, {front}) has a side under one line, which the controller has no code for")

        self.CONTROLLER.set_porch(self, back, front)
        self.__porch = (back, front)
        self.__line_slots = self.CONTROLLER.CONTROLLER_ROWS + back + front

    @property
    def requested_baudrate(self):
        """The rate this panel asked for, against display.baudrate()'s achieved one."""
        return self.__baudrate

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


class ScreenGroup(ScreenBase):
    """Several of a port's screens driven as one, sharing a frame.

    One stream reaches every member, so a wall of panels renders in the time one of
    them takes. The members keep their identity, so each can still be brought up and
    updated on its own.

    Built directly over panels agreeing on bit depth, dimensions, rate and tuning.
    Those are copied once, so a member that later re-rates itself moves only itself.
    A screen belongs to one group at a time, which is what keeps ownership of the
    panel state a group holds single.

    subset() names fewer of the members over the same display, for a frame that
    reaches only some of them. A subset owns nothing and costs no display.

    sync names the one member whose tearing-effect signal a frame waits on, which
    needs every member built te=SHARED_DC. That panel comes out clean and the rest
    tear, panels on a hub scanning independently with no edge safe for all of them.
    None takes the first member that can, saying so if none can; False declines the
    wait, so a frame goes out at once.
    """

    # The first probe after bringup reads long and settles within a second, so each
    # panel's first reading is discarded, as ScreenPair does. 300ms is about 13
    # periods: at 100 a single miscounted edge moved a trim by three porch lines,
    # which is more than the spread the trim exists to null.
    PROBE_MS = 300
    SETTLE_MS = 100

    # Of the fastest member's margin, what the hold may spend. ScreenPair holds its
    # dither to the same fraction and slips at 0.6.
    DITHER_FRACTION = 0.4

    # Frames between one probe-mode measurement and the next. 30 is about two
    # seconds at a group's frame rate, so six members come round in twelve.
    TRIM_FRAMES = 30

    # How far one gap between a member's anchors moves its modelled rate. The
    # panels' rates wander around 10us a period over seconds, which no calibration
    # can pin, so the model leans on the newest reading; the reading is good to
    # about 1us a period, the TE jitter over the dozen periods between anchors.
    RATE_GAIN = 0.5

    # Of a line, how far a member's modelled rate drifts before a whole porch line
    # corrects it. Half a line is the rounding point, but the 1.54's half-line is
    # 27us where its rate wanders about 10, so rounding fires corrections on noise
    # that a deadband this wide does not, each one a real rate step.
    TRIM_DEADBAND = 0.75

    # The most one correction moves a member. A stale calibration is worth whole
    # lines, and applying them at once is a visible step where a line at a time is
    # inside the sawtooth the hold carries anyway.
    TRIM_LIMIT_LINES = 1

    # Porch lines an acquisition's excursion rounds run at, and the depth the
    # hold's dither reaches while walking a straggler back in behind flowing
    # frames. Both move a member whichever way is nearer, since neither writes to
    # the member while it travels: an acquisition runs between frames, and a
    # walking member is held out of the write until it fits. Lengthening is
    # measured usable to 56 blanking lines, and shortening stops at the porch
    # floor, which the walk clamps to rather than overshooting.
    EXCURSION_LINES = 8
    WALK_LINES = 24

    # The shortest back porch a walk may leave. Blanking is the porch, so it is
    # also the tearing pulse: with the 12-line front porch this holds the pulse
    # above a millisecond on both panel types, clear of te_short_waits' 700us
    # and of the controller's own minimum, so a walking member is still readable
    # as the wait target and keeps taking its turn at being measured.
    WALK_FLOOR_LINES = 8

    # The longest a frame waits for the members to come together before it goes
    # out regardless. update() presents on every member before it returns, so a
    # straggler is waited for rather than dropped, and past this the frame is
    # written and tears on whoever is still out: one spoiled frame beats a
    # stalled wall. A pause long enough to need the whole budget is a pause the
    # caller has already spent seconds on, so the wait costs nothing it notices.
    WALK_WAIT_MS = 600

    # How far past the window a member may sit before a frame waits for it. The
    # write lands centre_us less the error into a member's scan, so an error
    # just past the window tears a line at the extreme edge where one several
    # milliseconds past tears a visible band. Stalling the wall for a line is
    # the wrong trade, and the hold's own ripple lives inside this.
    WAIT_SLACK_LINES = 8

    # Sweeps allowed to bring the phases together before the group gives up. It
    # converges in two and the third is noise, so more buys nothing.
    ACQUIRE_TRIES = 3

    # Past this gap between frames a rate reading is not trusted, the panels'
    # rates wandering while nothing measures them, and a hold not yet fed its
    # first frame reacquires outright. The bookings themselves survive any pause:
    # an anchor resolves its measurement nearest the booking and phases are
    # modular, so however far extrapolation drifted, the members walk back in.
    HOLD_PAUSE_MS = 1000

    # Past this gap a resume sweeps the members' phases before walking them
    # together, an extrapolation over it being worth less than a measurement:
    # a 1s prediction spends 42% of the 280's margin and overruns the 154's,
    # and a walk aimed from a stale booking arrives somewhere else.
    SWEEP_PAUSE_MS = 1000

    def __init__(self, *screens, sync=None, align=None, trim=None, parent=None):
        if len(screens) < 2 and parent is None:
            raise ValueError("a broadcast group needs at least two screens")

        port = screens[0].port
        if port.selector is not None:
            raise ValueError("a selector reaches one screen at a time, so a port with one cannot broadcast")

        for screen in screens:
            if screen.port is not port:
                raise ValueError("a broadcast group has to be on one port, since two ports are two streams")

        # A subset is a member set over its parent's display, so it claims no
        # members, builds no display, and leaves ownership where it is.
        if parent is not None:
            # A subset inherits its parent's nomination, since alignment and the
            # panel state stay the parent's; sync=False declines the wait for this
            # set alone. A nominated member outside the set is resolved per write.
            nominated = parent.sync if sync is None else sync
            if nominated is False:
                nominated = None
            super().__init__(port, parent.display, parent.width, parent.height,
                             parent.bitdepth, parent.backlight, nominated is not None,
                             nominated is not None, None, parent.reserve,
                             members=tuple(screens), sync=nominated)
            self.__subset_of = parent
            # Alignment stays the parent's, so a subset reports it rather than
            # owning it: its members are held whether or not this set writes them.
            self.__aligned = parent.is_aligned
            self.__reference = parent.reference
            self.__floor_us = parent.align_floor_us
            self.__trim = parent.trim
            return

        for screen in screens:
            if screen.__group is not None:
                raise ValueError("a screen belongs to one group at a time, and one of these is already in another. Take a subset of the group it is in, or build a single group over every panel that shares a frame.")

        # One member's TE, not all of them: a hub's panels scan independently, so no
        # edge is safe for every one and the nominated panel comes out clean while
        # the rest tear. Naming a member is a request and refuses if it cannot be
        # met; None takes the first that can, and False declines the wait outright.
        nominated = None
        if sync is not False:
            shared = [screen for screen in screens if screen.__shared_te]
            if sync is not None:
                if sync not in screens:
                    raise ValueError(f"{sync} is not a member of this group, so it cannot be the one its frames wait on")
                if not sync.__shared_te:
                    raise ValueError(f"{sync} was not built te=SHARED_DC, so its tearing-effect signal is not on the line this group's frames read. Build every member te=SHARED_DC, which needs the diode fitted.")
                nominated = sync
            elif shared:
                nominated = shared[0]
            else:
                logging.info("screens: this group's panels carry no shared tearing-effect signal, so its frames will not wait and every panel may tear. Build the members te=SHARED_DC to nominate one.")

        first = screens[0]
        display = port.bus.broadcast(*[screen.display for screen in screens])

        # The backlight is the first member's, since screens on a port share the one
        # PWM.
        super().__init__(port, display, first.width, first.height, first.bitdepth,
                         first.backlight, nominated is not None, nominated is not None,
                         None, first.reserve, members=tuple(screens), sync=nominated)

        self.__aligned = False
        # Three states, not two. Nulling the members' rates stops them drifting apart
        # quickly; an acquisition brings their scans together at one instant; only a
        # hold keeps them there. The residual rate spread separates them again at 30
        # to 90us a period, which is past the aim inside two of them, so an
        # acquisition on its own is worth a tenth of a second.
        self.__acquired_us = 0
        self.__holding = False
        self.__reference = None
        self.__floor_us = 0
        self.__target_us = 0
        self.__margins = ()
        self.__aim_us = 0
        self.__line_us = ()
        self.__trim_at = 0
        self.__starts = []
        self.__corrections = 0
        # Frames written with a member past its own tearing budget, and how far
        # the worst of them was past it. A tear is brief and only shows where the
        # content changed, so this is what a diagnostic reads instead of an eye.
        self.__exposed_frames = 0
        self.__worst_exposure_us = 0
        self.__past_budget_us = 0
        # The hold's state, per member: the sub-line rate error calibration left,
        # the phase error that rate has built since acquisition, and the porch line
        # currently dithered on. Armed by a successful acquisition.
        self.__residual_us = [0.0] * len(screens)
        self.__phase_us = [0.0] * len(screens)
        self.__dither = [0] * len(screens)
        self.__anchor_stamp = [0] * len(screens)
        self.__anchor_dither = [0.0] * len(screens)
        self.__anchor_skip = [False] * len(screens)
        self.__fresh_hold = False
        self.__walking = False
        self.__centre_us = 0
        self.__held_stamp = 0
        self.__swept_at = 0
        self.__grid_at = 0
        self.__grid_phases = ()
        if align is not False:
            if nominated is None:
                # The sync block above already said why there is no signal to hold
                # these panels by, so only a required alignment speaks again.
                if align is True:
                    raise ValueError("align holds a group's panels in phase by their tearing-effect signal, so it needs every member built te=SHARED_DC")
            else:
                self.__calibrate(align is True)

        # A trim holds members to the period calibration settled on, so a group with
        # no settled period has nothing to correct toward and does not trim.
        #
        # None rotates only once the members are held in phase, which is what makes
        # moving the wait target free: any member serves when they all fall together.
        # Held to one rate but not one phase, rotating moves which panel comes out
        # clean and jumps every other panel's tear with it, seen on the glass. So
        # until phase is held, None is off and probe is the way to ask for freshness.
        if trim not in (None, True, False, "rotate", "probe"):
            raise ValueError(f"{trim} is not a valid trim. Expected None, False, 'rotate', or 'probe'.")

        if not self.__target_us:
            if trim not in (None, False):
                logging.info("screens: this group holds no period for its members, so there is nothing for a trim to correct toward")
            self.__trim = False
        elif trim in (None, True):
            self.__trim = "rotate" if self.__holding else False
        else:
            self.__trim = trim

        # Last, so a construction that raised claims nothing: a member left holding a
        # group that does not exist refuses every later attempt to group it.
        for screen in screens:
            screen.__group = self

    def __calibrate(self, required):
        """Probe every member's period, trim each toward the slowest, and price it.

        The reference is the slowest member, so every trim lengthens a porch, which
        is the direction that also adds margin to the panel with least of it. One
        porch line is one line time, measured, so the quantum needs no probing: what
        is probed is each member's own period, which no table gives.

        required refuses where the members will not hold; otherwise an unmet request
        says why and the group falls back to the member sync nominated, which is a
        legitimate outcome and not a failure.
        """
        members = self.screens
        logging.info(f"> Calibrating {len(members)} screens, about"
                     f" {len(members) * self.PROBE_MS * 2 // 1000 + 1} seconds ...")

        periods = []
        for screen in members:
            if screen.sync is None:
                self.__unaligned(required, f"{screen} carries no tearing-effect signal a group can read, so build every member te=SHARED_DC")
                return
            period = self.__period_of(screen, settle=True)
            if not period:
                self.__unaligned(required, f"{screen} returned no period, so its tearing-effect signal is not reaching the shared line")
                return
            periods.append(period)

        # Each panel's line time is its own and fixed by its oscillator; the porch
        # moves how many of them a refresh spends, not how long one lasts.
        line_us = [period / screen.line_slots for period, screen in zip(periods, members)]
        slowest = periods.index(max(periods))
        frame_us = self.display.wire_window_us()
        trims = [int(round((periods[slowest] - period) / line))
                 for period, line in zip(periods, line_us)]

        # The budget is the fastest member's, not the reference's: a written frame
        # costs fixed microseconds while a fast panel's lines are shorter, so the
        # same write eats more of them.
        margins = [(screen.line_slots + trim + screen.height - frame_us / line)
                   for screen, trim, line in zip(members, trims, line_us)]
        tightest = margins.index(min(margins))
        quanta = 2 * line_us[tightest]
        margin_us = margins[tightest] * line_us[tightest]
        reserve = self.DITHER_FRACTION * margin_us

        if quanta + reserve > margin_us or margin_us <= 0:
            self.__unaligned(required, f"{members[tightest]} keeps only {margin_us:.0f}us of tearing margin, and holding a group costs {quanta:.0f}us of granularity plus a reserve. Lengthen every member's porch, or drop the rate a step")
            return

        # Past the refusal, so nothing above has moved a panel: a group that declines
        # to align leaves every porch where bringup left it and names no reference.
        self.__reference = members[slowest]
        for screen, trim in zip(members, trims):
            if trim:
                back, front = screen.porch
                screen.__set_porch(back + trim, front)

        # One verify pass. A trim is priced from a single reading, and a reading that
        # miscounts an edge lands whole porch lines out; measuring the trimmed panels
        # and correcting the residual costs one probe each and leaves the static trim
        # actually static, with only a fraction of a line for the hold to carry.
        time.sleep_ms(self.SETTLE_MS)
        held = [self.__period_of(screen) for screen in members]
        if all(held):
            target = max(held)
            for index, screen in enumerate(members):
                correction = int(round((target - held[index]) / line_us[index]))
                if correction:
                    back, front = screen.porch
                    screen.__set_porch(back + correction, front)
                # What the member runs at against the target, under half a line
                # either way: the rate error the hold's accumulator integrates.
                self.__residual_us[index] = held[index] + correction * line_us[index] - target
            logging.debug(f"screens: verified at {held}, spread {max(held) - min(held)}us")
            self.__target_us = target

        self.__aligned = True
        self.__floor_us = quanta
        self.__line_us = tuple(line_us)
        # In microseconds, per member, so an acquisition can tell which of them can
        # afford to be advanced and which has to be delayed the long way round.
        self.__margins = tuple(margin * line for margin, line in zip(margins, line_us))

        # What a phase spread has to fit inside. A member out of phase spends that
        # much of its own tearing margin, so the aim is the tightest member's less
        # the reserve the hold keeps, rather than a figure picked to suit a result.
        self.__aim_us = (1.0 - self.DITHER_FRACTION) * margin_us

        # Half the tightest member's margin, which is where a held group starts its
        # writes: at the fall itself the synced member's own budget is whole but a
        # member scanning later has none, and the constellation straddles that
        # edge, so the write floats in the middle of the window instead.
        self.__centre_us = int(margin_us / 2)

        # One rate stops them drifting apart; acquisition brings them together, and
        # the hold is what keeps them there, the residual rate spread passing the
        # aim inside half a second otherwise.
        if self.__target_us and self.__acquire():
            self.__arm_hold()
        logging.info(f"screens: aligned on {self.__reference}, trims {trims} porch lines,"
                     f" {margin_us:.0f}us of margin at the tightest member")

    def __phases(self):
        """Every member's phase at one instant, swept one at a time behind TEON.

        A shared line carries one panel's signal at a time, so the captures do not
        share a moment and ageing is what brings them onto one: each member's last
        fall is carried forward by the period the group holds them all to. The
        reference instant is the last capture's own end, so every member is aged
        forward and none backward.

        Returns the time since each member last fell, or None where one went silent.
        """
        # Two falls, which is the fewest that names one: the sweep serialises, so
        # every extra fall ages the members swept before it by another period and the
        # ageing error is what limits the aim. Four falls tripled the sweep and made
        # the acquisition worse.
        rows = []
        for screen in self.screens:
            screen.command(screen.CONTROLLER.REG_TEON, b"\x00")
            falls, finished = screen.display.te_capture(2, 200)
            screen.command(screen.CONTROLLER.REG_TEOFF)
            if not falls:
                return None
            rows.append((falls[-1], finished))

        # Aged by the period the group holds them all to, not by one read from this
        # capture: a period from two adjacent falls carries the panel's own jitter,
        # where the group's is averaged over a settled probe. The error left is the
        # residual rate spread times the periods aged, so a tight trim is what makes
        # a close aim possible.
        reference = rows[-1][1]
        self.__swept_at = reference & TICKS_MASK
        return [((reference - fall) & 0xFFFFFFFF) % self.__target_us
                for fall, _ in rows]

    def __acquire(self):
        """Bring the members' scans together, which one rate alone does not do.

        A member is moved by running its porch long for a while: a period stretched
        by EXCURSION_LINES for k of them delays that member by k times the stretch,
        and the porch goes back afterwards. Only ever lengthened, so a member is
        always delayed into place and its margin grows while it travels rather than
        shrinking, which the 1.54 has no room for.

        Sweeping serialises behind TEON and the members drift while it runs, so the
        aim carries the sweep's own ageing error. That is what the retries are for,
        and a group still past the aim when they run out is armed from its final
        sweep regardless: any measured sweep is a working grid, and the hold walks
        the remainder in at about a line time a frame, where refusing would leave
        every panel but one tearing indefinitely. Only a member going silent fails.
        """
        members = self.screens
        # One more check than excursion rounds: the last round's outcome has to be
        # measured, or a converged group is judged on the state before it.
        for attempt in range(self.ACQUIRE_TRIES + 1):
            phases = self.__phases()
            if phases is None:
                logging.info("screens: a member went silent during the phase sweep, so the group is not in phase")
                return False

            # Phases are modular, so the spread is taken on the circle: a member one
            # step behind the reference reads a whole period ahead of it, and a plain
            # max minus min calls a converged group maximally spread.
            target = phases[members.index(self.__reference)]
            errors = [self.__fold(phase - target) for phase in phases]
            spread = max(errors) - min(errors)
            settled = spread <= self.__aim_us
            if settled or attempt == self.ACQUIRE_TRIES:
                self.__acquired_us = spread
                # The grid the hold measures against is common: every member's
                # ideal falls are the reference's, and the bookings are seeded
                # with the offsets this sweep measured, so the hold walks every
                # member onto the grid rather than holding it where it landed.
                self.__grid_at = self.__swept_at
                self.__grid_phases = tuple([target] * len(members))
                self.__phase_us = [-error for error in errors]
                if settled:
                    logging.info(f"screens: members brought into phase, spread {spread}us"
                                 f" after {attempt} excursions. It decays at the residual"
                                 f" rate spread until a hold carries it")
                else:
                    logging.info(f"screens: the members are still {int(spread)}us apart"
                                 f" against a {self.__aim_us:.0f}us aim, so the hold"
                                 f" walks the rest in, about a line time a frame")
                return True

            # Delay each member until its fall meets the reference's. A phase is the
            # time since that member last fell, so one further through its frame than
            # the reference has to wait the difference out.
            self.__excurse(errors)

    def __excurse(self, errors):
        """One concurrent excursion round cancelling the given phase errors.

        errors carry the sweep's sign, positive being a member ahead of the
        reference, cancelled by delaying it that long: its porch runs long for
        whole periods, EXCURSION_LINES at a time, and goes back after. Each
        member takes whichever direction is nearer, which halves the worst case
        against delaying alone. Shortening a porch spends tearing margin while
        it runs, and that costs nothing here: no frame is written during an
        excursion, so there is no write for the margin to protect. Every
        excursion runs at once and each is lifted at its own count, so a round
        costs the longest one and not their sum. Returns how far each member
        moved, in microseconds, later being positive.
        """
        members = self.screens
        plans = []
        for index in range(len(members)):
            stretch = self.EXCURSION_LINES * self.__line_us[index]
            plans.append(int(round(errors[index] / stretch)))

        logging.debug(f"screens: errors {[int(e) for e in errors]},"
                      f" excursions {plans} periods")

        for index, screen in enumerate(members):
            if plans[index]:
                lines = self.EXCURSION_LINES if plans[index] > 0 else -self.EXCURSION_LINES
                back, front = screen.porch
                screen.__set_porch(back + lines, front)

        elapsed = 0
        for index in sorted(range(len(members)), key=lambda i: abs(plans[i])):
            if not plans[index]:
                continue
            run = abs(plans[index])
            time.sleep_ms(int((run - elapsed) * self.__target_us / 1000) + 1)
            elapsed = run
            lines = self.EXCURSION_LINES if plans[index] > 0 else -self.EXCURSION_LINES
            back, front = members[index].porch
            members[index].__set_porch(back - lines, front)

        return [plans[index] * self.EXCURSION_LINES * self.__line_us[index]
                for index in range(len(members))]

    def __fold(self, error):
        """A modular phase difference brought onto +-half a period."""
        error %= self.__target_us
        return error - self.__target_us if error > self.__target_us / 2 else error

    def __phase_spread(self):
        """How far apart the members' falls are, on the circle. 0 where unreadable."""
        phases = self.__phases()
        if phases is None:
            return 0

        target = phases[self.screens.index(self.__reference)]
        errors = [self.__fold(phase - target) for phase in phases]
        return int(max(errors) - min(errors))

    def update(self, image, *args, **kwargs):
        """Stream a frame to every member, then advance the hold and the trim.

        Takes what ScreenBase.update() takes. Every member the caller named is
        written, whatever its phase: update() is a promise that the group has
        presented by the time it returns, and a member held back to spare it a
        tear breaks that promise where a tear only spoils one frame. A member
        out of phase therefore tears until the hold walks it back, which takes a
        few frames. Both ticks run here rather than on a timer, the windows
        between written frames being the only ones a register write may sit in;
        a subset's frames tick its parent, since a member not being written
        still scans and still drifts.
        """
        owner = self.__subset_of or self
        if owner.__holding:
            to = args[6] if len(args) > 6 else kwargs.get("to")
            owner.__walk_in(self.screens if to is None else to)
        super().update(image, *args, **kwargs)
        synced = self.__synced_frame
        owner.__frame_ticked(self.display.stats(), synced, owner.__sync_delay_us)
        owner.__tick_trim(synced)

    def __walk_in(self, written):
        """Wait for the members to come together before a frame goes out.

        Nothing is written while this runs, so the group presents in one piece
        rather than in waves. Over a frame or two of streaming the wait needs no
        measurement, a tick asking only for an elapsed time and the rates the
        hold already carries; past SWEEP_PAUSE_MS it sweeps first, an
        extrapolation that far being worth less than what the panels say. Past
        WALK_WAIT_MS the frame goes out and tears on whoever is still out,
        update() being a promise that the group has presented by the time it
        returns.
        """
        if self.__out_of_phase(written):
            if ((time.ticks_us() - self.__held_stamp) & TICKS_MASK) > self.SWEEP_PAUSE_MS * 1000:
                self.__reseed()

            deadline = time.ticks_add(time.ticks_ms(), self.WALK_WAIT_MS)
            nap = int(self.__target_us / 1000) + 1
            waited = 0
            while self.__out_of_phase(written):
                if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                    logging.info("screens: some panels are still out of phase, so this frame goes out and tears on them rather than holding the group up any longer")
                    break
                time.sleep_ms(nap)
                self.__tick_hold(time.ticks_us() & TICKS_MASK, -1)
                waited += 1
            if waited:
                logging.debug(f"screens: held the frame {waited} periods for the members to come together")

        if self.__past_budget_us:
            self.__exposed_frames += 1
            if self.__past_budget_us > self.__worst_exposure_us:
                self.__worst_exposure_us = int(self.__past_budget_us)

    def __reseed(self):
        """Replace the bookings with a fresh sweep, so a walk aims at the truth.

        Every member drifts by its own residual while nothing measures it, which
        after a few seconds is milliseconds apiece and independent between them,
        so re-anchoring one member fixes only that one. The grid is rebuilt
        around the sweep's own instant and the bookings carry the offsets it
        measured, leaving the hold's dither to close what is left. A silent
        member keeps the bookings, the walk then being the only recovery left.
        """
        phases = self.__phases()
        if phases is None:
            logging.debug("screens: a member did not answer the sweep, so the walk keeps its bookings")
            return

        members = self.screens
        target = phases[members.index(self.__reference)]
        errors = [self.__fold(phase - target) for phase in phases]
        self.__grid_at = self.__swept_at
        self.__grid_phases = tuple([target] * len(members))
        self.__phase_us = [-error for error in errors]
        self.__held_stamp = self.__swept_at
        logging.debug(f"screens: swept the members after a pause, spread"
                      f" {int(max(errors) - min(errors))}us for the walk to close")

    def __out_of_phase(self, written):
        """How far the worst written member is past what a wait tolerates, 0 for none.

        The write starts centre_us into the synced member's scan, so that is how
        far out of phase a member may be before it leaves its own tearing
        margin, and WAIT_SLACK_LINES sits on top of that. Bookings are carried to
        this instant, so the first frame after a pause is judged on where the
        panels are and not where they were. __past_budget_us is left holding the
        worst excess over the budget itself, which is what a frame written now
        would risk on the glass.
        """
        self.__past_budget_us = 0
        members = self.screens
        synced = self.__sync
        if synced is None or synced not in written:
            return 0

        periods = ((time.ticks_us() - self.__held_stamp) & TICKS_MASK) / self.__target_us
        phases = {}
        for screen in written:
            index = members.index(screen)
            phases[screen] = self.__phase_us[index] + periods * (
                self.__residual_us[index] + self.__dither[index] * self.__line_us[index])

        base = phases[synced]
        worst = 0
        for screen, phase in phases.items():
            past = abs(self.__fold(phase - base)) - self.__centre_us
            if past > self.__past_budget_us:
                self.__past_budget_us = past
            past -= self.WAIT_SLACK_LINES * self.__line_us[members.index(screen)]
            if past > worst:
                worst = past
        return worst

    def __frame_ticked(self, stats, synced, delay):
        """Advance the hold from a written frame's own stamp."""
        if not self.__holding:
            return

        # The write trails the wait by the group's centring delay and the stamp
        # moves with it, so the delay comes back out: the clock and the grid are
        # both fall-referenced, whichever path the frame took.
        stamp = stats.write_start_us
        members = self.screens
        anchored = -1
        if synced is not None:
            stamp -= delay
            # A stamp is a fall only where the frame waited and the wait did not
            # time out, a timeout releasing at whatever phase its budget expired.
            if synced in members and stats.te_wait_us < 2 * self.__target_us:
                anchored = members.index(synced)
        self.__tick_hold(stamp & TICKS_MASK, anchored)

    def __tick_hold(self, stamp, anchored):
        """Walk each member onto the group's grid and hold it, a porch line at a time.

        Between frames each member's booked phase advances by its modelled rate
        error, but the frame's own write stamp is the synced member's TE fall, so
        that member's booking is replaced by a measurement for free and the trim's
        rotation carries the measurement round the group. The model alone cannot
        serve: a dithered porch line lands with a one-frame ambiguity, so each
        toggle mis-books up to a line and an unmeasured hold random-walks apart.

        Errors are held against the reference member, which is never dithered, so
        the whole group warming together costs nothing. Each other member takes
        the dither, -1, 0 or +1 porch lines, predicted to leave its error nearest
        zero, which centres the ripple instead of walking one side of it.
        """
        if not self.__holding:
            return

        elapsed = (stamp - self.__held_stamp) & TICKS_MASK
        self.__held_stamp = stamp
        if elapsed > self.HOLD_PAUSE_MS * 1000 and self.__fresh_hold:
            # A group's first frame can arrive seconds behind its acquisition,
            # another group's construction being that long, and nothing has drawn
            # yet so the backlight is dark: reacquire by sweeping behind the
            # frame. Released only when the reacquisition itself fails. Any later
            # pause is ridden out instead, the bookings extrapolating across it
            # and the dither's deep end walking the stragglers back in.
            if self.__acquire():
                self.__arm_hold()
                self.__fresh_hold = False
            else:
                self.__release_hold(elapsed)
            return
        self.__fresh_hold = False

        members = self.screens
        periods = elapsed / self.__target_us
        for index in range(len(members)):
            applied = self.__dither[index]
            if applied:
                self.__anchor_dither[index] += applied * self.__line_us[index] * periods
            if index == anchored:
                self.__anchor(index, stamp)
            else:
                self.__phase_us[index] += (self.__residual_us[index] + applied * self.__line_us[index]) * periods

        reference = members.index(self.__reference)
        anchor = self.__phase_us[reference]
        drift = self.__residual_us[reference] * periods
        walking = False
        for index, screen in enumerate(members):
            if index == reference:
                continue
            line = self.__line_us[index]
            residual = self.__residual_us[index]
            applied = self.__dither[index]
            # Folded: the whole group walks the grid as the panels warm, and the
            # anchor wraps each member's booking at half a period, so two members
            # either side of a wrap differ by a period while their scans do not.
            back, front = screen.porch
            error = self.__fold(self.__phase_us[index] - anchor)
            # The write starts centre_us into the synced member's scan, so a
            # member further out than that has it outside its own budget and is
            # tearing whatever happens: the walk runs deep, its margin no longer
            # being worth protecting. Inside, one line a frame is all the ripple
            # asks for.
            if abs(error) <= self.__centre_us:
                limit = 1
            else:
                limit = self.WALK_LINES
                walking = True
                # Advancing gives porch back and stops at the walk's floor, where
                # delaying has the whole depth to spend. A member with little
                # porch in hand therefore goes the long way round, which on these
                # panels closes a half-period error sooner than crawling.
                if error > 0:
                    room = back - applied - self.WALK_FLOOR_LINES
                    long_way = (self.__target_us - error) / (self.WALK_LINES * line)
                    if room < 1 or error / (room * line) > long_way:
                        error -= self.__target_us
            lines = int(round(((drift - error) / periods - residual) / line))
            lines = limit if lines > limit else (-limit if lines < -limit else lines)
            # Shortening stops at the walk's porch floor, which keeps this
            # member's tearing pulse readable while it travels. Clamp to it
            # rather than skipping the write, which would stall a walk that has
            # to advance.
            floor_lines = self.WALK_FLOOR_LINES - back + applied
            if lines < floor_lines:
                lines = floor_lines
            if abs(lines) > 1:
                # A porch moving whole excursions lands with the same one-frame
                # ambiguity a line does, several lines at a time: not a rate.
                self.__anchor_skip[index] = True
            if lines != applied:
                screen.__set_porch(back + lines - applied, front)
                self.__dither[index] = lines

        if walking != self.__walking:
            logging.debug(f"screens: walk {'engaged' if walking else 'done'},"
                          f" dithers {self.__dither}")
        self.__walking = walking

    def __arm_hold(self):
        """Start holding from the last sweep, whose grid and bookings acquisition set."""
        count = len(self.screens)
        self.__anchor_stamp = [0] * count
        self.__anchor_dither = [0.0] * count
        self.__anchor_skip = [False] * count
        self.__held_stamp = self.__swept_at
        self.__sync_delay_us = self.__centre_us
        self.__fresh_hold = True
        self.__holding = True
        logging.debug(f"screens: writes start {self.__centre_us}us behind the tearing"
                      f" edge, centred in the tightest member's margin")

    def __anchor(self, index, stamp):
        """Replace one member's booking with its measured fall, and learn its rate.

        Consecutive anchors of one member are whole periods apart, so their gap,
        less the dither lines the hold spent between them, is also a rate reading.
        A reference reading moves the group's target, so the whole fleet warming
        together is one number tracking; any other member's is smoothed into its
        model, corrected by a whole porch line where the model has drifted past
        the deadband. A gap spanning a correction is not a rate, the porch moving
        at a boundary only the panel knows, so the reading after one is discarded.
        """
        members = self.screens
        gap = (stamp - self.__anchor_stamp[index]) & TICKS_MASK
        if self.__anchor_stamp[index] and gap < self.HOLD_PAUSE_MS * 1000:
            if self.__anchor_skip[index]:
                self.__anchor_skip[index] = False
            else:
                whole = int(round(gap / self.__target_us))
                if whole > 0:
                    observed = (gap - self.__anchor_dither[index]) / whole - self.__target_us
                    residual = self.__residual_us[index]
                    residual += self.RATE_GAIN * (observed - residual)
                    screen = members[index]
                    if screen is self.__reference:
                        moved = int(round(residual))
                        if moved:
                            self.__rebase(self.__target_us + moved, stamp)
                            residual -= moved
                    else:
                        line = self.__line_us[index]
                        lines = 0
                        if residual > self.TRIM_DEADBAND * line:
                            lines = -self.TRIM_LIMIT_LINES
                        elif residual < -self.TRIM_DEADBAND * line:
                            lines = self.TRIM_LIMIT_LINES
                        if lines:
                            back, front = screen.porch
                            if back + lines >= 1:
                                screen.__set_porch(back + lines, front)
                                self.__corrections += 1
                                self.__anchor_skip[index] = True
                                residual += lines * line
                                logging.debug(f"screens: trimmed member {index} by"
                                              f" {lines:+} line to porch {screen.porch},"
                                              f" {residual:+.1f}us a period left")
                    self.__residual_us[index] = residual
        self.__anchor_stamp[index] = stamp
        self.__anchor_dither[index] = 0.0
        # Resolved nearest the booking: phases are modular, so a measurement is
        # only defined to within whole periods and the booking names which one.
        # That is what lets the bookings ride out a pause of any length.
        booked = self.__phase_us[index]
        raw = (((stamp - self.__grid_at) & TICKS_MASK) + self.__grid_phases[index]) % self.__target_us
        self.__phase_us[index] = booked + self.__fold(raw - booked)

    def __rebase(self, target, stamp):
        """Move the grid to a new period without disturbing the bookings.

        The grid's ideal falls keep their phase at the given instant and advance
        at the new period from it, so every booked error carries over unchanged.
        """
        self.__grid_phases = tuple(
            (((stamp - self.__grid_at) & TICKS_MASK) + phase) % self.__target_us
            for phase in self.__grid_phases)
        self.__grid_at = stamp
        self.__target_us = target

    def __release_hold(self, elapsed):
        """Stop holding the members' phases: they could not be brought back."""
        for index, screen in enumerate(self.screens):
            applied = self.__dither[index]
            if applied:
                back, front = screen.porch
                screen.__set_porch(back - applied, front)
                self.__dither[index] = 0
        # Back to the fall itself: with the constellation loose only the nominated
        # member comes out clean, and the fall is its own tuned phase.
        self.__sync_delay_us = 0
        self.__holding = False
        logging.info(f"screens: the panels could not be brought back into phase after a {elapsed // 1000}ms pause, so they are no longer being held together")
        if self.__trim == "rotate":
            # Moving the wait target is only free while the members fall together,
            # so freshness falls back to measuring one panel between frames.
            self.__trim = "probe"
            self.__starts = []

    def __tick_trim(self, synced=None):
        """Keep the members' rate models current between frames.

        A calibration goes stale as the panels warm, and a stale period costs an
        order of magnitude in what a prediction is worth, measured 2026-08-08.
        rotate moves the wait target to the next member each frame: each frame's
        stamp anchors the member it waited on, so every booking stays within a few
        periods of a measurement and nothing is probed. probe re-measures one
        member every TRIM_FRAMES through a capture, stalling the frame it lands on.
        """
        if not self.__trim:
            return

        members = self.screens
        if self.__trim == "rotate":
            # A frame that waited on someone else, or not at all, measured nothing,
            # so the target stays for the next frame to anchor.
            # Every member takes its turn, walking or not: the anchor is the only
            # thing that measures a member, so skipping one leaves it drifting on
            # a stale rate, which shows as a tear that walks. What a deep walk
            # needs is a porch floor that keeps its pulse readable, not a turn
            # missed.
            if synced is self.__sync:
                self.__trim_at = (members.index(self.__sync) + 1) % len(members)
                self.__sync = members[self.__trim_at]
            return

        self.__starts.append(0)
        if len(self.__starts) <= self.TRIM_FRAMES:
            return

        self.__starts = []
        index = self.__trim_at
        screen = members[index]
        self.__trim_at = (index + 1) % len(members)
        screen.command(screen.CONTROLLER.REG_TEON, b"\x00")
        falls, _ = screen.display.te_capture(4, 200)
        screen.command(screen.CONTROLLER.REG_TEOFF)
        if len(falls) > 1:
            measured = ((falls[-1] - falls[0]) & 0x3FFFFFFF) / (len(falls) - 1)
            # Each captured period carries a dithered porch line whole
            self.__correct(screen, measured - self.__dither[index] * self.__line_us[index])

    def __correct(self, screen, measured):
        """Move one member a line closer to the period the group holds.

        A held reference is not moved: the group's target follows it instead, so
        the whole fleet warming together is one number tracking and not several
        porches fighting it, and the grid is re-based so the bookings carry over.
        The reading also refreshes the rate the hold extrapolates with, whole
        lines or not: a stale one costs an order of magnitude, measured 2026-08-08.
        """
        if not measured or screen not in self.screens:
            return

        index = self.screens.index(screen)
        line = self.__line_us[index]
        if self.__holding and screen is self.__reference:
            # The target stays an int: the grid arithmetic is exact only while a
            # stamp's modulo is taken against whole microseconds.
            target = int(round(measured))
            if target != self.__target_us:
                self.__rebase(target, self.__held_stamp)
            self.__residual_us[index] = measured - target
            return
        lines = int(round((self.__target_us - measured) / line))
        limit = self.TRIM_LIMIT_LINES
        lines = limit if lines > limit else (-limit if lines < -limit else lines)
        if lines:
            back, front = screen.porch
            if back + lines < 1:
                lines = 0
            else:
                screen.__set_porch(back + lines, front)
                self.__corrections += 1
                logging.debug(f"screens: trimmed member {index} by"
                              f" {lines:+} line to porch {screen.porch},"
                              f" {measured:.0f}us against {self.__target_us:.0f}")
        if self.__holding:
            self.__residual_us[index] = measured + lines * line - self.__target_us
            if lines:
                self.__anchor_skip[index] = True

    @property
    def trim(self):
        """How the group keeps its members' periods current: rotate, probe or False."""
        return self.__trim

    @trim.setter
    def trim(self, value):
        if value not in (None, True, False, "rotate", "probe"):
            raise ValueError(f"{value} is not a valid trim. Expected None, False, 'rotate', or 'probe'.")

        if not self.__target_us:
            raise ValueError("this group holds no period for its members, so there is nothing for a trim to correct toward")

        if value in (None, True):
            value = "rotate" if self.__holding else False

        if value == "rotate" and not self.__holding:
            logging.info("screens: rotating the trim moves which member comes out clean, and these are held to one rate but not one phase, so every panel's tear moves with it")

        # A run of probe counts belongs to the mode that gathered it, so a change
        # begins its own run.
        self.__starts = []
        self.__trim = value

    @property
    def corrections(self):
        """Porch lines the trim has applied since construction, for a diagnostic."""
        return self.__corrections

    @property
    def exposed_frames(self):
        """Frames written with a member past its own tearing budget, for a diagnostic.

        A frame counted here may show a seam on that member; whether it does
        depends on how much the content changed. Only a held group counts, an
        unheld one having no phase to be outside of.
        """
        return self.__exposed_frames

    @property
    def worst_exposure_us(self):
        """How far past its budget the worst member of any exposed frame sat.

        Read against the group's tearing margin: a few tens of microseconds puts
        the seam within a line or two of an edge, where milliseconds put it in
        the middle of the glass.
        """
        return self.__worst_exposure_us

    def __period_of(self, screen, settle=False):
        """One member's refresh period, it alone asserting on the shared line.

        settle discards a first reading, which a panel fresh from bringup needs: it
        comes back about 3.4% long and settles within a second.
        """
        screen.command(screen.CONTROLLER.REG_TEON, b"\x00")
        if settle:
            screen.display.te_probe(self.PROBE_MS)
        period = screen.display.te_probe(self.PROBE_MS)[0]
        screen.command(screen.CONTROLLER.REG_TEOFF)
        return period

    def __unaligned(self, required, why):
        """Refuse an alignment that was required, or say why one asked for is unmet."""
        if required:
            raise ValueError(why)

        logging.info(f"screens: this group is not holding its panels in phase. {why}")

    @property
    def is_aligned(self):
        """Whether the members are held to one refresh rate.

        Their rates, not their phases: this stops them drifting apart, and on the
        glass it slows a tear band rather than removing one. is_in_phase is the
        state that makes a panel come out clean.
        """
        return self.__aligned

    @property
    def is_in_phase(self):
        """Whether the members' scans are being held together, not merely their rates.

        Held, not reached: acquisition brings them together at one instant and the
        residual rate spread pulls them apart again inside two periods, so only a
        hold makes this true for longer than a tenth of a second. It is what lets the
        wait target move, which is why the trim rotates on it.
        """
        if self.__subset_of is not None:
            return self.__subset_of.is_in_phase
        return self.__holding

    @property
    def acquired_us(self):
        """The phase spread the last acquisition reached, or 0 where it did not.

        A construction-time figure and not a running one: read is_in_phase for
        whether the members are together now.
        """
        if self.__subset_of is not None:
            return self.__subset_of.acquired_us
        return self.__acquired_us

    @property
    def reference(self):
        """The member every other is trimmed toward, the slowest of them, or None.

        None where the group is not aligned, since nothing was trimmed toward
        anything. is_aligned says the same thing and is the one to read.
        """
        return self.__reference

    @property
    def align_floor_us(self):
        """The skew the hold is predicted to settle within, or 0 when not aligned.

        An unmet align request is an outcome and not an error, so this reports zero
        where ScreenPair raises: a group falls back to its nominated member and
        carries on, and is_aligned is what distinguishes the two.
        """
        return self.__floor_us

    def subset(self, *screens, sync=None):
        """A member set over this group's display, writing only what it names.

        Cheap enough to make per frame: no display and no finaliser, just this
        group's own with a narrower set of members. A subset of one is allowed, so
        a loop over subsets does not break at the last.

        sync defaults to the group's own nomination, resolved per write since the
        nominated member need not be in the set. sync=False declines the wait for
        this set alone, leaving the group's nomination where it is.
        """
        if not screens:
            raise ValueError("a subset needs at least one screen")

        members = self.screens
        for screen in screens:
            if screen not in members:
                raise ValueError(f"{screen} is not a member of this group, so it cannot be in a subset of it")

        return ScreenGroup(*screens, sync=sync, parent=self.__subset_of or self)


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
        # The faster panel's own slot count, not the controller's default: a screen
        # whose porch has been moved spends a different number of them.
        line_slots = f_screen.line_slots
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
