# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

class NoneFX:
    NAME = "none"
    CALLED = None
    TAKES = ()

    def __call__(self):
        return 0.0
