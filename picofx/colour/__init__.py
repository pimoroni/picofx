# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .blink import RGBBlinkFX
from .colour import HSVFX, RGBFX
from .rainbow import RainbowFX, RainbowWaveFX
from .step import HueStepFX

# Colour constants (in RGB)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
MAGENTA = (255, 0, 255)
WARM = (255, 192, 96)
WHITE = (255, 255, 255)
COOL = (96, 192, 255)
BLACK = (0, 0, 0)

# Colour constants (in HSV)
H_RED = (0 / 6, 1, 1)
H_GREEN = (2 / 6, 1, 1)
H_BLUE = (4 / 6, 1, 1)
H_CYAN = (3 / 6, 1, 1)
H_MAGENTA = (5 / 6, 1, 1)
H_YELLOW = (1 / 6, 1, 1)
H_WARM = (0.1, 0.624, 1)
H_WHITE = (0, 0, 1)
H_COOL = (0.56, 0.624, 1)
H_BLACK = (0, 0, 0)

COLOUR_EFFECTS = [
    RGBFX,
    HSVFX,
    RainbowFX,
    RainbowWaveFX,
    HueStepFX,
    RGBBlinkFX
]
