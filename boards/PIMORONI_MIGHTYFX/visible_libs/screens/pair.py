# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Two screens on their own SP/CE ports, presented together as one: both panels
# streamed at once, and their refreshes held together so a frame lands on both.

import logging
import time

from machine import Pin

import spidisplay

from .base import __tightest_margin

# The placement defaults resolved, so a steady loop's update() allocates nothing
__BOTH_NONE = (None, None)
__BOTH_FALSE = (False, False)


def update_pair(first, second, v_sync=None):
    """Stream the frames two screens have prepare()d, at once and each on its own TE edge."""
    if first is second:
        raise ValueError("update_pair needs two different screens")
    if first.port is second.port:
        raise ValueError("update_pair needs a screen on each SP/CE port, since one port is one "
                         "stream; broadcast() shares a port")
    # A reservation is shared out across the pair, so one alone leaves both short
    if first.__reserve != second.__reserve:
        raise ValueError("update_pair needs both screens built with the same reserve, since a "
                         "reservation is shared out across the pair: set it on both, or on neither")

    if v_sync is None:
        v_sync = first.__v_sync and second.__v_sync
    elif v_sync and not (first.__v_sync and second.__v_sync):
        raise ValueError("v_sync needs both screens created with te, since each waits on its own "
                         "panel's tearing-effect signal")

    spidisplay.update_all(first.__display, second.__display, v_sync=v_sync)

    # Each port's backlight spends a scan before it lights; revealed together they share one
    together = first.reveal_together and second.reveal_together
    owed_first = first.__drawn(keep_dark=together)
    owed_second = second.__drawn(keep_dark=together)
    if together and owed_first is not None and owed_second is not None:
        time.sleep_ms(owed_first if owed_first > owed_second else owed_second)
        first.backlight.__reveal_now()
        second.backlight.__reveal_now()


