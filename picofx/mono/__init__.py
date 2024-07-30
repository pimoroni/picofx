# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .binary import BinaryCounterFX
from .blink import BlinkFX, BlinkWaveFX
from .flash import FlashFX, FlashSequenceFX
from .flicker import FlickerFX
from .pulse import PulseFX, PulseWaveFX
from .rand import RandomFX
from .static import StaticFX
from .traffic import TrafficLightFX

MONO_EFFECTS = [
    BinaryCounterFX,
    BlinkFX,
    BlinkWaveFX,
    FlashFX,
    FlashSequenceFX,
    FlickerFX,
    PulseFX,
    PulseWaveFX,
    RandomFX,
    StaticFX,
    TrafficLightFX,
]
