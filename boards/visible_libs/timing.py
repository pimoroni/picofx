# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Two clock timing classes, a Pacer holding a loop to a rate and a Roller saying when a thing is next due.
# Both carry a deadline forward with ticks_add, so one pass's cost is not paid again on the next.

import time


def rate_ms(interval, fps):
    """Convert a rate, given as an interval in seconds or as an fps, to milliseconds.

    Floored at a millisecond, so a rate too fast to hold becomes the fastest that can be
    held. None for both is no rate.
    """
    if interval is not None and fps is not None:
        raise ValueError("an interval and an fps are two ways to say one rate: name one of them")

    if fps is not None:
        if fps <= 0:
            raise ValueError(f"fps is {fps}. Give a rate above 0")
        interval = 1.0 / fps
    elif interval is None:
        return None

    if interval <= 0:
        raise ValueError(f"interval is {interval}. Give a number of seconds above 0")

    return max(1, int(1000.0 * interval + 0.5))


class Pacer:
    """A loop's clock, saying how long it has been running and holding how fast it goes round.

    An interval in seconds or an fps holds the loop to that rate, hold() waiting out what is
    left of each pass. A pass that overruns drops whole intervals, so the rate is never
    exceeded to catch up, and a delta above the interval means the loop cannot hold its rate.

    It waits with sleep_ms, which wanders under load, so a fast rate holds more evenly on a
    hardware Timer, as EffectPlayer uses.
    """

    def __init__(self, interval=None, fps=None):
        self.__interval_ms = None
        self.restart(interval, fps)

    def restart(self, interval=None, fps=None):
        """Begin again, as if the loop had just been entered, on a new rate if given."""
        if interval is not None or fps is not None:
            self.__interval_ms = rate_ms(interval, fps)

        now = time.ticks_ms()
        self.__started = now
        self.__last = now
        self.__delta_ms = 0
        self.__measured_ms = 0
        if self.__interval_ms is not None:
            self.__due = time.ticks_add(now, self.__interval_ms)

    @property
    def elapsed(self):
        """Milliseconds since the loop began, or since the last restart()."""
        return time.ticks_diff(time.ticks_ms(), self.__started)

    @property
    def delta(self):
        """Milliseconds the pass is counted as having taken, for scaling movement by.

        Whole intervals where a rate was named, so movement driven by it steps evenly and
        jumps only where a pass overran. With no rate named it is the measured time.
        """
        return self.__delta_ms

    @property
    def target_ms(self):
        """Milliseconds the loop is held to, or None where no rate was named."""
        return self.__interval_ms

    @property
    def target_fps(self):
        """The rate that interval amounts to, or None where no rate was named."""
        return None if self.__interval_ms is None else 1000 / self.__interval_ms

    @property
    def measured_ms(self):
        """Milliseconds the pass that just ended really took, its wait included."""
        return self.__measured_ms

    @property
    def measured_fps(self):
        """The rate the loop is holding, from the last pass."""
        return 1000 / self.__measured_ms if self.__measured_ms > 0 else float("inf")

    def hold(self):
        """Close the pass, waiting out the rest of the interval if there is one."""
        consumed = 1
        if self.__interval_ms is not None:
            behind = time.ticks_diff(time.ticks_ms(), self.__due)
            if behind < 0:
                time.sleep_ms(-behind)
                self.__due = time.ticks_add(self.__due, self.__interval_ms)
            else:
                # Counted, not stepped through, as a pass that stalled for seconds against a
                # millisecond interval would otherwise advance thousands of times
                consumed = behind // self.__interval_ms + 1
                self.__due = time.ticks_add(self.__due, consumed * self.__interval_ms)

        now = time.ticks_ms()
        self.__measured_ms = time.ticks_diff(now, self.__last)
        self.__last = now

        if self.__interval_ms is None:
            self.__delta_ms = self.__measured_ms
        else:
            self.__delta_ms = consumed * self.__interval_ms


class Roller:
    """When one thing is next due. A loop holds a Pacer, and one of these per thing.

    An interval in seconds or an fps is the length it works in. Each advance() carries the
    deadline on from itself, so a beat stays evenly spaced however late it is read. A restart()
    starts the length again from now, and is_due() asks and changes nothing.
    """

    def __init__(self, interval=None, fps=None):
        self.__interval_ms = None
        self.restart(interval, fps)

    def restart(self, interval=None, fps=None):
        """Start the length again from now, on a new one if given.

        With no length to work in the deadline goes to now, so it is due at once.
        """
        if interval is not None or fps is not None:
            self.__interval_ms = rate_ms(interval, fps)

        self.__ticks = time.ticks_ms()
        if self.__interval_ms is not None:
            self.advance_ms(self.__interval_ms)

    def advance(self, seconds=None):
        """Move the deadline on, by a length in seconds or by the one it works in.

        Its own length carries it to the next beat still ahead, dropping any a stall went past,
        as a Pacer does. A length given is added as it is.
        """
        if seconds is not None:
            # Checked here, so the message names the seconds given and not the milliseconds
            if seconds < 0:
                raise ValueError(f"the length to advance by is {seconds}s. Give a length of 0 or more")
            self.advance_ms(1000.0 * seconds + 0.5)
            return

        if self.__interval_ms is None:
            raise ValueError("this roller works in no length, so advance() needs one: advance(seconds), or restart(seconds) to set it")

        behind = time.ticks_diff(time.ticks_ms(), self.__ticks)
        beats = behind // self.__interval_ms + 1 if behind >= 0 else 1
        self.advance_ms(beats * self.__interval_ms)

    def advance_ms(self, ms):
        """Move the deadline on by a length in milliseconds."""
        if ms < 0:
            raise ValueError(f"the length to advance by is {ms}ms. Give a length of 0 or more")

        self.__ticks = time.ticks_add(self.__ticks, int(ms))

    def is_due(self):
        """Whether the deadline has arrived, leaving it where it is."""
        return time.ticks_diff(time.ticks_ms(), self.__ticks) >= 0
