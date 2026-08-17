# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

class StaticFX:
    NAME = "static"
    CALLED = None
    TAKES = ("brightness",)

    def __init__(self, brightness=1.0):
        self.brightness = brightness

    def __call__(self):
        return self.brightness
