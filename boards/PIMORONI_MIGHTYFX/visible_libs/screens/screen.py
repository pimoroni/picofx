# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# One panel on a SP/CE port. A screen type is a subclass carrying its panel's
# settings. Screen154 and Screen280 in __init__.py are the shipped ones.

import spidisplay
import st7789

from .base import ScreenBase, __check_rotation


class Reserve:
    """What a screen's share of the fast SRAM is set aside for."""
    CANVAS_SPACE = 0        # Only what a frame needs, leaving the rest for canvas()
    FULL_SIZE_IMAGES = 1    # Room to convert a full-size heap image while a paired screen does the same


class Screen(ScreenBase):
    """One panel on a SP/CE port."""

    CONTROLLER = st7789      # Bringup, the rate and depth code tables, the porch and the rows a refresh scans
    PROBE_MS = 60            # A present panel always answers inside this
    PATIENT_PROBE_MS = 250   # The second look, paid only by a line with nothing on it
    WIDTH = HEIGHT = None
    BITDEPTH = 16
    FRAMERATE = 60
    BAUDRATE = 24_000_000
    BAND_LINES = 12          # The measured band a wire outside PROFILES falls back on
    CACHE_COLUMNS = 12       # The measured cache width a wire outside PROFILES falls back on
    DEPTHS = (16, 12)        # Default bit depth preference, first row wins

    # Reserve.FULL_SIZE_IMAGES recipes per (baudrate, bitdepth), being the ring depth
    # and cache width measured to hold a pair wire-bound. A wire with no row is refused.
    FULL_IMAGE_RESERVE = {}

    # Measured tuning per (baudrate, bitdepth), being the band, cache and highest rate
    # that hold at rotation 90. A "dual" entry replaces the row on a two-core firmware.
    PROFILES = {}

    def __init__(self, port, cs=None, dc=None, te=None, v_sync=None, bl=True,
                 width=None, height=None, bitdepth=None, framerate=None,
                 baudrate=None, reserve=Reserve.CANVAS_SPACE, band_lines=None,
                 cache_columns=None, stage_lines=None, dual_profiles=None,
                 rotation=0, mirror=False, reveal_together=False):

        # Before any claim, so a bad angle leaves the port holding nothing
        __check_rotation(rotation)

        width = self.WIDTH if width is None else width
        height = self.HEIGHT if height is None else height
        self.__baudrate = self.BAUDRATE if baudrate is None else baudrate

        # dual_convert() is off on a firmware with no second core to convert on
        if dual_profiles is None:
            dual_profiles = spidisplay.dual_convert()

        if bitdepth is None:
            for depth in self.DEPTHS:
                if (self.__baudrate, depth) in self.PROFILES:
                    bitdepth = depth
                    break
            else:
                bitdepth = self.BITDEPTH

        # An off-table pair falls back to the class constants, so a new wire can be profiled
        profile = self.PROFILES.get((self.__baudrate, bitdepth))
        if profile is None:
            profile = {"band_lines": self.BAND_LINES,
                       "cache_columns": self.CACHE_COLUMNS,
                       "framerate": self.FRAMERATE}
        else:
            profile = self.__for_cores(profile, dual_profiles,
                                       ("band_lines", "cache_columns", "framerate"),
                                       "PROFILES")

        if reserve == Reserve.FULL_SIZE_IMAGES:
            recipe = self.FULL_IMAGE_RESERVE.get((self.__baudrate, bitdepth))
            if recipe is None:
                raise ValueError("Reserve.FULL_SIZE_IMAGES has no measured recipe for "
                                 f"{type(self).__name__} at {self.__baudrate}Hz {bitdepth}-bit. "
                                 "Measure one, or name stage_lines and cache_columns.")

            recipe = self.__for_cores(recipe, dual_profiles,
                                      ("stage_lines", "cache_columns"),
                                      "FULL_IMAGE_RESERVE")

            if stage_lines is None:
                stage_lines = recipe["stage_lines"]
            if cache_columns is None:
                cache_columns = recipe["cache_columns"]
        elif reserve != Reserve.CANVAS_SPACE:
            raise ValueError(f"{reserve} is not a valid reserve. Expected Reserve.CANVAS_SPACE, or "
                             "Reserve.FULL_SIZE_IMAGES.")

        band_lines = profile["band_lines"] if band_lines is None else band_lines
        cache_columns = profile["cache_columns"] if cache_columns is None else cache_columns
        self.__framerate = profile["framerate"] if framerate is None else framerate
        stage_lines = 0 if stage_lines is None else stage_lines

        if width is None or height is None:
            raise ValueError(f"{type(self).__name__} sets no WIDTH and HEIGHT. Subclass Screen and "
                             "set them, or pass them here.")

        controller = self.CONTROLLER
        bd_code = self.__code_for(controller.PIXEL_FORMAT, bitdepth, "bit depth")
        fr_code = self.__code_for(controller.FRAME_RATE_CONTROL, self.__framerate, "frame rate")

        if te is None:
            te = port.__default_te

        te_used = te is not False
        named_line = te if te_used and te is not True else None

        # Naming the port's DC line declares a shared TE line, one panel asserting at a
        # time. The driver reads a DC line by flipping it to an input, so a shared
        # line is passed as no pin, a pin here meaning a dedicated input.
        shared_te = named_line is not None and named_line is port.__dc_line
        te_pin = None if shared_te else named_line

        if v_sync is None:
            v_sync = te_used
        elif v_sync and not te_used:
            raise ValueError("v_sync waits on the panel's tearing-effect signal, which te=False turns off")

        # Claimed only once the panel has answered, so a refusal reserves nothing
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

        # The divider rounds a request down, so a profile measured at 37.5MHz would
        # otherwise run its tuning on a 24MHz wire
        achieved = display.baudrate()
        if achieved < self.__baudrate:
            # The display claimed SRAM at construction, so a refusal hands it back
            display.__del__()
            raise ValueError(f"this wire reached {achieved} baud of the {self.__baudrate} requested. "
                             f"Raise clk_peri first, machine.freq(150_000_000, 150_000_000), "
                             f"or request a rate the current clock reaches.")

        # A hub has already reset and cleared every panel on the port, so a screen on
        # its own does both. A shared line comes up at TEOFF.
        alone = not port.__panels_reset
        if alone:
            controller.reset(display)

        controller.setup(display, width, height, bd_code, fr_code, te_used and not shared_te)

        if te_used and not self.__answered(display, controller, shared_te):
            display.__del__()
            raise ValueError(f"no screen answered on {cs}. Check it is plugged in, or pass "
                             f"te=False for a screen whose tearing-effect signal is not wired, "
                             f"which also turns off waiting for it.")

        port.__claim_cs(cs)
        port.__claim_dc(dc, te_used, shared_te)
        backlight = port.__claim_backlight() if bl else None

        super().__init__(port.__connector, display, width, height, bitdepth, backlight,
                         te_used, v_sync, reserve, shared_te=shared_te,
                         leader=self if shared_te else None,
                         rotation=rotation, mirror=mirror,
                         reveal_together=reveal_together)

        port.__register(self)

        # setup()'s porch and the scan slots it implies, both kept current by __set_porch
        self.__porch = controller.PORCH
        self.__line_slots = controller.LINE_SLOTS

        if alone:
            display.fill()

    def __answered(self, display, controller, shared):
        # A present panel answers inside PROBE_MS. An empty line gets a second, longer
        # look, since a missing panel is reported once and nothing can contradict it.
        if shared:
            # One panel at a time may assert on a shared line, so ask and release
            display.command(controller.REG_TEON, bytes((controller.TE_MODE,)))

        answered = display.te_probe(self.PROBE_MS)[2] > 0
        if not answered:
            answered = display.te_probe(self.PATIENT_PROBE_MS)[2] > 0

        if shared:
            display.command(controller.REG_TEOFF)

        return answered

    @staticmethod
    def __code_for(table, value, what):
        try:
            return table[value]
        except KeyError as e:
            items = [str(key) for key in table]
            expected = items[0] if len(items) == 1 else ", ".join(items[:-1]) + f", or {items[-1]}"
            raise ValueError(f"{value} is not a valid {what}. Expected {expected}.") from e

    @staticmethod
    def __for_cores(row, dual, required, what):
        # A "dual" entry is the whole row again, so a single-core edit cannot leak into it
        if not dual or "dual" not in row:
            return row

        override = row["dual"]
        missing = [key for key in required if key not in override]
        if missing:
            raise ValueError(f"the dual-core {what} row names {', '.join(missing)} nowhere. It "
                             "replaces the single-core row rather than amending it, so it needs "
                             "every setting that row has.")

        return override

    @property
    def framerate(self):
        """The refresh rate this screen was built with. Alignment may move a panel a little off it."""
        return self.__framerate

    def __set_porch(self, back, front):
        # One porch line is one line time, and a group's align moves a member with this
        if back < 1 or front < 1:
            raise ValueError(f"a porch of ({back}, {front}) has a side under one line, which the "
                             "controller has no code for")

        self.CONTROLLER.set_porch(self.__display, back, front)
        self.__porch = (back, front)
        self.__line_slots = self.CONTROLLER.CONTROLLER_ROWS + back + front

    @property
    def requested_baudrate(self):
        """The rate this panel asked for, against display.baudrate()'s achieved one."""
        return self.__baudrate
