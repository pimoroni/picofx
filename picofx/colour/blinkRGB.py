# SPDX-FileCopyrightText: 2025 Tom Hallam for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Cycling


class BlinkRGBFX(Cycling):
    def __init__(self, speed=1, phase=0.0, duty=0.5, brightness=1.0, r=255, g=0, b=0):
        super().__init__(speed)
        self.phase = phase
        self.duty = duty
        self.brightness = brightness
        self.red = r
        self.green = g
        self.blue = b

    def __call__(self):
        percent = (self.__offset + self.phase) % 1.0
        if percent < self.duty:
            r = self.red * self.brightness
            g = self.green * self.brightness
            b = self.blue * self.brightness

            return max(min(r, 255), 0), \
                max(min(g, 255), 0), \
                max(min(b, 255), 0)
        else:
            return 0, 0, 0
