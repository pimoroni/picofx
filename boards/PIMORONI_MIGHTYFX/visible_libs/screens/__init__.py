# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# The screens a SP/CE port can drive. A screen type is a Screen subclass carrying
# its panel's settings.

from .base import ScreenBase, Tile
from .group import ScreenGroup
from .hub import ScreenHub
from .pair import ScreenPair, update_pair
from .screen import Reserve, Screen


class Screen154(Screen):
    """The 1.54" screen, 240 by 240 pixels."""

    SIZE = "1.54"
    WIDTH, HEIGHT = 240, 240

    # Every wire here is wire-bound, so a second core buys nothing and no row has a dual entry
    PROFILES = {
        # No 24MHz 16-bit, too slow to finish a frame inside the controller's slowest refresh
        (24_000_000, 12): {"band_lines": 2, "cache_columns": 0, "framerate": 53},
        (37_500_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 60},
        (37_500_000, 12): {"band_lines": 12, "cache_columns": 12, "framerate": 60},
        (75_000_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 60},
        # No 75MHz 12-bit, so fast the write overtakes the panel's scan and tears near the top
    }

    FULL_IMAGE_RESERVE = {
        # The shallowest ring holding a pair wire-bound at either rotation, no column cache needed
        (24_000_000, 12): {"stage_lines": 120, "cache_columns": 0},
        # No 37.5MHz or 75MHz rows, so fast that conversion sets the pace whatever the ring holds
    }


class Screen280(Screen):
    """The 2.8" screen, 240 by 320 pixels."""

    SIZE = "2.8"
    WIDTH, HEIGHT = 240, 320

    # Each rate is a controller step below the measured tearing onset, so a fast panel
    # oscillator still has margin. A dual row is a wire one core could not keep fed.
    PROFILES = {
        # No 24MHz 16-bit, too slow to finish a frame inside the controller's slowest refresh
        (24_000_000, 12): {"band_lines": 4, "cache_columns": 4, "framerate": 45},
        (37_500_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 52},
        (37_500_000, 12): {"band_lines": 12, "cache_columns": 12, "framerate": 55,
                           "dual": {"band_lines": 12, "cache_columns": 12, "framerate": 60}},
        (75_000_000, 16): {"band_lines": 12, "cache_columns": 12, "framerate": 53,
                           "dual": {"band_lines": 12, "cache_columns": 12, "framerate": 60}},
        # No 75MHz 12-bit, so fast the write overtakes the panel's scan and tears near the top
    }

    FULL_IMAGE_RESERVE = {
        # The shallowest ring holding a pair wire-bound
        (24_000_000, 12): {"stage_lines": 160, "cache_columns": 12},
        # No 37.5MHz or 75MHz rows, so fast that conversion sets the pace whatever the ring holds
    }


# Every screen type by the size it declares, which is where a new type is registered
SCREEN_TYPES = {screen.SIZE: screen for screen in (Screen154, Screen280)}
