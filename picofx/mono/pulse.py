# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import math
from picofx import Cycling


class PulseFX(Cycling):
    def __init__(self, speed=1, phase=0):
        super().__init__(speed)
        self.phase = phase

    def __call__(self):
        angle = (self.__offset + self.phase) * math.pi * 2
        return (math.sin(angle) + 1) / 2.0


class PulseWaveFX(Cycling):
    def __init__(self, speed=1, length=1, phase=0.0):
        super().__init__(speed)
        self.length = length
        self.phase = phase

    def __call__(self, pos):
        def fx():
            nonlocal pos
            phase = pos / self.length
            angle = (self.__offset + self.phase + phase) * math.pi * 2
            return (math.sin(angle) + 1) / 2.0
        return self, fx
