# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Two screens on their own SP/CE ports, presented together as one. A pair streams
# both panels concurrently and holds their tearing-effect phases together, so one
# image does not land on one panel tens of milliseconds before the other.

import logging
import time

from machine import Pin

import picovector
import spidisplay


def update_pair(first, second, v_sync=None):
    """Stream a frame to two screens at once, each starting on its own TE edge.

    Both screens must have prepare()d a frame, sit on different SP/CE ports since
    one port is one stream, and agree on reserve. Presenting a pair this way takes
    about the time one of them alone would, instead of the two in turn, and the
    panels change together.

    v_sync=None waits on the tearing-effect signal when both screens were built
    for it.
    """
    if first is second:
        raise ValueError("update_pair needs two different screens")
    if first.port is second.port:
        raise ValueError("update_pair needs a screen on each SP/CE port, since one port is one stream; broadcast() shares a port")
    # One reservation is shared out across the pair, so it leaves both screens short
    # rather than protecting the one that made it.
    if first.reserve != second.reserve:
        raise ValueError("update_pair needs both screens built with the same reserve, since a reservation is shared out across the pair: set it on both, or on neither")

    if v_sync is None:
        v_sync = first.v_sync and second.v_sync
    elif v_sync and not (first.v_sync and second.v_sync):
        raise ValueError("v_sync needs both screens created with te, since each waits on its own panel's tearing-effect signal")

    spidisplay.update_all(first.display, second.display, v_sync=v_sync)
    first.drawn()
    second.drawn()