class ScreenPair:
    """Two screens on their own SP/CE ports, presented together as one."""

    # The per-frame correction
    DEADBAND_LINES = 2
    KP = 1.0
    MAX_STEP = 8
    SLIP_FRACTION = 0.6         # of the tear margin: the walk's ceiling
    DITHER_FRACTION = 0.4       # of the margin: steady dither pulls the walk back here
    ASSIST_LINES = 4            # lines of unmet need before the dither assists the walk

    # The static trim lengthens the follower's blanking, measured usable to this many lines
    BLANKING_CEILING_LINES = 56

    # The resync after a pause
    DEPTHS = (1, 2)             # rate steps a plan may move a panel: deeper buys latency, costs aim
    MAX_FRAMES = 3              # frames of excursion a plan may spend on one panel
    ACCURACY_LINES = 5          # close enough to hand over, so a plan stops paying for better
    ABSORB_US = 1430            # handover error the fine loop hides without looking worse than usual
    WANDER_US_PER_PERIOD = 20   # two free-running oscillators wander about 10us a period each
    TARGET_US = -300            # aim slightly negative, the side the walk corrects
    PROBE_MS = 250              # settled period probe
    CAPTURE_EDGES = 2           # TE falls per panel per phase capture
    CAPTURE_TIMEOUT_MS = 500
    SCHEDULE_TIMEOUT_MS = 250   # an excursion spans at most MAX_FRAMES + 1 periods

    def __init__(self, first, second, align=None, reveal_together=False):
        if first is second:
            raise ValueError("a pair needs two different screens")
        if first.port is second.port:
            raise ValueError("a pair needs a screen on each SP/CE port, since one port is one "
                             "stream; broadcast() shares a port")
        if first.__reserve != second.__reserve:
            raise ValueError("a pair needs both screens built with the same reserve, since a "
                             "reservation is shared out across the pair: set it "
                             "on both, or on neither")

        # The screens carry it, each port's backlight being what holds
        if reveal_together:
            first.__reveal_together = True
            second.__reveal_together = True

        self.__screens = (first, second)
        self.__align = False
        self.__calibrated = False
        self.__last_frame_ms = None
        self.__walk = 0
        self.__walk_sent = 0
        self.__dither = 0
        self.__trim_lines = 0
        self.__trim_on = False
        self.__resync_due = False
        self.__timeouts_seen = 0
        self.__n_hi = None
        self.__dither_hi = 0

        if align is None:
            # A request, not a requirement: every reason a pair cannot hold alignment is
            # a fact about the panels, and streaming unaligned still buys the interleaving
            try:
                self.start_aligning()
            except ValueError as e:
                logging.info(f"> Screen pair could not align: {e}")
        elif align:
            self.start_aligning()

    @staticmethod
    def __pair_values(value, name):
        if isinstance(value, (tuple, list)):
            if len(value) != 2:
                raise ValueError(f"a per-screen {name} is two values, one for each "
                                 f"screen, not {len(value)}")
            return value
        return (value, value)

    @staticmethod
    def __pair_offsets(offset):
        # Shared unless either element is itself a pair. Any other shape is rejected, the
        # two readings differing silently; (5, None) is the one case where both mean the same
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
                    raise ValueError(f"{offset} reads as a per-screen offset, so each element is an "
                                     "(x, y) pair or None; a shared offset is (x, y) "
                                     "with plain coordinates")
                for coordinate in element:
                    if coordinate is not None and not isinstance(coordinate, int):
                        raise ValueError(f"{element} is not an (x, y) pair: each coordinate is a "
                                         "number, or None for centred on that axis")
            return offset

        # Shared: one (x, y) applied to both screens
        for coordinate in offset:
            if coordinate is not None and not isinstance(coordinate, int):
                raise ValueError(f"{offset} is not an (x, y) pair: each coordinate is a number, or None "
                                 "for centred on that axis. A per-screen offset is two such pairs.")
        return (offset, offset)

    @staticmethod
    def __pair_tiles(tile):
        # Shared unless either element is itself a pair, the rule offset follows
        if not isinstance(tile, (tuple, list)):
            return (tile, tile)
        if len(tile) != 2:
            raise ValueError("tile is one value for both axes, or an (x, y) pair; a "
                             "per-screen tile is two of either")

        if any(isinstance(element, (tuple, list)) for element in tile):
            for element in tile:
                if isinstance(element, (tuple, list)) and len(element) != 2:
                    raise ValueError(f"{element} is not an (x, y) pair of tile settings")
            return tile

        return (tile, tile)

    @staticmethod
    def __fold(delta, period):
        # Signed, into half a period either way
        d = delta % period
        if d > period // 2:
            d -= period
        return d

    @staticmethod
    def __signed_mod(delta, period):
        # Two 32-bit microsecond stamps, folded to signed 32 bits before the period
        # reduction: 2**32 is not a multiple of a period, so an unsigned wrap would bias
        # every negative skew by 2**32 % period
        return ScreenPair.__fold(((delta + 0x80000000) & 0xFFFFFFFF) - 0x80000000, period)

    @property
    def screens(self):
        return self.__screens

    def is_aligned(self):
        """Whether the pair is holding its panels' refreshes together, not whether it was asked to."""
        return self.__align

    def start_aligning(self):
        """Start holding the panels' refreshes together, calibrating for about four seconds the first time."""
        if self.__align:
            return

        first, second = self.__screens
        if not (first.__v_sync and second.__v_sync):
            raise ValueError("alignment waits on both panels' tearing-effect signals, so it needs "
                             "both screens created with te and v_sync")
        if not self.__calibrated:
            self.__calibrate()
        self.__apply_trim()
        self.__walk = 0
        # The scans start up to half a period out, which the hold closes at about a
        # line a period, so the first aligned frame spends a resync instead
        self.__resync_due = True
        self.__timeouts_seen = self.__f_disp.te_timeouts() + self.__l_disp.te_timeouts()
        self.__last_frame_ms = None
        self.__f_screen.__pair = self
        self.__align = True

    def stop_aligning(self):
        """Stop correcting, handing the following panel its own rate back."""
        if not self.__align:
            return

        self.__align = False
        if self.__calibrated:
            self.__release_panel()
            self.__f_screen.__pair = None

    def update(self, image, second=None, *, rotation=None, mirror=None,
               pixel_double=False, offset=None, tile=False,
               bg_color=None, v_sync=None):
        """Stream one image, or one each, to both screens at once."""
        first_screen, second_screen = self.__screens
        if second is None:
            second = image
        # The defaults resolve to constants, so a steady loop allocates none of these
        if (rotation is None and mirror is None and pixel_double is False
                and offset is None and tile is False and bg_color is None):
            rotations = mirrors = offsets = backgrounds = __BOTH_NONE
            doubles = tiles = __BOTH_FALSE
        else:
            rotations = self.__pair_values(rotation, "rotation")
            mirrors = self.__pair_values(mirror, "mirror")
            doubles = self.__pair_values(pixel_double, "pixel_double")
            offsets = self.__pair_offsets(offset)
            tiles = self.__pair_tiles(tile)
            backgrounds = self.__pair_values(bg_color, "bg_color")

        if self.__align:
            if v_sync is False:
                raise ValueError("an aligned pair waits on the tearing-effect signal every frame, "
                                 "since that is what alignment measures by. Call stop_aligning() "
                                 "for free-running frames.")

            # A pause leaves the pair drifted; past what the loop can hide, spend a resync
            # while the content is still stale. A frame outside the pair handed the trim
            # back and the panels drifted untrimmed meanwhile, so reapplying it spends one too
            due = self.__apply_trim() or self.__resync_due
            self.__resync_due = False
            last = self.__last_frame_ms
            if due or (last is not None and
                       time.ticks_diff(time.ticks_ms(), last) * self.__drift_us_per_ms > self.ABSORB_US):
                self.__resync()

        first_screen.prepare(image, rotation=rotations[0], mirror=mirrors[0],
                             pixel_double=doubles[0], offset=offsets[0],
                             tile=tiles[0], bg_color=backgrounds[0])
        second_screen.prepare(second, rotation=rotations[1], mirror=mirrors[1],
                              pixel_double=doubles[1], offset=offsets[1],
                              tile=tiles[1], bg_color=backgrounds[1])
        update_pair(first_screen, second_screen, v_sync=v_sync)

        if self.__align:
            self.__correct()
            self.__last_frame_ms = time.ticks_ms()

    def __calibrate(self):
        # Probe both periods, trim the faster panel onto the slower in whole porch lines,
        # then sweep the rate codes on the trimmed panel, so the excursion shifts price
        # the periods the pair actually runs. The nominal rates are not linear in the
        # divider, so every code is probed.

        # Said at the default level: a mute four-second constructor reads as a hung board
        logging.info("> Calibrating the screen pair, about four seconds ...")
        started = time.ticks_ms()

        screens = self.__screens
        displays = tuple(screen.__display for screen in screens)

        # The first probe after bringup reads long and settles within a second, so it is discarded
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

        # A panel's line time is fixed by its oscillator; the porch moves how many a refresh spends
        line_us = [period / screen.__line_slots
                   for period, screen in zip(periods, screens)]
        s_line = line_us[fi]

        # Floored, so the follower stays the faster panel: the dither only ever slows it
        trim = int((periods[li] - periods[fi]) // s_line)
        back, front = f_screen.__porch

        # Both refusals run before anything moves a panel
        if back + trim + front > self.BLANKING_CEILING_LINES:
            # Different panel types take their rates from their own PROFILES, which has a fix
            if screens[0].framerate != screens[1].framerate:
                remedy = (f"Set both screens to the same framerate, {screens[0].framerate}fps and "
                          f"{screens[1].framerate}fps being too far apart")
            else:
                remedy = "Pair better-matched panels"
            raise ValueError("these panels' refreshes sit further apart than a porch trim can "
                             f"bridge. {remedy}, or create the pair with align=False.")

        trims = [0, 0]
        trims[fi] = trim
        tightest, margins_us, quanta = __tightest_margin(
            screens, trims, line_us,
            [display.wire_window_us() for display in displays])
        margin_us = margins_us[tightest]
        if quanta + self.DITHER_FRACTION * margin_us > margin_us or margin_us <= 0:
            raise ValueError(f"{screens[tightest]} keeps only {margin_us:.0f}us of tearing margin, "
                             f"and holding a pair costs {quanta:.0f}us of granularity plus a "
                             "reserve. Drop the rate a step, or create the pair with align=False.")

        if trim:
            f_screen.__set_porch(back + trim, front)
            time.sleep_ms(100)
            held = displays[fi].te_probe(self.PROBE_MS)[0]
            if held:
                # One verify pass: a trim priced from one reading lands whole lines out
                correction = int((periods[li] - held) // s_line)
                if correction:
                    back, front = f_screen.__porch
                    f_screen.__set_porch(back + correction, front)
                    trim += correction
                periods[fi] = int(round(held + correction * s_line))
            else:
                periods[fi] = int(round(periods[fi] + trim * s_line))
            logging.debug(f"> Trimmed the follower {trim} porch lines, "
                          f"{periods[li] - periods[fi]}us a period left")

        # The follower's slot count, which the trim just moved
        line_slots = f_screen.__line_slots

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
                    screen.__command(screen.CONTROLLER.REG_FRCTRL2, table[ordered[rate_index]])
                    time.sleep_ms(100)
                    period = screen.__display.te_probe(self.PROBE_MS)[0]
                    if period:
                        sweep[i][rate_index] = period
            screen.__command(screen.CONTROLLER.REG_FRCTRL2, table[ordered[nominal]])
            time.sleep_ms(100)

        # What the trim left, under one line a period, which the dither carries at a duty
        natural = line_slots * (1.0 / periods[fi] - 1.0 / periods[li])  # lines per us
        logging.debug(f"> Pair drift {natural * periods[fi]:.2f} lines a period after the trim")

        # Excursion options per panel: the no-op, then each probed code held for one to
        # MAX_FRAMES frames. A slower follower or a faster leader closes a positive error.
        options = ([(None, 0, 0.0)], [(None, 0, 0.0)])
        for i in (0, 1):
            for rate_index, period in sweep[i].items():
                stretch = line_slots * (period / periods[i] - 1.0)
                per_frame = -stretch if i == fi else stretch
                code = tables[i][rates[i][rate_index]]
                for frames in range(1, self.MAX_FRAMES + 1):
                    options[i].append((code, frames, per_frame * frames))

        # Every plan a resync could use, priced once. A plan pays the drift over its own
        # run, half a period of wait plus one per frame, and only codes pushing one way pair.
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
        self.__s_line = s_line
        self.__natural = natural
        # What a pause costs, floored at the oscillators' wander: without the floor a
        # well-matched pair never prices a pause as worth a resync
        self.__drift_us_per_ms = max(abs(natural) * s_line * 1000.0,
                                     self.WANDER_US_PER_PERIOD * 1000.0 / periods[fi])
        self.__target_lines = self.TARGET_US / s_line
        self.__floor_us = self.DEADBAND_LINES * s_line
        self.__reg_tescan = controller.REG_TESCAN
        self.__nominal_codes = tuple(tables[i][rates[i][nominals[i]]] for i in (0, 1))
        self.__te_lines = tuple(screen.__te_line for screen in screens)
        self.__plans = plans
        self.__trim_lines = trim
        self.__trim_on = trim != 0
        self.__calibrated = True

        # The opener promised four seconds, so say when they are up
        if logging.level < logging.LOG_DEBUG:
            logging.info("> Screen pair calibrated")
        else:
            logging.debug(f"> Calibrated in {time.ticks_diff(time.ticks_ms(), started)}ms, "
                          f"predicted skew floor {self.__floor_us:.0f}us")

    def __send_walk(self, walk):
        if walk != self.__walk_sent:
            self.__f_screen.__command(self.__reg_tescan, bytes((walk >> 8, walk & 0xFF)))
            self.__walk_sent = walk

    def __send_dither(self, want):
        # want is -1, 0 or +1 porch lines off the trim
        if want != self.__dither:
            back, front = self.__f_screen.__porch
            self.__f_screen.__set_porch(back + want - self.__dither, front)
            self.__dither = want

    def __restore_panel(self):
        # A non-zero TESCAN narrows the TE pulse to about a line, which only a pair
        # frame's poll absorbs. The static trim stays on; __release_panel takes that too.
        self.__send_walk(0)
        self.__send_dither(0)
        self.__walk = 0

    def __release_panel(self):
        # Runs before any frame outside the pair, so a lone update keeps no period it did not ask for
        self.__restore_panel()
        if self.__trim_on:
            back, front = self.__f_screen.__porch
            self.__f_screen.__set_porch(back - self.__trim_lines, front)
            self.__trim_on = False

    def __apply_trim(self):
        # Returns whether the trim had been handed back
        if not self.__trim_lines or self.__trim_on:
            return False

        back, front = self.__f_screen.__porch
        self.__f_screen.__set_porch(back + self.__trim_lines, front)
        self.__trim_on = True
        return True

    def __correct(self):
        # One proportional correction from the last pair frame's write starts
        stats_f = self.__f_disp.stats()
        stats_l = self.__l_disp.stats()
        if self.__n_hi is None:
            # The tear margin needs a streamed frame's length, so the walk's
            # bounds wait for the first one
            margin = (self.__f_screen.__line_slots + self.__f_screen.height
                      - stats_f.frame_us / self.__s_line)
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
        # One porch line each way: +1 bleeds the walk back and cancels drift it cannot,
        # -1 hastens a follower left late with no walk to give back
        if need > (self.__n_hi - walk) + self.ASSIST_LINES or walk > self.__dither_hi:
            dither = 1
        elif walk == 0 and need < -self.ASSIST_LINES:
            dither = -1
        else:
            dither = 0
        self.__send_dither(dither)

    def __resync(self):
        # The walk narrows the TE pulse and a capture needs it wide, so zero the walk,
        # measure, correct, and let the loop rebuild it. Runs between frames, so it
        # costs one late frame.
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
        # The cheapest plan landing within ACCURACY_LINES, else the closest at any cost
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
        screen = self.__screens[index]
        screen.__command(screen.CONTROLLER.REG_FRCTRL2,
                       self.__nominal_codes[index] if code is None else code)
        self.__te_lines[index].init(Pin.IN, pull=Pin.PULL_DOWN)

    def __run_schedule(self, schedule):
        # schedule[i] is (code, frames), 0 frames leaving that panel alone. A code goes on
        # just after one of that panel's TE falls and comes off after a counted number of
        # later ones, so the frames it spans are whole. Both panels count at once.
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
