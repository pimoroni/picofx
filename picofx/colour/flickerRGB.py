# SPDX-FileCopyrightText: 2025 Tom Hallam for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import random
from picofx import Updateable


class FlickerRGBFX(Updateable):
    def __init__(self, brightness=1.0, dimness=0.5, bright_min=0.05, bright_max=0.1, dim_min=0.02, dim_max=0.04, r1=255, g1=0, b1=0, r2=None, g2=None, b2=None):
        self.brightness = brightness
        self.dimness = dimness
        self.bright_min = bright_min
        self.bright_max = bright_max
        self.dim_min = dim_min
        self.dim_max = dim_max

        self.red1 = r1
        self.green1 = g1
        self.blue1 = b1

        if None in (r2, g2, b2):
            self.red2 = r1
            self.green2 = g1
            self.blue2 = b1
        else:
            self.red2 = r2
            self.green2 = g2
            self.blue2 = b2

        self.__is_dim = False
        self.__bright_dur = 0
        self.__dim_dur = 0
        self.__time = 0

    def __call__(self):
        if self.__is_dim:
            r = self.red2 * (self.brightness * (1.0 - self.dimness))
            g = self.green2 * (self.brightness * (1.0 - self.dimness))
            b = self.blue2 * (self.brightness * (1.0 - self.dimness))
        else:
            r = self.red1 * self.brightness
            g = self.green1 * self.brightness
            b = self.blue1 * self.brightness

        return max(min(r, 255), 0), \
            max(min(g, 255), 0), \
            max(min(b, 255), 0)

    def tick(self, delta_ms):
        self.__time += delta_ms

        if self.__is_dim:
            # Check if the dim duration has elapsed
            if self.__time >= self.__dim_dur:
                self.__time -= self.__dim_dur

                self.__bright_dur = int(random.uniform(self.bright_min, self.bright_max) * 1000)
                self.__is_dim = False

        else:
            # Only attempt to flicker if not in bright period
            if self.__time >= self.__bright_dur:
                self.__time -= self.__bright_dur

                self.__dim_dur = int(random.uniform(self.dim_min, self.dim_max) * 1000)
                self.__is_dim = True
