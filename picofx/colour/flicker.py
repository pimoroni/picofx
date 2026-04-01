# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import random
from picofx import Updateable


class RGBFlickerFX(Updateable):
    def __init__(self, colour=None, brightness=1.0, dimness=0.5, bright_min=0.05, bright_max=0.1, dim_min=0.02, dim_max=0.04):
        if colour is None:
            self.colour = (255, 0, 0)
        if isinstance(colour, tuple) and len(colour) == 3:
            self.colour = colour
        else:
            raise TypeError("colour is not a supported type. Expected a tuple of 3 numbers, or None.")
        
        self.brightness = brightness
        self.dimness = dimness
        self.bright_min = bright_min
        self.bright_max = bright_max
        self.dim_min = dim_min
        self.dim_max = dim_max

        self.__is_dim = False
        self.__bright_dur = 0
        self.__dim_dur = 0
        self.__time = 0

    def __call__(self):
        return int(((self.brightness * (1.0 - self.dimness)) if self.__is_dim else self.brightness) * self.colour[0]), \
               int(((self.brightness * (1.0 - self.dimness)) if self.__is_dim else self.brightness) * self.colour[1]), \
               int(((self.brightness * (1.0 - self.dimness)) if self.__is_dim else self.brightness) * self.colour[2])

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
