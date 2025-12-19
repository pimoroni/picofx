# SPDX-FileCopyrightText: 2025 Tom Hallam for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Cycling


class FlashRGBFX(Cycling):
    def __init__(self, speed=1, flashes=2, window=0.5, phase=0.0, duty=0.5, brightness=1.0, r=255, g=0, b=0):
        super().__init__(speed)
        self.flashes = flashes
        self.window = window
        self.phase = phase
        self.duty = duty
        self.brightness = brightness
        self.red = r
        self.green = g
        self.blue = b

    @property
    def flashes(self):
        return self.__flashes

    @flashes.setter
    def flashes(self, flashes):
        if not isinstance(flashes, int) or flashes <= 0:
            raise ValueError("flashes must be an integer greater than zero")

        self.__flashes = int(flashes)

    def __call__(self):
        offset = (self.__offset + self.phase) % 1.0
        if offset < self.window:
            percent = ((offset * self.__flashes) / self.window) % 1.0
            if percent < self.duty:
                r = self.red * self.brightness
                g = self.green * self.brightness
                b = self.blue * self.brightness
        
                return max(min(r, 255), 0), \
                    max(min(g, 255), 0), \
                    max(min(b, 255), 0)
            else:
                return 0, 0, 0
        return 0, 0, 0