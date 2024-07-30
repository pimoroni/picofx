# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Updateable


class BinaryCounterFX(Updateable):
    def __init__(self, interval=0.1, count=0, step=1):
        self.interval = interval
        self.counter = count
        self.step = step
        self.__time = 0

    def __call__(self, bit):
        def fx():
            nonlocal bit
            return 1.0 if self.counter & 1 << bit else 0.0
        return self, fx

    def tick(self, delta_ms):
        self.__time += delta_ms

        # Check if the interval has elapsed
        if self.__time >= (self.interval * 1000):
            self.__time -= (self.interval * 1000)
            self.counter += self.step
