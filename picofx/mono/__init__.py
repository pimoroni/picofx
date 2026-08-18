# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .binary import BinaryCounterFX
from .blink import BlinkFX, BlinkWaveFX
from .flash import FlashFX, FlashSequenceFX
from .flicker import FlickerFX
from .none import NoneFX
from .pelican import PelicanCrossingFX
from .pulse import PulseFX, PulseWaveFX
from .rand import RandomFX
from .static import StaticFX
from .sweep import SweepFX
from .traffic import TrafficLightFX

# Every effect here drives a plain light, and declares NAME as it is known outside
# code, CALLED as how a channel gets its callable, and TAKES as its settings.
MONO_EFFECTS = [
    BinaryCounterFX,
    BlinkFX,
    BlinkWaveFX,
    FlashFX,
    FlashSequenceFX,
    FlickerFX,
    NoneFX,
    PelicanCrossingFX,
    PulseFX,
    PulseWaveFX,
    RandomFX,
    StaticFX,
    SweepFX,
    TrafficLightFX,
]
