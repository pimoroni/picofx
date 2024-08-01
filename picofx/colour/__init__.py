# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .colour import RGBFX, HSVFX
from .rainbow import RainbowFX, RainbowWaveFX
from .step import HueStepFX

RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
MAGENTA = (255, 0, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

COLOUR_EFFECTS = [
    RGBFX,
    HSVFX,
    RainbowFX,
    RainbowWaveFX,
    HueStepFX
]
