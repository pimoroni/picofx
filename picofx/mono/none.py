# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

class NoneFX:
    """An effect that keeps its outputs dark."""

    NAME = "none"
    CALLED = None
    TAKES = ()

    def __call__(self):
        return 0.0
