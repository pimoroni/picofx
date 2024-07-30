# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from .binary import BinaryCounterFX
from .blink import BlinkFX, BlinkWaveFX
from .emergency import EmergencyFX
from .flicker import FlickerFX
from .pelican import PelicanLightFX
from .pulse import PulseFX, PulseWaveFX
from .rand import RandomFX
from .static import StaticFX
from .traffic import TrafficLightFX

MONO_EFFECTS = [
    BinaryCounterFX,
    BlinkFX,
    BlinkWaveFX,
    EmergencyFX,
    FlickerFX,
    PelicanLightFX,
    PulseFX,
    PulseWaveFX,
    RandomFX,
    StaticFX,
    TrafficLightFX,
]
