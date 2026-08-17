# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Updateable


class SweepFX(Updateable):
    """A light that sweeps across the outputs and bounces back at each end. """

    NAME = "sweep"
    CALLED = "position"
    TAKES = ("speed", "length", "extent")

    def __init__(self, speed=1, length=1, extent=1.0):
        self.speed = speed
        self.length = length
        self.extent = extent
        # Counts a pass out and a pass back, so a speed means the same here as it
        # does for the effects that travel one way and wrap
        self.__offset_ms = 0
        self.__head = 0.0

    def tick(self, delta_ms):
        self.__offset_ms = (self.__offset_ms + int(delta_ms * self.speed)) % 2000

        travel = self.__offset_ms
        if travel > 1000:
            travel = 2000 - travel
        self.__head = (travel * (self.length - 1)) / 1000

    def reset(self):
        self.__offset_ms = 0
        self.__head = 0.0

    def __call__(self, pos):
        def fx():
            nonlocal pos
            return max(0.0, 1.0 - abs(pos - self.__head) / self.extent)
        return self, fx
