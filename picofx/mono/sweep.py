# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

from picofx import Updateable


class SweepFX(Updateable):
    """A light that sweeps across the outputs and bounces back at each end."""

    NAME = "sweep"
    CALLED = "position"
    TAKES = ("speed", "length", "extent", "hold")

    def __init__(self, speed=1, length=1, extent=1.0, hold=0):
        # Does the light have a width? Each frame divides by it
        if extent <= 0:
            raise ValueError(f"extent is {extent}. Give the light's width in outputs as a number above 0, such as 1")

        self.speed = speed
        self.length = length
        self.extent = extent
        # Seconds to wait at each end, one value for both or a (far, near) pair. Counted in
        # real time, so a faster sweep waits as long and the wait can be set to outlast a trail
        self.hold = hold

        # A crossing out and a crossing back, a million each, so a speed of 1 crosses once a second
        # as a wrapping effect cycles once. Microseconds, since a slow speed moves under 1ms a tick
        self.__offset_us = 0

        # The wait still owed at the end the sweep is resting on
        self.__held_us = 0

        # Where the centre of the light is, in outputs
        self.__head = 0.0

    # The wait owed at an end, each end falling on a whole million of the offset
    def __hold_us(self, end):
        hold = self.hold
        if isinstance(hold, (tuple, list)):
            # The far end is the odd million, the near end the even one
            hold = hold[0] if (end // 1_000_000) % 2 else hold[1]
        return int(hold * 1_000_000)

    def tick(self, delta_ms):
        elapsed_us = delta_ms * 1000
        if self.__held_us > 0:
            self.__held_us -= elapsed_us
            if self.__held_us > 0:
                return
            # What is left of this tick after the hold ended partway through it
            elapsed_us = -self.__held_us
            self.__held_us = 0

        step = int(elapsed_us * self.speed)
        offset = self.__offset_us + step

        # The end this step is heading for, and whether it gets there
        reached = False
        if step > 0:
            end = (self.__offset_us // 1_000_000 + 1) * 1_000_000
            reached = offset >= end
        elif step < 0:
            end = ((self.__offset_us + 999_999) // 1_000_000 - 1) * 1_000_000
            reached = offset <= end

        if reached:
            # Time spent past the end counts towards the hold, which starts as the end is
            # reached partway through this tick
            held = self.__hold_us(end) - elapsed_us * abs(offset - end) // abs(step)

            # Is a wait owed? Without one the sweep passes the end untouched
            if held > 0:
                offset = end
                self.__held_us = held

        self.__offset_us = offset % 2_000_000
        # Whole milliseconds, so the product below stays a small int on a long strip
        travel = self.__offset_us // 1000
        if travel > 1000:
            travel = 2000 - travel
        self.__head = (travel * (self.length - 1)) / 1000

    def reset(self):
        self.__offset_us = 0
        self.__held_us = 0
        self.__head = 0.0

    def __call__(self, pos):
        def fx():
            nonlocal pos
            return max(0.0, 1.0 - abs(pos - self.__head) / self.extent)
        return self, fx
