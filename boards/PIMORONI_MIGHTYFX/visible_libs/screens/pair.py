# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Two screens, already built on their own SP/CE ports, presented together as one. A pair
# streams both at once and holds their refreshes together, correcting the faster panel's
# porch every frame. update_pair() streams two prepared screens and holds nothing.

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
                         "stream. broadcast() shares a port")

    # A reservation is shared out across the pair, so one alone leaves both short
    if first.__reserve != second.__reserve:
        raise ValueError("update_pair needs both screens built with the same reserve, since a "
                         "reservation is shared out across the pair. Set it on both, or on neither")

    if v_sync is None:
        v_sync = first.__v_sync and second.__v_sync
    elif v_sync and not (first.__v_sync and second.__v_sync):
        raise ValueError("v_sync needs both screens created with te, since each waits on its own "
                         "panel's tearing-effect signal")

    spidisplay.update_all(first.__display, second.__display, v_sync=v_sync)

    # Revealed together, both backlights wait the longer of the two scans owed and light as one
    together = first.reveal_together and second.reveal_together
    owed_first = first.__drawn(keep_dark=together)
    owed_second = second.__drawn(keep_dark=together)

    # Check if both owe a wait, since lighting one alone defeats revealing together
    if together and owed_first is not None and owed_second is not None:
        time.sleep_ms(owed_first if owed_first > owed_second else owed_second)
        first.backlight.__reveal_now()
        second.backlight.__reveal_now()