class ScreenPair:
    """Two screens on their own SP/CE ports, presented together as one.

    update() streams a frame to both panels at once and, with align on, holds
    their TE phases together so the two change as one: the faster panel
    follows, its edge delayed with TESCAN inside the measured tear margin and
    its rate pulled with FRCTRL2 when TESCAN cannot absorb the error, one
    correction per pair frame. After a pause long enough for the pair to drift
    apart, the next update() first spends a frame-counted rate excursion on
    both panels while the stale content hides it, so resuming costs one late
    frame instead of seconds of visible catching up.

    align defaults to aligning where the pair can, calibrating at construction:
    about four seconds of period probes which it says it is doing, from which the
    pair predicts the steady skew it can hold, align_floor_us. A pair too
    mismatched to hold any says why and runs unaligned, is_aligned() then
    reporting False. align=True refuses such a pair instead, and align=False
    leaves the panels alone; start_aligning() takes the four seconds later, and
    stop_aligning() stops.

    Alignment holds panel state on the following screen, a non-zero TESCAN and
    at times a slower rate code. Both are restored whenever that screen is
    updated outside its pair, and by stop_aligning(). update_pair() stays
    underneath as the stateless entry, which is what the diagnostics use.
    """

    # The fine loop, as tools/check_te_align.py measured it
    DEADBAND_LINES = 2
    KP = 1.0
    MAX_STEP = 8
    SLIP_FRACTION = 0.6         # of the tear margin: the walk's ceiling
    DITHER_FRACTION = 0.4       # of the margin: steady dither pulls the walk back here
    ASSIST_LINES = 4            # slower-code assist when the need exceeds the walk room

    # The resync, as tools/check_te_resync.py measured it
    DEPTHS = (1, 2)             # rate steps a plan may move a panel: deeper buys latency, costs aim
    MAX_FRAMES = 3              # frames of excursion a plan may spend on one panel
    ACCURACY_LINES = 5          # close enough to hand over, so a plan stops paying for better
    ABSORB_US = 1430            # handover error the fine loop hides without looking worse than usual
    TARGET_US = -300            # aim slightly negative, drift closing that side for free
    FLOOR_FRACTION = 0.7        # of the rate quantum: where both measured pairs settle
    PROBE_MS = 250              # settled period probe
    CAPTURE_EDGES = 2           # TE falls per panel per phase capture
    CAPTURE_TIMEOUT_MS = 500
    SCHEDULE_TIMEOUT_MS = 250   # an excursion spans at most MAX_FRAMES + 1 periods

    def __init__(self, first, second, align=None):
        if first is second:
            raise ValueError("a pair needs two different screens")
        if first.port is second.port:
            raise ValueError("a pair needs a screen on each SP/CE port, since one port is one stream; broadcast() shares a port")
        if first.reserve != second.reserve:
            raise ValueError("a pair needs both screens built with the same reserve, since a reservation is shared out across the pair: set it on both, or on neither")

        self.__screens = (first, second)
        self.__align = False
        self.__calibrated = False
        self.__last_frame_ms = None
        self.__walk = 0
        self.__walk_sent = 0
        self.__slow_on = False
        self.__timeouts_seen = 0
        self.__n_hi = None
        self.__dither_hi = 0

        if align is None:
            # A request rather than a requirement: every reason a pair cannot hold
            # alignment is a fact about the panels, so saying so and streaming
            # unaligned still leaves the caller the interleaving, which is the larger
            # part of what a pair buys. Nothing needs undoing on the way out, since
            # start_aligning() raises before it changes anything and calibration hands
            # both panels back their nominal rate whichever way it ends.
            try:
                self.start_aligning()
            except ValueError as e:
                logging.info(f"> Screen pair could not align: {e}")
        elif align:
            self.start_aligning()

    @staticmethod
    def __pair_values(value, name):
        """One value for both screens, or a 2-tuple giving one each."""
        if isinstance(value, (tuple, list)):
            if len(value) != 2:
                raise ValueError(f"a per-screen {name} is two values, one for each screen, not {len(value)}")
            return value
        return (value, value)

    @staticmethod
    def __pair_offsets(offset):
        """offset resolved to one (x, y) or None per screen.

        Shared unless either element is itself a pair, offset being an (x, y) pair
        already. Every shape that is neither form is rejected, since the two
        readings differ silently: (5, None) is the one quiet case, and only because
        both readings mean the same frame.
        """
        if offset is None:
            return (None, None)
        if not isinstance(offset, (tuple, list)) or len(offset) != 2:
            raise ValueError("offset is (x, y) for both screens, or two of them for one screen each")

        if any(isinstance(element, (tuple, list)) for element in offset):
            # Per screen: each element an (x, y) pair, or None for centred
            for element in offset:
                if element is None:
                    continue
                if not isinstance(element, (tuple, list)) or len(element) != 2:
                    raise ValueError(f"{offset} reads as a per-screen offset, so each element is an (x, y) pair or None; a shared offset is (x, y) with plain coordinates")
                for coordinate in element:
                    if coordinate is not None and not isinstance(coordinate, int):
                        raise ValueError(f"{element} is not an (x, y) pair: each coordinate is a number, or None for centred on that axis")
            return offset

        # Shared: one (x, y) applied to both screens
        for coordinate in offset:
            if coordinate is not None and not isinstance(coordinate, int):
                raise ValueError(f"{offset} is not an (x, y) pair: each coordinate is a number, or None for centred on that axis. A per-screen offset is two such pairs.")
        return (offset, offset)

    @staticmethod
    def __fold(delta, period):
        """Signed fold of a difference into half a period."""
        d = delta % period
        if d > period // 2:
            d -= period
        return d

    @staticmethod
    def __signed_mod(delta, period):
        """Signed difference between two of the C module's 32-bit microsecond stamps.

        The difference folds to signed 32 bits before the period reduction: 2**32 is
        not a multiple of a TE period, so reducing an unsigned wrap biases every
        negative skew by (2**32 % period), 130-odd lines at these rates.
        """
        return ScreenPair.__fold(((delta + 0x80000000) & 0xFFFFFFFF) - 0x80000000, period)

    @property
    def screens(self):
        return self.__screens

    def is_aligned(self):
        """Whether the pair is holding its panels' TE phases together.

        The state alignment reached rather than what was asked of it, so False
        where a request went unmet and False again after stop_aligning().
        """
        return self.__align

    def start_aligning(self):
        """Start holding the panels' TE phases together, measuring them first.

        The first call spends about four seconds probing both panels' periods,
        which it says it is doing; later calls resume from those measurements.
        Raises where this pair cannot hold alignment, saying which reason.
        """
        if self.__align:
            return

        first, second = self.__screens
        if not (first.v_sync and second.v_sync):
            raise ValueError("alignment waits on both panels' tearing-effect signals, so it needs both screens created with te and v_sync")
        if not self.__calibrated:
            self.__calibrate()
        self.__walk = 0
        self.__slow_on = False
        self.__timeouts_seen = self.__f_disp.te_timeouts() + self.__l_disp.te_timeouts()
        self.__last_frame_ms = None
        self.__f_screen.__pair = self
        self.__align = True

    def stop_aligning(self):
        """Stop correcting, handing the following panel its TESCAN and rate back."""
        if not self.__align:
            return

        self.__align = False
        if self.__calibrated:
            self.__restore_panel()
            self.__f_screen.__pair = None

    @property
    def align_floor_us(self):
        """The steady skew alignment is predicted to settle at, in microseconds.

        About 0.7 of the follower's one-step rate quantum, which is where both
        measured pair types land. Construction already refused a pair whose
        drift exceeds the quantum outright.
        """
        if not self.__calibrated:
            raise ValueError("align has never been on, so the pair is uncalibrated")

        return self.__floor_us

    def update(self, image, second=None, *, rotation=0, mirror=False, v_sync=None,
               bg_color=picovector.color.black, pixel_double=False, offset=None):
        """Stream a frame to both screens, aligned when align is on.

        One image reaches both panels, or a second positional image gives each
        its own. Every placement keyword takes one value for both screens, or a
        2-tuple for one each, so a pair mounted opposite ways is
        rotation=(90, 270). offset is the exception, being an (x, y) pair
        itself: it is shared unless an element is itself a pair.

            offset=(5, 10)              both screens at (5, 10)
            offset=(5, None)            both screens: x=5, y centred
            offset=(None, (5, 10))      first centred, second at (5, 10)
            offset=((0, 0), (5, 10))    one each

        v_sync=None waits on the tearing-effect signal when both screens were
        built for it. An aligned pair refuses v_sync=False, the signal being
        what alignment measures by.
        """
        first_screen, second_screen = self.__screens
        if second is None:
            second = image
        rotations = self.__pair_values(rotation, "rotation")
        mirrors = self.__pair_values(mirror, "mirror")
        doubles = self.__pair_values(pixel_double, "pixel_double")
        backgrounds = self.__pair_values(bg_color, "bg_color")
        offsets = self.__pair_offsets(offset)

        if self.__align:
            if v_sync is False:
                raise ValueError("an aligned pair waits on the tearing-effect signal every frame, since that is what alignment measures by. Call stop_aligning() for free-running frames.")

            # A pause leaves the pair drifted apart. Once the expected error
            # passes what the fine loop can hide, spend a resync on it while
            # the content is still stale; below that the loop absorbs it.
            last = self.__last_frame_ms
            if last is not None and \
                    time.ticks_diff(time.ticks_ms(), last) * self.__drift_us_per_ms > self.ABSORB_US:
                self.__resync()

        first_screen.prepare(image, rotation=rotations[0], mirror=mirrors[0],
                             bg_color=backgrounds[0], pixel_double=doubles[0],
                             offset=offsets[0])
        second_screen.prepare(second, rotation=rotations[1], mirror=mirrors[1],
                              bg_color=backgrounds[1], pixel_double=doubles[1],
                              offset=offsets[1])
        update_pair(first_screen, second_screen, v_sync=v_sync)

        if self.__align:
            self.__correct()
            self.__last_frame_ms = time.ticks_ms()

    def __calibrate(self):
        """Probe both panels' periods, nominal and four codes each, and derive the rest.

        The excursion shifts are derived from the probed periods,
        LINE_SLOTS * (P_code / P_nominal - 1) signed by which panel it is, which
        tracks a frame-counted measurement to a few lines and is the stabler
        number. The nominal rate labels are not derivable from: they are not
        linear in the divider, so every code is probed.
        """
        # Said at the default level: four seconds of a mute constructor reads as a hung
        # board. The figure is fixed work, so unlike a folder of images it can be quoted.
        logging.info("> Calibrating the screen pair, about four seconds ...")
        started = time.ticks_ms()

        screens = self.__screens
        displays = tuple(screen.display for screen in screens)

        # The first probe after a panel's bringup reads about 3.4% long and
        # settles within a second, so each panel's first reading is discarded.
        periods = []
        for display in displays:
            display.te_probe(self.PROBE_MS)
            periods.append(display.te_probe(self.PROBE_MS)[0])
        if not (periods[0] and periods[1]):
            raise ValueError("no tearing-effect signal from one of the panels, which alignment measures by")

        fi = 0 if periods[0] <= periods[1] else 1      # the faster panel follows
        li = 1 - fi
        f_screen = screens[fi]
        controller = f_screen.CONTROLLER
        # The faster panel's own slot count, not the controller's default: a screen
        # whose porch has been moved spends a different number of them.
        line_slots = f_screen.line_slots
        s_line = periods[fi] / line_slots

        # Per panel: the sorted rate table, the built rate's index, and a probed
        # settled period at one and two steps each way where the table has them.
        tables = []
        rates = []
        nominals = []
        sweep = [{}, {}]
        for i, screen in enumerate(screens):
            table = screen.CONTROLLER.FRAME_RATE_CONTROL
            ordered = sorted(table)
            nominal = ordered.index(screen.framerate)
            tables.append(table)
            rates.append(ordered)
            nominals.append(nominal)
            for depth in self.DEPTHS:
                for rate_index in (nominal - depth, nominal + depth):
                    if not 0 <= rate_index < len(ordered):
                        continue
                    screen.command(screen.CONTROLLER.REG_FRCTRL2, table[ordered[rate_index]])
                    time.sleep_ms(100)
                    period = screen.display.te_probe(self.PROBE_MS)[0]
                    if period:
                        sweep[i][rate_index] = period
            screen.command(screen.CONTROLLER.REG_FRCTRL2, table[ordered[nominal]])
            time.sleep_ms(100)

        if nominals[fi] - 1 not in sweep[fi]:
            raise ValueError(f"the faster panel is already at {f_screen.framerate}fps, the slowest rate it has, so alignment has no slower one to pull it with")

        # The rate quantum bounds what the loop can hold: one slow-code frame
        # removes quantum lines while every frame adds the drift, so a pair
        # drifting faster than its quantum has no duty that holds it.
        natural = line_slots * (1.0 / periods[fi] - 1.0 / periods[li])  # lines per us
        drift = natural * periods[fi]                                   # lines per period
        quantum = line_slots * (sweep[fi][nominals[fi] - 1] / periods[fi] - 1.0)
        logging.debug(f"> Pair drift {drift:.1f} lines a period, against {quantum:.1f} lines a one-step rate change buys back")
        if drift >= quantum:
            # Panels of different types take their rate from their own PROFILES and
            # so can disagree on a wire where both are tuned well. That has a fix
            # from here, unlike two panels already on one rate.
            if screens[0].framerate != screens[1].framerate:
                remedy = f"Set both screens to the same framerate, {screens[0].framerate}fps and {screens[1].framerate}fps being too far apart"
            else:
                remedy = "Pair better-matched panels"
            raise ValueError(f"these panels' refreshes drift apart faster than alignment can pull them back. {remedy}, or create the pair with align=False.")

        # Excursion options per panel: the no-op, then each probed code held for
        # one to MAX_FRAMES of that panel's own frames. A slower follower or a
        # faster leader closes a positive error, so the shift carries the sign
        # of the panel.
        options = ([(None, 0, 0.0)], [(None, 0, 0.0)])
        for i in (0, 1):
            for rate_index, period in sweep[i].items():
                stretch = line_slots * (period / periods[i] - 1.0)
                per_frame = -stretch if i == fi else stretch
                code = tables[i][rates[i][rate_index]]
                for frames in range(1, self.MAX_FRAMES + 1):
                    options[i].append((code, frames, per_frame * frames))

        # Every plan a resync could want, priced once. A plan pays the drift
        # over its own execution, half a period of average wait for the first
        # fall plus one per counted frame, and only codes pushing the way the
        # error needs are worth pairing.
        settling = natural * periods[fi]
        plans = {}
        for want_negative in (False, True):
            entries = []
            for f_code, f_frames, f_lines in options[fi]:
                if f_frames and (f_lines < 0) != want_negative:
                    continue
                for l_code, l_frames, l_lines in options[li]:
                    if l_frames and (l_lines < 0) != want_negative:
                        continue
                    cost = max(f_frames, l_frames)
                    shift = f_lines + l_lines + settling * (cost + 0.5)
                    schedule = [None, None]
                    schedule[fi] = (f_code, f_frames)
                    schedule[li] = (l_code, l_frames)
                    entries.append((shift, cost, tuple(schedule)))
            plans[want_negative] = entries

        self.__f_screen = f_screen
        self.__f_disp = displays[fi]
        self.__l_disp = displays[li]
        self.__period_f = periods[fi]
        self.__line_slots = line_slots
        self.__s_line = s_line
        self.__natural = natural
        self.__drift_us_per_ms = abs(natural) * s_line * 1000.0
        self.__target_lines = self.TARGET_US / s_line
        self.__floor_us = self.FLOOR_FRACTION * quantum * s_line
        self.__reg_tescan = controller.REG_TESCAN
        self.__reg_frctrl2 = controller.REG_FRCTRL2
        self.__code_norm = tables[fi][rates[fi][nominals[fi]]]
        self.__code_slow = tables[fi][rates[fi][nominals[fi] - 1]]
        self.__nominal_codes = tuple(tables[i][rates[i][nominals[i]]] for i in (0, 1))
        self.__te_lines = tuple(screen.__te_line for screen in screens)
        self.__plans = plans
        self.__calibrated = True

        # The opener promised four seconds, so say when they are up. The figures
        # only reach a caller who asked for them.
        if logging.level < logging.LOG_DEBUG:
            logging.info("> Screen pair calibrated")
        else:
            logging.debug(f"> Calibrated in {time.ticks_diff(time.ticks_ms(), started)}ms, predicted skew floor {self.__floor_us:.0f}us")

    def __send_walk(self, walk):
        if walk != self.__walk_sent:
            self.__f_screen.command(self.__reg_tescan, bytes((walk >> 8, walk & 0xFF)))
            self.__walk_sent = walk

    def __send_slow(self, want_slow):
        if want_slow != self.__slow_on:
            self.__f_screen.command(self.__reg_frctrl2,
                                    self.__code_slow if want_slow else self.__code_norm)
            self.__slow_on = want_slow

    def __restore_panel(self):
        """Hand the follower's panel back: TESCAN wide, nominal rate.

        A non-zero TESCAN narrows the TE pulse to about one line time, which a
        pair frame's tight poll absorbs but a screen updated on its own is not
        promised to, so this runs before any frame outside the pair.
        """
        self.__send_walk(0)
        self.__send_slow(False)
        self.__walk = 0

    def __correct(self):
        """One proportional correction from the last pair frame's write starts."""
        stats_f = self.__f_disp.stats()
        stats_l = self.__l_disp.stats()
        if self.__n_hi is None:
            # The tear margin needs a streamed frame's length, so the walk's
            # bounds wait for the first one
            margin = self.__line_slots + self.__f_screen.height - stats_f.frame_us / self.__s_line
            self.__n_hi = max(4, int(margin * self.SLIP_FRACTION))
            self.__dither_hi = max(2, int(margin * self.DITHER_FRACTION))

        timeouts = self.__f_disp.te_timeouts() + self.__l_disp.te_timeouts()
        if timeouts != self.__timeouts_seen:
            self.__timeouts_seen = timeouts     # a timeout fired, so the skew is not a phase
            return

        err_us = self.__signed_mod(stats_f.write_start_us - stats_l.write_start_us,
                                   self.__period_f)
        need = -err_us / self.__s_line          # positive: the follower must be delayed
        walk = self.__walk
        if abs(need) >= self.DEADBAND_LINES:
            step = round(self.KP * need)
            step = max(-self.MAX_STEP, min(self.MAX_STEP, step))
            walk = max(0, min(self.__n_hi, walk + step))
        self.__walk = walk
        self.__send_walk(walk)
        self.__send_slow(need > (self.__n_hi - walk) + self.ASSIST_LINES
                         or walk > self.__dither_hi)

    def __resync(self):
        """Measure the drift a pause left, and spend an excursion cancelling it.

        The walk holds TESCAN non-zero and a capture wants the wide V-porch
        pulse, so the two never run concurrently: zero the walk, measure,
        correct, and let the loop rebuild it. Runs between frames, while the
        panels still show stale content, so it costs one late frame.
        """
        self.__restore_panel()
        captured = spidisplay.te_phase(self.__f_disp, self.__l_disp, self.__period_f,
                                       self.CAPTURE_EDGES, self.CAPTURE_TIMEOUT_MS)
        if captured is None:
            return          # too few edges, so let the fine loop walk it out
        skew_us, age_us = captured
        if abs(skew_us) <= self.ABSORB_US:
            return
        aged = -skew_us / self.__s_line + self.__natural * age_us
        self.__run_schedule(self.__plan_for(aged - self.__target_lines))

    def __plan_for(self, error):
        """The cheapest plan landing within ACCURACY_LINES, else the closest at any cost."""
        cheapest = None
        closest = None
        for shift, cost, schedule in self.__plans[error > 0]:
            left = abs(error + shift)
            if closest is None or left < closest[0]:
                closest = (left, cost, schedule)
            if left > self.ACCURACY_LINES:
                continue
            if cheapest is None or (cost, left) < (cheapest[1], cheapest[0]):
                cheapest = (left, cost, schedule)
        best = cheapest if cheapest is not None else closest
        return best[2]

    def __set_rate(self, index, code):
        """Set one panel's rate, and hand its TE line back to the schedule's watch."""
        screen = self.__screens[index]
        screen.command(screen.CONTROLLER.REG_FRCTRL2,
                       self.__nominal_codes[index] if code is None else code)
        self.__te_lines[index].init(Pin.IN, pull=Pin.PULL_DOWN)

    def __run_schedule(self, schedule):
        """Hold each panel's code across a counted number of that panel's own frames.

        schedule[i] is (code, frames), frames of 0 leaving that panel alone. A
        panel latches its frame length at a frame boundary, so each code goes on
        just after one of that panel's TE falls and comes off after a counted
        number of later ones, making the frames it spans whole ones. Both panels
        count at once, so a correction costs the longer of the two.
        """
        pins = self.__te_lines
        for pin in pins:
            pin.init(Pin.IN, pull=Pin.PULL_DOWN)
        waiting, counting, done = 0, 1, 2
        state = [done if schedule[i][1] <= 0 else waiting for i in range(2)]
        counts = [0, 0]
        levels = [pin.value() for pin in pins]
        start = time.ticks_ms()
        while state[0] != done or state[1] != done:
            if time.ticks_diff(time.ticks_ms(), start) >= self.SCHEDULE_TIMEOUT_MS:
                break
            for i in range(2):
                if state[i] == done:
                    continue
                value = pins[i].value()
                if value == levels[i]:
                    continue
                levels[i] = value
                if value:
                    continue                # only the falls bound a frame
                if state[i] == waiting:
                    self.__set_rate(i, schedule[i][0])
                    state[i] = counting
                else:
                    counts[i] += 1
                    if counts[i] >= schedule[i][1]:
                        self.__set_rate(i, None)
                        state[i] = done
                levels[i] = pins[i].value()     # the command drove DC, so resync
        for i in range(2):
            if state[i] != done:
                self.__set_rate(i, None)
