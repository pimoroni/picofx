# SPDX-FileCopyrightText: 2025 Tom Hallam for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import random
from picofx import Updateable


class RandomRGBFX(Updateable):
    def __init__(self, interval=0.05, brightness_min=0.0, brightness_max=1.0, r=255, g=0, b=0):
        self.interval = interval
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max
        self.red = r
        self.green = g
        self.blue = b
        self.__time = 0
        self.__brightness = random.uniform(self.brightness_min, self.brightness_max)

    def __call__(self):
        r = self.red * self.__brightness
        g = self.green * self.__brightness
        b = self.blue * self.__brightness

        return max(min(r, 255), 0), \
            max(min(g, 255), 0), \
            max(min(b, 255), 0)

    def tick(self, delta_ms):
        self.__time += delta_ms

        # Check if the interval has elapsed
        if self.__time >= (self.interval * 1000):
            self.__time -= (self.interval * 1000)

            self.__brightness = random.uniform(self.brightness_min, self.brightness_max)
