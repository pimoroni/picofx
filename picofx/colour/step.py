# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Updateable, rgb_from_hsv


class HueStepFX(Updateable):
    def __init__(self, interval=1.0, hue=0.0, sat=1.0, val=1.0, steps=6):
        self.interval = interval
        self.start_hue = hue
        self.sat = sat
        self.val = val
        self.__steps = steps
        self.__current_step = 0
        self.__time = 0

    def __call__(self):
        hue = (self.start_hue + (self.__current_step / self.__steps)) % 1.0
        r, g, b = rgb_from_hsv(hue, self.sat, self.val)
        return int(r * 255), int(g * 255), int(b * 255)

    def tick(self, delta_ms):
        self.__time += delta_ms

        # Check if the interval has elapsed
        if self.__time >= (self.interval * 1000):
            self.__time -= (self.interval * 1000)

            self.__current_step = (self.__current_step + 1) % self.__steps
