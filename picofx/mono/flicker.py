# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import random

from picofx import Updateable


class FlickerFX(Updateable):
    NAME = "flicker"
    CALLED = None
    TAKES = ("brightness", "dimness", "bright_min", "bright_max", "dim_min", "dim_max")

    def __init__(self, brightness=1.0, dimness=0.5, bright_min=0.05, bright_max=0.1, dim_min=0.02, dim_max=0.04):
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
        self.__dim = brightness * (1.0 - dimness)

    def __call__(self):
        return self.__dim if self.__is_dim else self.brightness

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

        # Calculated once a frame, where __call__ would be once a channel
        self.__dim = self.brightness * (1.0 - self.dimness)
