# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Updateable, rgb_from_hsv


class HueStepFX(Updateable):
    NAME = "hue_step"
    CALLED = None
    TAKES = ("interval", "hue", "sat", "val", "steps")

    def __init__(self, interval=1.0, hue=0.0, sat=1.0, val=1.0, steps=6):
        self.interval = interval
        self.__start_hue = hue
        self.__sat = sat
        self.__val = val
        self.__steps = steps
        self.__current_step = 0
        self.__time = 0

        self.__stale = False
        self.__mix()

    def __mix(self):
        """Mix HSV into RGB, calculated whenever the step or a setting changes."""
        hue = (self.__start_hue + (self.__current_step / self.__steps)) % 1.0
        r, g, b = rgb_from_hsv(hue, self.__sat, self.__val)
        self.__rgb = (int(r * 255), int(g * 255), int(b * 255))

    @property
    def start_hue(self):
        return self.__start_hue

    @start_hue.setter
    def start_hue(self, value):
        self.__start_hue = value
        self.__stale = True

    @property
    def sat(self):
        return self.__sat

    @sat.setter
    def sat(self, value):
        self.__sat = value
        self.__stale = True

    @property
    def val(self):
        return self.__val

    @val.setter
    def val(self, value):
        self.__val = value
        self.__stale = True

    def __call__(self):
        return self.__rgb

    def tick(self, delta_ms):
        self.__time += delta_ms

        # Check if the interval has elapsed
        if self.__time >= (self.interval * 1000):
            self.__time -= (self.interval * 1000)

            self.__current_step = (self.__current_step + 1) % self.__steps
            self.__stale = True

        # A player ticks before it shows, so one mix here covers however many
        # settings moved since the last frame
        if self.__stale:
            self.__mix()
            self.__stale = False
