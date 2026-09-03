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

from .base import ScreenBase, __check_rotation


class Reserve:
    """What a screen's share of the fast SRAM is set aside for."""
    CANVAS_SPACE = 0        # Only what a frame needs, leaving the region for canvas()
    FULL_SIZE_IMAGES = 1    # Room for two screens to each convert a full-size heap image


class Screen(ScreenBase):
    """One panel on an SP/CE port."""

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
                 cache_columns=None, stage_lines=None, dual_profiles=None,
                 rotation=0, mirror=False, reveal_together=False):

        # Ahead of the pin claims and the bringup below, so a bad angle costs
        # neither, the port otherwise being left holding claims for a screen
        # that never finished
        __check_rotation(rotation)

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
            te = port.__default_te

        te_used = te is not False
        named_line = te if te_used and te is not True else None

        # Naming the port's DC line, where True names this panel's own, is what
        # declares the diode each breakout on a shared line needs. One panel at a
        # time may assert there, so the driver sends TEON as a frame's wait begins
        # and TEOFF as it ends.
        shared_te = named_line is not None and named_line is port.__dc_line

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
        cs = port.__check_cs(cs)
        dc = port.__check_dc(dc, te_used, shared_te)

        # The line TE is read from, which a pair's excursion scheduler watches
        self.__te_line = (te_pin if te_pin is not None else dc) if te_used else None

        display = spidisplay.SPIDisplay(bus=port.__bus, cs=cs, dc=dc, te=te_pin,
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
        alone = not port.__panels_reset
        if alone:
            controller.reset(display)

        controller.setup(display, width, height, bd_code, fr_code, te_used and not shared_te)

        if te_used and not self.__answered(display, controller, shared_te):
            display.__del__()
            raise ValueError(f"no screen answered on {cs}. Check it is plugged in, or pass"
                             f" te=False for a screen whose tearing-effect signal is not wired,"
                             f" which also turns off waiting for it.")

        port.__claim_cs(cs)
        port.__claim_dc(dc, te_used, shared_te)
        backlight = port.__claim_backlight() if bl else None

        super().__init__(port.__connector, display, width, height, bitdepth, backlight,
                         te_used, v_sync, reserve, shared_te=shared_te,
                         leader=self if shared_te else None,
                         rotation=rotation, mirror=mirror,
                         reveal_together=reveal_together)

        port.__register(self)

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
        """The refresh rate this screen was built with; an aligned panel is trimmed off it."""
        return self.__framerate

    def __set_porch(self, back, front):
        """Move this panel's refresh period by whole scan lines.

        One porch line is one line time. The setting a caller reaches for is the
        group's align; this is the mechanism it moves a member with.
        """
        if back < 1 or front < 1:
            raise ValueError(f"a porch of ({back}, {front}) has a side under one line, which the controller has no code for")

        self.CONTROLLER.set_porch(self.__display, back, front)
        self.__porch = (back, front)
        self.__line_slots = self.CONTROLLER.CONTROLLER_ROWS + back + front

    @property
    def requested_baudrate(self):
        """The rate this panel asked for, against display.baudrate()'s achieved one."""
        return self.__baudrate
