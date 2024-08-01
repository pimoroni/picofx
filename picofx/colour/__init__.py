# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .colour import RGBFX, HSVFX
from .rainbow import RainbowFX, RainbowWaveFX
from .step import HueStepFX

COLOUR_EFFECTS = [
    RGBFX,
    HSVFX,
    RainbowFX,
    RainbowWaveFX,
    HueStepFX
]
