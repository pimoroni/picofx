# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Cycling


class BlinkFX(Cycling):
    NAME = "blink"
    CALLED = None
    TAKES = ("speed", "phase", "duty")

    def __init__(self, speed=1, phase=0.0, duty=0.5):
        super().__init__(speed)
        self.phase = phase
        self.duty = duty

    def __call__(self):
        percent = (self.__offset + self.phase) % 1.0
        return 1.0 if percent < self.duty else 0.0


class BlinkWaveFX(Cycling):
    NAME = "blink_wave"
    CALLED = "position"
    TAKES = ("speed", "length", "phase", "duty")

    def __init__(self, speed=1, length=1, phase=0.0, duty=0.5):
        super().__init__(speed)
        self.length = length
        self.phase = phase
        self.duty = duty

    def __call__(self, pos):
        def fx():
            nonlocal pos
            phase = (pos / self.length)
            percent = (self.__offset + self.phase + phase) % 1.0
            return 1.0 if percent < self.duty else 0.0
        return self, fx
