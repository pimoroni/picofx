# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .blink import RGBBlinkFX
from .colour import HSVFX, RGBFX
from .rainbow import RainbowFX, RainbowWaveFX
from .step import HueStepFX

# Colour constants (in RGB)
RED = (255, 0, 0)
ORANGE = (255, 128, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (128, 0, 255)
MAGENTA = (255, 0, 255)
PINK = (255, 128, 128)
WARM = (255, 192, 96)
WHITE = (255, 255, 255)
COOL = (96, 192, 255)
BLACK = (0, 0, 0)

# Colour constants (in HSV)
H_RED = (0 / 6, 1, 1)
H_ORANGE = (0.5 / 6, 1, 1)
H_GREEN = (2 / 6, 1, 1)
H_BLUE = (4 / 6, 1, 1)
H_CYAN = (3 / 6, 1, 1)
H_PURPLE = (4.5 / 6, 1, 1)
H_MAGENTA = (5 / 6, 1, 1)
H_YELLOW = (1 / 6, 1, 1)
H_PINK = (0, 0.498, 1)
H_WARM = (0.1, 0.624, 1)
H_WHITE = (0, 0, 1)
H_COOL = (0.566, 0.624, 1)
H_BLACK = (0, 0, 0)

# Every effect here brings its own colour, and declares NAME as it is known outside
# code, CALLED as how a channel gets its callable, and TAKES as its settings.
COLOUR_EFFECTS = [
    RGBFX,
    HSVFX,
    RainbowFX,
    RainbowWaveFX,
    HueStepFX,
    RGBBlinkFX
]
