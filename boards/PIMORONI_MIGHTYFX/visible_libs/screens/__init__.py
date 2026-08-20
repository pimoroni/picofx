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

from .base import ScreenBase, Tile
from .group import ScreenGroup
from .hub import ScreenHub
from .pair import ScreenPair, update_pair
from .screen import Reserve, Screen


class Screen154(Screen):
    SIZE = "1.54"
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
    SIZE = "2.8"
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


# Every screen type, keyed by the size each one declares, so a new size is a subclass
# added here and nothing else has to name it again
SCREEN_TYPES = {screen.SIZE: screen for screen in (Screen154, Screen280)}
