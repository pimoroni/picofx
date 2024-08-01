# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Cycling, rgb_from_hsv


class RainbowFX(Cycling):
    def __init__(self, speed=1.0, sat=1.0, val=1.0):
        Cycling.__init__(self, speed)
        self.sat = sat
        self.val = val

    def __call__(self):
        r, g, b = rgb_from_hsv(self.__offset, self.sat, self.val)
        return int(r * 255), int(g * 255), int(b * 255)


class RainbowWaveFX(Cycling):
    def __init__(self, speed=1, length=1, sat=1, val=1):
        super().__init__(speed)
        self.length = length
        self.sat = sat
        self.val = val

    def __call__(self, pos):
        def fx():
            nonlocal pos
            phase = pos / self.length
            hue = (self.__offset + phase) % 1.0
            r, g, b = rgb_from_hsv(hue, self.sat, self.val)
            return int(r * 255), int(g * 255), int(b * 255)
        return self, fx
