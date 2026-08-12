# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# One panel on an SP/CE port. A screen type is a class carrying its panel's
# settings, so a new size is a subclass setting a few attributes and a one-off is
# a keyword override. PROFILES carries the measured tuning per wire, so a
# construction naming only a baud rate lands on settings profiling chose, and
# CONTROLLER names the module supplying the bringup sequence, so the chip stays an
# independent axis from the panel size.

import spidisplay
import st7789

from .base import ScreenBase


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


class Screen(ScreenBase):
    """One panel on an SP/CE port.

    The first screen on a port names no pins and takes the port's own DC, CS and
    backlight. Every further screen names its cs, and its dc unless it is
    deliberately sharing the port's. A screen built against one of a ScreenHub's
    ports names none of them, the hub having named the whole line-up already.

    te names the line the tearing-effect signal comes back on. True is this screen's
    own DC line, which is how MightyFX wires a single panel to a port; the port's own
    DC line is one other screens share, which needs a diode on each breakout and
    asserts TE only for the frame waiting on it; any other Pin is a dedicated input;
    False sends TEOFF and never waits. None takes the port's default, which is True
    on a connector and the shared line on a hub. v_sync follows te, and False keeps
    the signal without waiting on it. bl=False declines the port's backlight, for a
    panel whose own is tied on at the assembly.

    Where te is in play, construction refuses if no panel answers on that line, which
    is how an empty port or an unplugged panel reports itself instead of running as a
    screen nothing can see. A refusing screen claims nothing, so a caller may build a
    line-up over a hub and keep whichever built. A panel wired without its
    tearing-effect signal takes te=False and is not looked for, there being nothing to
    look for.

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
    PROBE_MS = 60            # a present panel always answers inside this
    PATIENT_PROBE_MS = 250   # the second look, paid only by a line with nothing on it
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

    # Measured tuning per (baudrate, bitdepth), from a 21,600-cell sweep of the
    # full-PSRAM case: the band and cache holding the rotation-90 floor, and the
    # highest controller rate that floor sustains (capped at the useful 60fps). A
    # row may carry a "dual" replacement for a firmware converting on both cores,
    # which is a rate its wire could not hold while one core was what it waited for.
    PROFILES = {}

    def __init__(self, port, cs=None, dc=None, te=None, v_sync=None, bl=True,
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
            profile = self.__for_cores(profile, dual_profiles,
                                       ("band_lines", "cache_columns", "framerate"),
                                       "PROFILES")

        # reserve picks the measured recipe; a named band, cache or stage still wins,
        # so a profiling run can construct anything.
        if reserve == Reserve.FULL_SIZE_IMAGES:
            recipe = self.FULL_IMAGE_RESERVE.get((self.__baudrate, bitdepth))
            if recipe is None:
                raise ValueError(f"Reserve.FULL_SIZE_IMAGES has no measured recipe for {type(self).__name__} at {self.__baudrate}Hz {bitdepth}-bit. Measure one, or name stage_lines and cache_columns.")

            recipe = self.__for_cores(recipe, dual_profiles,
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
        bd_code = self.__code_for(controller.PIXEL_FORMAT, bitdepth, "bit depth")
        fr_code = self.__code_for(controller.FRAME_RATE_CONTROL, self.__framerate, "frame rate")

        if te is None:
            te = port.default_te

        te_used = te is not False
        named_line = te if te_used and te is not True else None

        # Naming the port's DC line, where True names this panel's own, is what
        # declares the diode each breakout on a shared line needs. One panel at a
        # time may assert there, so the driver sends TEON as a frame's wait begins
        # and TEOFF as it ends.
        shared_te = named_line is not None and named_line is port.dc

        # A DC line is read by flipping it to an input for the wait, which the driver
        # does only where it holds no TE pin of its own. So a shared line is declared
        # by name here and passed as none: a pin means a dedicated input, and giving
        # it the DC line leaves that line an output and the wait reading what this
        # board is driving.
        te_pin = None if shared_te else named_line

        if v_sync is None:
            v_sync = te_used
        elif v_sync and not te_used:
            raise ValueError("v_sync waits on the panel's tearing-effect signal, which te=False turns off")

        # Checked here and claimed once the panel has answered, so a screen that
        # refuses reserves neither line
        cs = port.check_cs(cs)
        dc = port.check_dc(dc, te_used, shared_te)

        # The line TE is read from, which a pair's excursion scheduler watches
        self.__te_line = (te_pin if te_pin is not None else dc) if te_used else None

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
            display.__del__()
            raise ValueError(f"this wire reached {achieved} baud of the {self.__baudrate} requested."
                             f" Raise clk_peri first, machine.freq(150_000_000, 150_000_000),"
                             f" or request a rate the current clock reaches.")

        # Bringup goes through the display rather than this screen, so the panel is
        # up and answering before anything on the port is claimed for it.
        #
        # A shared line comes up at TEOFF: the driver asserts TE only for the frame
        # that waits on it, since one panel at a time may reach the line.
        #
        # A hub has already reset and cleared every panel on the port, in one pass
        # over all of them. On its own a screen does both for itself, the clear
        # being what keeps the panel's power-on contents off the glass when the
        # backlight comes up.
        alone = not port.panels_reset
        if alone:
            controller.reset(display)

        controller.setup(display, width, height, bd_code, fr_code, te_used and not shared_te)

        if te_used and not self.__answered(display, controller, shared_te):
            display.__del__()
            raise ValueError(f"no screen answered on {cs}. Check it is plugged in, or pass"
                             f" te=False for a screen whose tearing-effect signal is not wired,"
                             f" which also turns off waiting for it.")

        port.claim_cs(cs)
        port.claim_dc(dc, te_used, shared_te)
        backlight = port.claim_backlight() if bl else None

        super().__init__(port.connector, display, width, height, bitdepth, backlight,
                         te_used, v_sync, reserve, shared_te=shared_te,
                         sync=self if shared_te else None)

        port.register(self)

        # What setup() wrote, and the slots that porch spends. A group's trim moves
        # both, so every margin sum reads them from the screen.
        self.__porch = controller.PORCH
        self.__line_slots = controller.LINE_SLOTS

        if alone:
            display.fill()

    @staticmethod
    def __answered(display, controller, shared):
        """Whether a panel drove the tearing-effect line, which says one is there.

        A present panel answers inside PROBE_MS, measured over 100 probes against a
        22 to 25ms period. The longer second look is what an empty line pays: two
        silences are wanted before refusing a screen, since a panel is only reported
        missing once, and it happens where nothing else can contradict it.
        """
        if shared:
            # One panel at a time may assert on a shared line, so this one is asked
            # for the probe and released again
            display.command(controller.REG_TEON, bytes((controller.TE_MODE,)))

        answered = display.te_probe(Screen.PROBE_MS)[2] > 0
        if not answered:
            answered = display.te_probe(Screen.PATIENT_PROBE_MS)[2] > 0

        if shared:
            display.command(controller.REG_TEOFF)

        return answered

    @staticmethod
    def __code_for(table, value, what):
        """Look a panel setting up in one of the controller's code tables."""
        try:
            return table[value]
        except KeyError as e:
            items = [str(key) for key in table]
            expected = items[0] if len(items) == 1 else ", ".join(items[:-1]) + f", or {items[-1]}"
            raise ValueError(f"{value} is not a valid {what}. Expected {expected}.") from e

    @staticmethod
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

    @property
    def framerate(self):
        """The refresh rate this screen was built with, which bounds the tearing margin.

        A label, nominal at the default porch: alignment trims the porch to hold
        panels together, so an aligned panel runs off it. line_slots against the
        controller's LINE_SLOTS says how far.
        """
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
