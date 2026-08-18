# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Updateable


class TrafficLightFX(Updateable):
    NAME = "traffic_light"
    CALLED = ("red", "amber", "green")
    TAKES = ("red_interval", "red_amber_interval", "green_interval", "amber_interval")

    def __init__(self, red_interval=10, red_amber_interval=5, green_interval=10, amber_interval=5):
        self.__states = [
            ((1, 0, 0), int(red_interval * 1000)),          # Red
            ((1, 1, 0), int(red_amber_interval * 1000)),    # Red + Amber
            ((0, 0, 1), int(green_interval * 1000)),        # Green
            ((0, 1, 0), int(amber_interval * 1000))         # Amber
        ]
        self.__index = 0  # Start with Red state
        self.__time = 0  # Track time of last state change
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

    def tick(self, delta_ms):
        self.__time += delta_ms

        # Check if the interval has elapsed
        if self.__time >= self.__interval:
            self.__time -= self.__interval

            self.__index = (self.__index + 1) % len(self.__states)
            self.__state = list(self.__states[self.__index][0])
            self.__interval = self.__states[self.__index][1]
