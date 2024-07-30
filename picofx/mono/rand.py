# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import random
from picofx import Updateable


class RandomFX(Updateable):
    def __init__(self, interval=0.05, brightness_min=0.0, brightness_max=1.0):
        self.interval = interval
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max
        self.__time = 0
        self.__brightness = random.uniform(self.brightness_min, self.brightness_max)

    def __call__(self):
        return self.__brightness

    def tick(self, delta_ms):
        self.__time += delta_ms

        # Check if the interval has elapsed
        if self.__time >= (self.interval * 1000):
            self.__time -= (self.interval * 1000)

            self.__brightness = random.uniform(self.brightness_min, self.brightness_max)
