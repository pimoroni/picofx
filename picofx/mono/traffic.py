# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Updateable


class TrafficLightFX(Updateable):
    AMBER_FLASHING_CYCLE = 0.25

    def __init__(self, red_interval=10, red_amber_interval=5, green_interval=10, amber_interval=5, fade_rate=0.01, amber_flashing=False):
        # Have the red be on with amber if amber isn't flashing
        r = 0 if amber_flashing else 1
        self.__states = [
            ((1, 0, 0), int(red_interval * 1000)),          # Red
            ((r, 1, 0), int(red_amber_interval * 1000)),    # Red + Amber
            ((0, 0, 1), int(green_interval * 1000)),        # Green
            ((0, 1, 0), int(amber_interval * 1000))         # Amber
        ]
        self.__index = 0  # Start with Red state
        self.__time = 0  # Track time of last state change
        self.__state = list(self.__states[self.__index][0])
        self.__interval = self.__states[self.__index][1]
        self.__current = [0, 0, 0]
        self.fade_rate = fade_rate
        self.__amber_flashing = amber_flashing

    def red(self):
        def fx():
            return self.__current[0]
        return self, fx

    def amber(self):
        def fx():
            return self.__current[1]
        return self, fx

    def green(self):
        def fx():
            return self.__current[2]
        return self, fx

    def tick(self, delta_ms):
        self.__time += delta_ms

        # Check if the interval has elapsed
        if self.__time >= self.__interval:
            self.__time -= self.__interval

            self.__index = (self.__index + 1) % len(self.__states)
            self.__state = list(self.__states[self.__index][0])
            self.__interval = self.__states[self.__index][1]

        if self.__amber_flashing:
            # Handle special case for Amber state (flashing)
            if self.__index == 1 and ((self.__time / 1000) % self.AMBER_FLASHING_CYCLE) >= (self.AMBER_FLASHING_CYCLE / 2):
                self.__state[1] = 0
            else:
                self.__state[1] = self.__states[self.__index][0][1]

        # Add a fading effect to the outputs
        for i in range(len(self.__current)):
            if self.__current[i] < self.__state[i]:
                self.__current[i] = min(self.__current[i] + delta_ms * self.fade_rate, self.__state[i])
            elif self.__current[i] > self.__state[i]:
                self.__current[i] = max(self.__current[i] - delta_ms * self.fade_rate, self.__state[i])
