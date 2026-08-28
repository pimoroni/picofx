# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import math

from picofx import Cycling

# A whole turn, calculated once so a call reaches neither the module nor its attribute
TAU = math.pi * 2


class PulseFX(Cycling):
    NAME = "pulse"
    CALLED = None
    TAKES = ("speed", "phase")

    def __init__(self, speed=1, phase=0):
        super().__init__(speed)
        self.phase = phase

    def __call__(self):
        angle = (self.__offset + self.phase) * TAU
        return (math.sin(angle) + 1) / 2.0


class PulseWaveFX(Cycling):
    NAME = "pulse_wave"
    CALLED = "position"
    TAKES = ("speed", "length", "phase")

    def __init__(self, speed=1, length=1, phase=0.0):
        super().__init__(speed)
        self.length = length
        self.phase = phase

    def __call__(self, pos):
        def fx():
            nonlocal pos
            phase = pos / self.length
            angle = (self.__offset + self.phase + phase) * TAU
            return (math.sin(angle) + 1) / 2.0
        return self, fx
