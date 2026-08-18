# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Updateable


class PelicanCrossingFX(Updateable):
    """A pelican crossing: the traffic lights, and the two figures pedestrians read.

    Runs on its own clock rather than on demand, so the crossing comes round in its
    own time. The amber and the walking figure flash together, which is the phase a
    pelican has in place of red and amber.
    """

    NAME = "pelican_crossing"
    CALLED = ("red", "amber", "green", "stop", "walk")
    TAKES = ("red_interval", "flashing_interval", "green_interval", "amber_interval")

    FLASHING_CYCLE = 0.25

    def __init__(self, red_interval=8, flashing_interval=6, green_interval=20, amber_interval=3):
        # Traffic red, amber and green, then the figures: stop and walk. The figures
        # follow the traffic, so nothing sets them beyond the state they belong to
        self.__states = [
            ((1, 0, 0, 0, 1), int(red_interval * 1000)),        # Stopped, and crossing
            ((0, 1, 0, 0, 1), int(flashing_interval * 1000)),   # Both flashing, crossing ends
            ((0, 0, 1, 1, 0), int(green_interval * 1000)),      # Traffic moving
            ((0, 1, 0, 1, 0), int(amber_interval * 1000))       # Traffic clearing
        ]
        self.__flashing = 1  # The state whose amber and figure flash
        self.__index = 0
        self.__time = 0
        self.__state = list(self.__states[self.__index][0])
        self.__interval = self.__states[self.__index][1]

    def red(self):
        def fx():
            return self.__state[0]
        return self, fx

    def amber(self):
        def fx():
            return self.__state[1]
        return self, fx

    def green(self):
        def fx():
            return self.__state[2]
        return self, fx

    def stop(self):
        def fx():
            return self.__state[3]
        return self, fx

    def walk(self):
        def fx():
            return self.__state[4]
        return self, fx

    def tick(self, delta_ms):
        self.__time += delta_ms

        if self.__time >= self.__interval:
            self.__time -= self.__interval

            self.__index = (self.__index + 1) % len(self.__states)
            self.__state = list(self.__states[self.__index][0])
            self.__interval = self.__states[self.__index][1]

        if self.__index == self.__flashing:
            # One clock for both, so the amber and the figure are never out of step
            lit = self.__states[self.__index][0]
            dark = ((self.__time / 1000) % self.FLASHING_CYCLE) >= (self.FLASHING_CYCLE / 2)
            self.__state[1] = 0 if dark else lit[1]
            self.__state[4] = 0 if dark else lit[4]

    def reset(self):
        self.__index = 0
        self.__time = 0
        self.__state = list(self.__states[self.__index][0])
        self.__interval = self.__states[self.__index][1]
