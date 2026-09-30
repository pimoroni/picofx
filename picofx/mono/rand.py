# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import random

from picofx import Updateable


class RandomFX(Updateable):
    NAME = "random"
    CALLED = None
    TAKES = ("interval", "brightness_min", "brightness_max")

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


class RandomEachFX(Updateable):
    """A random brightness for every output, all changing together each interval. """

    NAME = "random_each"
    CALLED = "position"
    TAKES = ("interval", "brightness_min", "brightness_max")

    def __init__(self, interval=0.05, brightness_min=0.0, brightness_max=1.0):
        self.interval = interval
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max
        self.__time = 0
        # The brightness of each output, added to as each output requests its callable
        self.__brightness = []

    def __call__(self, pos):
        # Add a brightness for every position up to this one, as positions may be requested out of order
        while len(self.__brightness) <= pos:
            self.__brightness.append(random.uniform(self.brightness_min, self.brightness_max))

        def fx():
            nonlocal pos
            return self.__brightness[pos]
        return self, fx

    def tick(self, delta_ms):
        self.__time += delta_ms

        # Check if the interval has elapsed
        if self.__time >= (self.interval * 1000):
            self.__time -= (self.interval * 1000)

            brightness = self.__brightness
            for pos in range(len(brightness)):
                brightness[pos] = random.uniform(self.brightness_min, self.brightness_max)
