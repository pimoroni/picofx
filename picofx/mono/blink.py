# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Cycling


class BlinkFX(Cycling):
    """A blink on and off shared by every output it drives."""

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
    """A blink that travels along the outputs with each a step behind the one before."""

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
