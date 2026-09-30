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


class FlickerEachFX(Updateable):
    """A flicker for every output, each dipping at its own moments. """

    NAME = "flicker_each"
    CALLED = "position"
    TAKES = ("brightness", "dimness", "bright_min", "bright_max", "dim_min", "dim_max")

    def __init__(self, brightness=1.0, dimness=0.5, bright_min=0.05, bright_max=0.1, dim_min=0.02, dim_max=0.04):
        self.brightness = brightness
        self.dimness = dimness
        self.bright_min = bright_min
        self.bright_max = bright_max
        self.dim_min = dim_min
        self.dim_max = dim_max

        # The state of each output, added to as each output requests its callable
        self.__is_dim = []
        self.__time = []
        self.__duration = []
        self.__dim = brightness * (1.0 - dimness)

    def __call__(self, pos):
        # Add state for every position up to this one, as positions may be requested out of order
        while len(self.__is_dim) <= pos:
            self.__is_dim.append(False)
            self.__time.append(0)
            # Start with a random bright period, so the outputs do not all flicker together
            self.__duration.append(int(random.uniform(0, self.bright_max) * 1000))

        def fx():
            nonlocal pos
            return self.__dim if self.__is_dim[pos] else self.brightness
        return self, fx

    def tick(self, delta_ms):
        # Held locally, so each list is looked up once a frame
        is_dim = self.__is_dim
        time = self.__time
        duration = self.__duration

        for pos in range(len(is_dim)):
            elapsed = time[pos] + delta_ms

            # Check if this output's current period has elapsed
            if elapsed >= duration[pos]:
                elapsed -= duration[pos]

                if is_dim[pos]:
                    # A dim period has ended, so a bright one follows
                    duration[pos] = int(random.uniform(self.bright_min, self.bright_max) * 1000)
                else:
                    # A bright period has ended, so a dim one follows
                    duration[pos] = int(random.uniform(self.dim_min, self.dim_max) * 1000)

                is_dim[pos] = not is_dim[pos]

            time[pos] = elapsed

        # Calculated once a frame, where __call__ would be once a channel
        self.__dim = self.brightness * (1.0 - self.dimness)