class ScreenPair:
    """Two screens on their own SP/CE ports, presented together as one."""

    # The faster panel is the follower and the slower the reference. Three moves hold
    # the follower on it. The walk is the controller's TESCAN line shifting its scan a
    # few lines a frame, the dither is one porch line either way, and an excursion is a
    # rate code held for whole frames to close the drift a pause left.

    # The per-frame correction
    DEADBAND_LINES = 2          # Skew under this is left alone
    STEP_GAIN = 1.0             # Walk lines asked per line of error, so one frame aims to close it all
    MAX_STEP = 8                # The most the walk moves in a frame, however large the error
    SLIP_FRACTION = 0.6         # Of the tear margin, the walk's ceiling
    DITHER_FRACTION = 0.4       # Of the margin, both the hold's reserve and the walk the dither joins at
    ASSIST_LINES = 4            # Lines of unmet need before the dither assists the walk

    PROBE_MS = 250              # Calibration's settled period reading, which needs longer than a presence probe
    SETTLE_MS = 100             # What a porch or rate change needs before a period reads true

    # The static trim lengthens the follower's blanking. Both panel types were measured
    # keeping a period linear in the porch out to this many lines
    BLANKING_CEILING_LINES = 56

    # The resync after a pause
    RATE_STEPS = (1, 2)         # Steps either side of the built rate a plan may run, the larger closing more, less exactly
    MAX_FRAMES = 3              # Frames of excursion a plan may spend on one panel
    ACCURACY_LINES = 5          # Close enough to hand over, so a plan stops paying for better
    ABSORB_US = 1430            # Handover error the loop hides, its 1,800us worst frame less a recovery's frame of drift
    WANDER_US_PER_PERIOD = 20   # Two free-running oscillators wander about 10us a period each
    TARGET_US = -300            # Aim off centre, the side leaving the follower needing the delay a walk can give
    CAPTURE_EDGES = 2           # TE falls per panel per phase capture, two being the fewest that name one
    CAPTURE_TIMEOUT_MS = 500    # The wait for those falls, far past the period two of them span
    SCHEDULE_TIMEOUT_MS = 250   # Only a silent panel reaches it, an excursion spanning MAX_FRAMES + 1 periods

    def __init__(self, first, second, align=None, reveal_together=False):
        """Present two screens as one, streamed at once and held to one refresh.
        align=None holds them where it can, True raises where it cannot, False leaves them alone."""
        if first is second:
            raise ValueError("a pair needs two different screens")
        if first.port is second.port:
            raise ValueError("a pair needs a screen on each SP/CE port, since one port is one "
                             "stream. broadcast() shares a port")
        if first.__reserve != second.__reserve:
            raise ValueError("a pair needs both screens built with the same reserve, since a "
                             "reservation is shared out across the pair. Set it "
                             "on both, or on neither")

        # Each port's backlight is what holds, so reveal_together goes on the screens
        if reveal_together:
            first.__reveal_together = True
            second.__reveal_together = True

        self.__screens = (first, second)
        self.__align = False
        self.__calibrated = False       # Whether the four-second pass is paid, which stop_aligning keeps

        self.__last_frame_ms = None     # When the last aligned frame streamed, None until one has
        self.__resync_due = False       # Whether the next aligned frame spends a resync
        self.__timeouts_seen = 0        # The panels' running timeout total, compared not counted

        self.__walk = 0                 # The TESCAN line the hold wants
        self.__walk_sent = 0            # What TESCAN last took, so an unchanged walk costs no command
        self.__walk_ceiling = None      # The walk's bound, None until a streamed frame prices the margin
        self.__dither = 0               # The porch line held either way, -1, 0 or +1 off the trim
        self.__dither_ceiling = 0       # The walk the dither starts helping past

        self.__trim_lines = 0           # The porch lines calibration lengthened the follower by
        self.__trim_on = False          # Whether they are on the panel now

        if align is None:
            # A request, not a requirement. Every reason a pair cannot hold alignment is
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
        # two readings differing silently. (None, None) is the one case where both mean the same
        if offset is None:
            return (None, None)
        if not isinstance(offset, (tuple, list)) or len(offset) != 2:
            raise ValueError("offset is (x, y) for both screens, or two of them for one screen each")

        if any(isinstance(element, (tuple, list)) for element in offset):
            # Per screen, each element an (x, y) pair, or None for centred
            for element in offset:
                if element is None:
                    continue
                if not isinstance(element, (tuple, list)) or len(element) != 2:
                    raise ValueError(f"{offset} reads as a per-screen offset, so each element is an "
                                     "(x, y) pair or None. A shared offset is (x, y) "
                                     "with plain coordinates")
                for coordinate in element:
                    if coordinate is not None and not isinstance(coordinate, int):
                        raise ValueError(f"{element} is not an (x, y) pair. Each coordinate is a "
                                         "number, or None for centred on that axis")
            return offset

        # Shared, one (x, y) applied to both screens
        for coordinate in offset:
            if coordinate is not None and not isinstance(coordinate, int):
                raise ValueError(f"{offset} is not an (x, y) pair. Each coordinate is a number, or None "
                                 "for centred on that axis. A per-screen offset is two such pairs.")
        return (offset, offset)

    @staticmethod
    def __pair_tiles(tile):
        # Shared unless either element is itself a pair, the rule offset follows
        if not isinstance(tile, (tuple, list)):
            return (tile, tile)
        if len(tile) != 2:
            raise ValueError("tile is one value for both axes, or an (x, y) pair. A "
                             "per-screen tile is two of either")

        if any(isinstance(element, (tuple, list)) for element in tile):
            for element in tile:
                if isinstance(element, (tuple, list)) and len(element) != 2:
                    raise ValueError(f"{element} is not an (x, y) pair of tile settings")
            return tile

        return (tile, tile)

    @staticmethod
    def __fold(delta, period):
        # Fold into half a period either way, keeping the sign
        d = delta % period
        if d > period // 2:
            d -= period
        return d

    @staticmethod
    def __signed_mod(delta, period):
        # Two 32-bit microsecond stamps, folded to signed 32 bits before the period
        # reduction. 2**32 is not a multiple of a period, so an unsigned wrap would bias
        # every negative skew by 2**32 % period
        return ScreenPair.__fold(((delta + 0x80000000) & 0xFFFFFFFF) - 0x80000000, period)

    @property
    def screens(self):
        """The pair's two screens, in the order they were given."""
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
        self.__timeouts_seen = self.__follower_display.te_timeouts() + self.__reference_display.te_timeouts()
        self.__last_frame_ms = None
        self.__follower.__pair = self
        self.__align = True

    def stop_aligning(self):
        """Stop correcting, handing the following panel its own rate back."""
        if not self.__align:
            return

        self.__align = False
        if self.__calibrated:
            self.__release_panel()
            self.__follower.__pair = None

    def update(self, image, second=None, *, rotation=None, mirror=None,
               pixel_double=False, offset=None, tile=False,
               bg_color=None, v_sync=None):
        """Stream one image, or one each, to both screens at once."""
        first_screen, second_screen = self.__screens
        if second is None:
            second = image

        # Check if the placement is all default
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

            # A pause leaves the pair drifted. Past what the loop can hide, spend a resync
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
        # the periods the pair actually runs. The table's rates are not linear in the
        # divider, so each code the sweep uses has to be measured.

        # Said at the default level, a mute four-second constructor reading as a hung board
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

        follower_index = 0 if periods[0] <= periods[1] else 1      # The faster panel follows the slower
        reference_index = 1 - follower_index
        follower = screens[follower_index]
        controller = follower.CONTROLLER

        # A panel's line time is fixed by its oscillator, the porch moving how many a refresh spends
        line_us = [period / screen.__line_slots
                   for period, screen in zip(periods, screens)]
        follower_line_us = line_us[follower_index]

        # Floored, so the follower stays the faster panel, the dither only ever slowing it
        trim = int((periods[reference_index] - periods[follower_index]) // follower_line_us)
        back, front = follower.__porch

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
        trims[follower_index] = trim
        tightest, margins_us, quanta = __tightest_margin(
            screens, trims, line_us,
            [display.wire_window_us() for display in displays])
        margin_us = margins_us[tightest]
        if quanta + self.DITHER_FRACTION * margin_us > margin_us or margin_us <= 0:
            raise ValueError(f"{screens[tightest]} is {margin_us:.0f}us from tearing where the "
                             f"hold needs {quanta:.0f}us plus a reserve. Drop the rate a step, "
                             "or create the pair with align=False.")

        # Past both refusals, so nothing above has moved a panel
        if trim:
            follower.__set_porch(back + trim, front)
            time.sleep_ms(self.SETTLE_MS)
            held = displays[follower_index].te_probe(self.PROBE_MS)[0]
            if held:
                # One verify pass, since a trim priced from one reading lands whole lines out
                correction = int((periods[reference_index] - held) // follower_line_us)
                if correction:
                    back, front = follower.__porch
                    follower.__set_porch(back + correction, front)
                    trim += correction
                periods[follower_index] = int(round(held + correction * follower_line_us))
            else:
                # A silent probe leaves the trim's arithmetic as the period, unverified
                periods[follower_index] = int(round(periods[follower_index] + trim * follower_line_us))
            logging.debug(f"> Trimmed the follower {trim} porch lines, "
                          f"{periods[reference_index] - periods[follower_index]}us a period left")

        # The follower's slot count, which the trim just moved
        line_slots = follower.__line_slots

        # Per panel, the sorted rate table, the built rate's index, and a probed
        # settled period at one and two steps each way where the table has them.
        tables = []
        rates = []
        nominals = []
        sweep = [{}, {}]
        for i, screen in enumerate(screens):
            table = screen.CONTROLLER.FRAME_RATE_CONTROL
            # Sorted ascending by rate, since the controller's codes rise as the rate
            # falls and a step here has to be a step in rate
            ordered = sorted(table)
            nominal = ordered.index(screen.framerate)
            tables.append(table)
            rates.append(ordered)
            nominals.append(nominal)
            for steps in self.RATE_STEPS:
                # A step past the table's ends, or a probe reading nothing, leaves that
                # option out and the plan builder one fewer to price
                for rate_index in (nominal - steps, nominal + steps):
                    if not 0 <= rate_index < len(ordered):
                        continue
                    screen.__command(screen.CONTROLLER.REG_FRCTRL2, table[ordered[rate_index]])
                    time.sleep_ms(self.SETTLE_MS)
                    period = screen.__display.te_probe(self.PROBE_MS)[0]
                    if period:
                        sweep[i][rate_index] = period

            # Back on its built rate, which every measurement after this assumes
            screen.__command(screen.CONTROLLER.REG_FRCTRL2, table[ordered[nominal]])
            time.sleep_ms(self.SETTLE_MS)

        # What the trim left, under one line a period, which the dither carries at a duty
        natural = line_slots * (1.0 / periods[follower_index]
                                - 1.0 / periods[reference_index])  # lines per us
        logging.debug(f"> Pair drift {natural * periods[follower_index]:.2f} lines a period after the trim")

        # Excursion options per panel, the no-op and then each probed code held for one to
        # MAX_FRAMES frames. A slower follower or a faster reference closes a positive error.
        options = ([(None, 0, 0.0)], [(None, 0, 0.0)])
        for i in (0, 1):
            for rate_index, period in sweep[i].items():
                stretch = line_slots * (period / periods[i] - 1.0)
                per_frame = -stretch if i == follower_index else stretch
                code = tables[i][rates[i][rate_index]]
                for frames in range(1, self.MAX_FRAMES + 1):
                    options[i].append((code, frames, per_frame * frames))

        # Every plan a resync could use, priced once. A plan pays the drift over its own
        # run, half a period of wait plus one per frame, and only codes pushing one way pair.
        settling = natural * periods[follower_index]
        plans = {}
        for want_negative in (False, True):
            entries = []
            for follower_code, follower_frames, follower_lines in options[follower_index]:
                if follower_frames and (follower_lines < 0) != want_negative:
                    continue
                for reference_code, reference_frames, reference_lines in options[reference_index]:
                    if reference_frames and (reference_lines < 0) != want_negative:
                        continue
                    cost = max(follower_frames, reference_frames)
                    shift = follower_lines + reference_lines + settling * (cost + 0.5)
                    schedule = [None, None]
                    schedule[follower_index] = (follower_code, follower_frames)
                    schedule[reference_index] = (reference_code, reference_frames)
                    entries.append((shift, cost, tuple(schedule)))
            plans[want_negative] = entries

        self.__follower = follower
        self.__follower_display = displays[follower_index]
        self.__reference_display = displays[reference_index]
        self.__follower_period_us = periods[follower_index]
        self.__follower_line_us = follower_line_us
        self.__natural = natural

        # What a pause costs, floored at the oscillators' wander. Without the floor a
        # well-matched pair never prices a pause as worth a resync
        self.__drift_us_per_ms = max(abs(natural) * follower_line_us * 1000.0,
                                     self.WANDER_US_PER_PERIOD * 1000.0 / periods[follower_index])
        self.__target_lines = self.TARGET_US / follower_line_us

        # The skew the deadband implies, logged below and read nowhere else
        self.__floor_us = self.DEADBAND_LINES * follower_line_us
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
        # The walk is the TESCAN scanline, so the register value and the walk are one number
        if walk != self.__walk_sent:
            self.__follower.__command(self.__reg_tescan, bytes((walk >> 8, walk & 0xFF)))
            self.__walk_sent = walk

    def __send_dither(self, want):
        # want is -1, 0 or +1 porch lines off the trim
        if want != self.__dither:
            back, front = self.__follower.__porch
            self.__follower.__set_porch(back + want - self.__dither, front)
            self.__dither = want

    def __restore_panel(self):
        # A non-zero TESCAN narrows the TE pulse to about a line, which only a pair
        # frame's poll absorbs. The static trim stays on, and __release_panel takes that too.
        self.__send_walk(0)
        self.__send_dither(0)
        self.__walk = 0

    def __release_panel(self):
        # Runs before any frame outside the pair, so a lone update keeps no period it did not ask for
        self.__restore_panel()
        if self.__trim_on:
            back, front = self.__follower.__porch
            self.__follower.__set_porch(back - self.__trim_lines, front)
            self.__trim_on = False

    def __apply_trim(self):
        # Returns whether the trim had been handed back
        if not self.__trim_lines or self.__trim_on:
            return False

        back, front = self.__follower.__porch
        self.__follower.__set_porch(back + self.__trim_lines, front)
        self.__trim_on = True
        return True

    def __correct(self):
        # One proportional correction from the last pair frame's write starts
        follower_stats = self.__follower_display.stats()
        reference_stats = self.__reference_display.stats()
        if self.__walk_ceiling is None:
            # The tear margin needs a streamed frame's length, so the walk's
            # bounds wait for the first one
            margin = (self.__follower.__line_slots + self.__follower.height
                      - follower_stats.frame_us / self.__follower_line_us)

            # Floored, since a tight margin would otherwise leave the walk nowhere to
            # move and the dither engaged on every frame
            self.__walk_ceiling = max(4, int(margin * self.SLIP_FRACTION))
            self.__dither_ceiling = max(2, int(margin * self.DITHER_FRACTION))

        timeouts = self.__follower_display.te_timeouts() + self.__reference_display.te_timeouts()
        if timeouts != self.__timeouts_seen:
            # A wait that timed out did not end on a tearing edge, so this frame's write
            # stamps say nothing about the panels' phase
            self.__timeouts_seen = timeouts
            return

        err_us = self.__signed_mod(follower_stats.write_start_us - reference_stats.write_start_us,
                                   self.__follower_period_us)
        need = -err_us / self.__follower_line_us          # Positive means the follower must be delayed
        walk = self.__walk
        if abs(need) >= self.DEADBAND_LINES:
            step = round(self.STEP_GAIN * need)
            step = max(-self.MAX_STEP, min(self.MAX_STEP, step))
            walk = max(0, min(self.__walk_ceiling, walk + step))  # Floored, since a scanline has no negative
        self.__walk = walk
        self.__send_walk(walk)

        # Check if a porch line either way is needed, the dither moving one at most
        if need > (self.__walk_ceiling - walk) + self.ASSIST_LINES or walk > self.__dither_ceiling:
            dither = 1      # Bleed the walk back, and cancel the drift it cannot
        elif walk == 0 and need < -self.ASSIST_LINES:
            dither = -1     # Hasten a follower left late with no walk to give back
        else:
            dither = 0
        self.__send_dither(dither)

    def __resync(self):
        # The walk narrows the TE pulse a capture needs wide, so it is zeroed here and the
        # loop rebuilds it. Runs between frames, at the cost of one late frame
        self.__restore_panel()
        captured = spidisplay.te_phase(self.__follower_display, self.__reference_display, self.__follower_period_us,
                                       self.CAPTURE_EDGES, self.CAPTURE_TIMEOUT_MS)
        if captured is None:
            return          # Too few edges, so let the fine loop walk it out
        skew_us, age_us = captured
        if abs(skew_us) <= self.ABSORB_US:
            return
        aged = -skew_us / self.__follower_line_us + self.__natural * age_us
        self.__run_schedule(self.__plan_for(aged - self.__target_lines))

    def __plan_for(self, error):
        # The cheapest plan landing within ACCURACY_LINES, else the closest at any cost
        LEFT, COST, SCHEDULE = 0, 1, 2      # A candidate's three elements

        cheapest = None
        closest = None
        for shift, cost, schedule in self.__plans[error > 0]:
            left = abs(error + shift)
            if closest is None or left < closest[LEFT]:
                closest = (left, cost, schedule)
            if left > self.ACCURACY_LINES:
                continue
            # Cheaper wins, and as cheap is settled by whichever lands closer
            if cheapest is None or (cost, left) < (cheapest[COST], cheapest[LEFT]):
                cheapest = (left, cost, schedule)
        best = cheapest if cheapest is not None else closest
        return best[SCHEDULE]

    def __set_rate(self, index, code):
        screen = self.__screens[index]
        screen.__command(screen.CONTROLLER.REG_FRCTRL2,
                         self.__nominal_codes[index] if code is None else code)

        # The command drove DC, so a shared TE line comes back as an input
        self.__te_lines[index].init(Pin.IN, pull=Pin.PULL_DOWN)

    def __run_schedule(self, schedule):
        # A code goes on just after one of that panel's TE falls and comes off after a
        # counted number of later ones, so the frames it spans are whole. An entry of no
        # frames leaves that panel alone. Both panels count at once.

        # DONE covers a panel that never takes part as well as one that has finished
        WAITING, COUNTING, DONE = 0, 1, 2
        CODE, FRAMES = 0, 1         # A schedule entry's two elements
        PANELS = 2

        pins = self.__te_lines
        # Read as inputs, whatever the last command left them as
        for pin in pins:
            pin.init(Pin.IN, pull=Pin.PULL_DOWN)
        state = [DONE if schedule[i][FRAMES] <= 0 else WAITING for i in range(PANELS)]
        counts = [0] * PANELS
        levels = [pin.value() for pin in pins]
        start = time.ticks_ms()

        # Polled here, since each fall has to be answered with a command
        while state[0] != DONE or state[1] != DONE:
            if time.ticks_diff(time.ticks_ms(), start) >= self.SCHEDULE_TIMEOUT_MS:
                break
            for i in range(PANELS):
                if state[i] == DONE:
                    continue
                value = pins[i].value()
                if value == levels[i]:
                    continue
                levels[i] = value
                if value:
                    continue                # Only the falls bound a frame
                if state[i] == WAITING:
                    self.__set_rate(i, schedule[i][CODE])
                    state[i] = COUNTING
                else:
                    counts[i] += 1
                    if counts[i] >= schedule[i][FRAMES]:
                        self.__set_rate(i, None)
                        state[i] = DONE
                levels[i] = pins[i].value()     # That command moved the line, so re-read the level

        # A timeout leaves a panel mid-excursion, so put every unfinished one back
        for i in range(PANELS):
            if state[i] != DONE:
                self.__set_rate(i, None)
