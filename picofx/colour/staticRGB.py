# SPDX-FileCopyrightText: 2025 Tom Hallam for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

class StaticRGBFX:
    def __init__(self, brightness=1.0, r=255, g=0, b=0):
        self.brightness = brightness
        self.red = r
        self.green = g
        self.blue = b

    def __call__(self):
        r = self.red * self.brightness
        g = self.green * self.brightness
        b = self.blue * self.brightness

        return max(min(r, 255), 0), \
            max(min(g, 255), 0), \
            max(min(b, 255), 0)
