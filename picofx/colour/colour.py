# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import rgb_from_hsv


class RGBFX:
    def __init__(self, red=255, green=255, blue=255):
        self.red = red
        self.green = green
        self.blue = blue

    def __call__(self):
        return max(min(self.red, 255), 0), \
            max(min(self.green, 255), 0), \
            max(min(self.blue, 255), 0)


class HSVFX:
    def __init__(self, hue=0.0, sat=1.0, val=1.0):
        self.hue = hue
        self.sat = sat
        self.val = val

    def __call__(self):
        r, g, b = rgb_from_hsv(self.hue, self.sat, self.val)
        return int(r * 255), int(g * 255), int(b * 255)
