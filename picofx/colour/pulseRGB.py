# SPDX-FileCopyrightText: 2025 Tom Hallam for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import math
from picofx import Cycling


class PulseRGBFX(Cycling):
    def __init__(self, speed=1, phase=0, brightness=1.0, r=255, g=0, b=0):
        super().__init__(speed)
        self.phase = phase
        self.brightness = brightness
        self.red = r
        self.green = g
        self.blue = b

    def __call__(self):
        angle = (self.__offset + self.phase) * math.pi * 2

        r = self.red * self.brightness * ((math.sin(angle) + 1) / 2.0)
        g = self.green * self.brightness * ((math.sin(angle) + 1) / 2.0)
        b = self.blue * self.brightness * ((math.sin(angle) + 1) / 2.0)
        
        return max(min(r, 255), 0), \
            max(min(g, 255), 0), \
            max(min(b, 255), 0)
