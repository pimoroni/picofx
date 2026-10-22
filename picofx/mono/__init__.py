# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .binary import BinaryCounterFX
from .blink import BlinkFX, BlinkWaveFX
from .flash import FlashFX, FlashSequenceFX
from .flicker import FlickerEachFX, FlickerFX
from .none import NoneFX
from .pelican import PelicanCrossingFX
from .pulse import PulseFX, PulseWaveFX
from .rand import RandomEachFX, RandomFX
from .static import StaticFX
from .sweep import SweepFX
from .traffic import TrafficLightFX

# The effects that give a brightness. Each declares NAME as the word it is known by, CALLED for
# how a channel gets its callable and TAKES for its settings
MONO_EFFECTS = [
    BinaryCounterFX,
    BlinkFX,
    BlinkWaveFX,
    FlashFX,
    FlashSequenceFX,
    FlickerFX,
    FlickerEachFX,
    NoneFX,
    PelicanCrossingFX,
    PulseFX,
    PulseWaveFX,
    RandomFX,
    RandomEachFX,
    StaticFX,
    SweepFX,
    TrafficLightFX,
]
