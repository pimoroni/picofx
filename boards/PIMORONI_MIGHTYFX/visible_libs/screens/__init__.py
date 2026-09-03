# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# The screens an SP/CE port can drive. A screen type is a Screen subclass carrying
# its panel's settings, PROFILES being the measured tuning per wire.

from .base import ScreenBase, Tile
from .group import ScreenGroup
from .hub import ScreenHub
from .pair import ScreenPair, update_pair
from .screen import Reserve, Screen


class Screen154(Screen):
    SIZE = "1.54"
    WIDTH, HEIGHT = 240, 240
    # Two wires have no row. 24MHz 16-bit: that frame outruns the controller's slowest
    # rate. 75MHz 12-bit: that wire overtakes the panel's scan near the top of the frame.
    PROFILES = {
        (24_000_000, 12): {"band_lines": 2, "cache_columns": 0, "framerate": 53},
        (37_500_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 60},
        (37_500_000, 12): {"band_lines": 12, "cache_columns": 12, "framerate": 60},
        (75_000_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 60},
    }

    # The shallowest ring holding a pair wire-bound at either rotation; a column cache buys nothing here
    FULL_IMAGE_RESERVE = {
        (24_000_000, 12): {"stage_lines": 120, "cache_columns": 0},
    }


class Screen280(Screen):
    SIZE = "2.8"
    WIDTH, HEIGHT = 240, 320
    # No 12-bit row at 75MHz, as for the 1.54". Each rate is a controller step below the
    # measured tearing onset, so a fast panel oscillator still has margin. The dual rows
    # are the wires one core could not keep fed.
    PROFILES = {
        (24_000_000, 12): {"band_lines": 4, "cache_columns": 4, "framerate": 45},
        (37_500_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 52},
        (37_500_000, 12): {"band_lines": 12, "cache_columns": 12, "framerate": 55,
                           "dual": {"band_lines": 12, "cache_columns": 12, "framerate": 60}},
        (75_000_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 53,
                           "dual": {"band_lines": 12, "cache_columns": 12, "framerate": 60}},
    }

    # The shallowest ring holding a pair wire-bound; the faster wires have no row since a
    # shorter wire row makes the frame conversion-bound whatever the ring holds
    FULL_IMAGE_RESERVE = {
        (24_000_000, 12): {"stage_lines": 160, "cache_columns": 12},
    }


# Every screen type by the size it declares, so a new size is added here alone
SCREEN_TYPES = {screen.SIZE: screen for screen in (Screen154, Screen280)}
