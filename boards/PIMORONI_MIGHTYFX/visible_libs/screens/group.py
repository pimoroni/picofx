# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Several of a port's screens driven as one, sharing a frame: calibrated onto one
# refresh rate, brought into phase, and held there from the frames they already write.

import logging
import time

from .base import ScreenBase, __tightest_margin

# time.ticks_us() wraps at 2**30 and the C module's stamps at 2**32; their low bits
# agree, so every stamp is reduced to 30 bits and the two share one arithmetic
TICKS_MASK = 0x3FFFFFFF


class ScreenGroup(ScreenBase):
    """Several of a port's screens driven as one, sharing a frame."""

    # How a group holds its members together, in three stages. Calibration probes each
    # member's period and trims every porch toward the slowest member, the reference,
    # until the rates agree to a fraction of a line. Acquisition then runs each
    # member's porch long or short for whole periods until their scans fall together.
    #
    # The hold keeps them there. Each member has a booked phase against a common grid,
    # advanced between frames by its modelled rate error. The synced member's TE fall
    # is the frame's write stamp, so its booking is replaced by a measurement. Every
    # other member is dithered a porch line either way to keep its booked error nearest
    # zero, and a member far enough out to be tearing anyway walks in faster. The trim
    # keeps the rate models current as the panels warm, by rotating which member a
    # frame waits on or by probing one between frames.
    #
    # Three members have names. The leader is the one a frame waits on, nominated at
    # construction and moved by a rotating trim. The reference is the slowest, whose
    # rate the others are trimmed to and whose booking errors are held against. The
    # synced member is whichever the last frame's wait ended on: the leader, unless a
    # narrowed write left it out.

    # The first probe after bringup reads long, so each panel's first reading is
    # discarded. 300ms is about 13 periods; at 100 one miscounted edge moved a trim
    # by three lines.
    PROBE_MS = 300
    SETTLE_MS = 100

    # Of the fastest member's margin, what the hold may spend
    DITHER_FRACTION = 0.4

    # Frames between probe-mode measurements, about two seconds
    TRIM_FRAMES = 30

    # How far one anchor gap moves a member's modelled rate. The rates wander about
    # 10us a period, so the model leans on the newest reading, itself good to about 1us.
    RATE_GAIN = 0.5

    # Of a line, how far a modelled rate drifts before a whole porch line corrects
    # it. Half a line would fire corrections on the 1.54's own wander.
    TRIM_DEADBAND = 0.75

    # The most one correction moves a member; whole lines at once are a visible step
    TRIM_LIMIT_LINES = 1

    # Porch lines an acquisition's excursion runs at, and the depth the hold's walk
    # reaches. Neither writes the member while it travels, so both may move it either way.
    EXCURSION_LINES = 8
    WALK_LINES = 24

    # The shortest back porch a walk may leave: with the front porch it keeps the
    # tearing pulse above a millisecond, so a walking member is still readable as the wait target
    WALK_FLOOR_LINES = 8

    # The longest a frame waits for the members to come together before it goes out
    # and tears on whoever is still out: one spoiled frame beats a stalled wall
    WALK_WAIT_MS = 600

    # Clearance held beyond coming into the window: at centre_us exactly the following
    # scan overtakes the write on the last row. Two, a dithered line landing with a
    # one-frame ambiguity.
    WAIT_SLACK_LINES = 2

    # How far a capture's two falls may span from a period before its phase is suspect
    CAPTURE_TOLERANCE_LINES = 8

    # Sweeps allowed to bring the phases together; it converges in two
    ACQUIRE_TRIES = 3

    # Past this gap between frames a rate reading is not trusted, and a hold not yet
    # fed its first frame reacquires. The bookings survive any pause, phases being modular.
    HOLD_PAUSE_MS = 1000

    # Past this gap a resume sweeps the phases before walking, an extrapolation that
    # far being worth less than a measurement
    SWEEP_PAUSE_MS = 1000

    def __init__(self, *screens, leader=None, align=None, trim=None,
                 rotation=None, mirror=None, reveal_together=False, parent=None):
        if not screens:
            raise ValueError("a broadcast group needs at least one screen")

        port = screens[0].port
        for screen in screens:
            if screen.port is not port:
                raise ValueError("a broadcast group has to be on one port, since two ports are two streams")

        # The backlight counts panels, not whatever wrote them, so the members carry it
        if reveal_together:
            for screen in screens:
                screen.__reveal_together = True

        # A subset is a member set over its parent's display: it claims no members and
        # builds no display
        if parent is not None:
            for screen in screens:
                if screen not in parent.screens:
                    raise ValueError(f"{screen} is not a member of this group, so it cannot "
                                     "be in a subset of it")
            # A subset inherits the parent's nomination; leader=False declines the wait
            # for this set alone
            nominated = parent.__leader if leader is None else leader
            if nominated is False:
                nominated = None
            super().__init__(port, parent.__display, parent.width, parent.height,
                             parent.__bitdepth, parent.backlight, nominated is not None,
                             nominated is not None, parent.__reserve,
                             members=tuple(screens), leader=nominated,
                             rotation=parent.rotation if rotation is None else rotation,
                             mirror=parent.mirror if mirror is None else mirror)
            self.__subset_of = parent
            self.__subset_displays = tuple(screen.__display for screen in screens)
            # Inherited live, so a rotating trim moving the parent's leader moves this one's
            if leader is None:
                self.__leader_source = parent
            # Answered through a subset as the parent would; is_aligned() forwards live
            self.__reference = parent.__reference
            self.__acquired_us = parent.__acquired_us
            self.__trim_mode = parent.__trim_mode
            return

        for screen in screens:
            if screen.__group is not None:
                raise ValueError("a screen belongs to one group at a time, and one of these is "
                                 "already in another. Take a subset of the group it is in, or "
                                 "build a single group over every panel that shares a frame.")

        # A hub's panels scan independently, so no edge is safe for every one: the
        # nominated panel comes out clean and the rest tear. Naming one refuses if unmet.
        nominated = None
        if leader is not False:
            shared = [screen for screen in screens if screen.__shared_te]
            if leader is not None:
                if leader not in screens:
                    raise ValueError(f"{leader} is not a member of this group, so it cannot be the "
                                     "one its frames wait on")
                if not leader.__shared_te:
                    raise ValueError(f"{leader} does not read its tearing-effect signal from the "
                                     "line this group reads. Build every member with te set to "
                                     "the DC line they share, which needs each breakout's diode.")
                nominated = leader
            elif shared:
                nominated = shared[0]
            else:
                logging.info("screens: this group's panels carry no shared tearing-effect signal, "
                             "so its frames will not wait and every panel may tear. Build the "
                             "members with te set to the DC line they share to nominate one.")

        first = screens[0]

        # broadcast() refuses these too, in the driver's words. The cache width, ring depth
        # and write command have no reading here, so those three stay its to report.
        for position, screen in enumerate(screens[1:], start=2):
            if (screen.width, screen.height) != (first.width, first.height):
                raise ValueError(f"screen size mismatch: panel {position} is "
                                 f"{screen.width}x{screen.height} whereas panel 1 is "
                                 f"{first.width}x{first.height}. Group panels by size")
            if screen.__bitdepth != first.__bitdepth:
                raise ValueError(f"bitdepth mismatch: panel {position} is {screen.__bitdepth}-bit "
                                 f"whereas panel 1 is {first.__bitdepth}-bit")
            if screen.__display.baudrate() != first.__display.baudrate():
                raise ValueError(f"baudrate mismatch: panel {position} runs at "
                                 f"{screen.__display.baudrate()} whereas panel 1 runs at "
                                 f"{first.__display.baudrate()}")
            if screen.__display.band_rows() != first.__display.band_rows():
                raise ValueError(f"band_lines mismatch: panel {position} takes "
                                 f"{screen.__display.band_rows()} rows at a time whereas panel 1 "
                                 f"takes {first.__display.band_rows()}")

        display = port.__bus.broadcast(*[screen.__display for screen in screens])

        # A group places its own frames, so an unnamed rotation is upright, not the
        # first member's
        rotation = 0 if rotation is None else rotation
        mirror = False if mirror is None else bool(mirror)
        if any(screen.rotation != rotation or screen.mirror != mirror for screen in screens):
            logging.info(f"screens: a group places its own frames, at rotation {rotation}"
                         f"{' and mirrored' if mirror else ''}, so its members' own placement is "
                         "not used. Create the group with the placement its panels want.")

        # The backlight is the first member's, screens on a port sharing the one PWM
        super().__init__(port, display, first.width, first.height, first.__bitdepth,
                         first.backlight, nominated is not None, nominated is not None,
                         first.__reserve, members=tuple(screens), leader=nominated,
                         rotation=rotation, mirror=mirror)

        # Position by member, so a frame's bookkeeping never scans the tuple
        self.__member_index = {screen: index for index, screen in enumerate(screens)}
        self.__reference_index = 0
        # Three states: one rate stops the members drifting apart quickly, an acquisition
        # brings their scans together at one instant, and only a hold keeps them there
        self.__acquired_us = 0
        self.__holding = False
        self.__reference = None
        self.__target_us = 0
        self.__margins = ()
        self.__aim_us = 0
        self.__line_us = ()
        self.__trim_at = 0
        self.__trim_frames = 0
        self.__corrections = 0
        # Diagnostics: frames written with a member past its tearing budget and the worst
        # excess, and captures whose two falls did not span a plausible period
        self.__exposed_frames = 0
        self.__worst_exposure_us = 0
        self.__past_budget_us = 0
        self.__suspect_sweeps = 0
        self.__worst_sweep_error_us = 0
        # The hold's state per member, armed by a successful acquisition
        self.__residual_us = [0.0] * len(screens)
        self.__phase_us = [0.0] * len(screens)
        self.__dither = [0] * len(screens)
        self.__anchor_stamp = [0] * len(screens)
        self.__anchor_dither = [0.0] * len(screens)
        self.__anchor_skip = [False] * len(screens)
        self.__fresh_hold = False
        self.__walking = False
        self.__centre_us = 0
        self.__held_stamp = 0
        self.__swept_at = 0
        self.__grid_at = 0
        self.__grid_phases = ()
        # A lone member is in phase with itself, so a required alignment is already met
        if align is not False and len(screens) > 1:
            if nominated is None:
                # The leader block above already said why, so only a required alignment speaks again
                if align is True:
                    raise ValueError("align holds a group's panels in phase by their "
                                     "tearing-effect signal, so it needs every member built with "
                                     "te set to the DC line they share")
            else:
                self.__calibrate(align is True)

        # None rotates only once the members are held in phase: held to one rate but not
        # one phase, rotating moves which panel comes out clean and jumps every tear with it
        if trim not in (None, True, False, "rotate", "probe"):
            raise ValueError(f"{trim} is not a valid trim. Expected None, False, 'rotate', or 'probe'.")

        if not self.__target_us:
            if trim not in (None, False):
                logging.info("screens: this group holds no period for its members, so there is "
                             "nothing for a trim to correct toward")
            self.__trim_mode = False
        elif trim in (None, True):
            self.__trim_mode = "rotate" if self.__holding else False
        else:
            self.__trim_mode = trim

        # Last, so a construction that raised claims nothing
        for screen in screens:
            screen.__group = self

    def __calibrate(self, required):
        # The reference is the slowest member, so every trim lengthens a porch, the
        # direction that adds margin. required refuses where the members will not hold;
        # otherwise an unmet request says why.
        members = self.screens
        logging.info(f"> Calibrating {len(members)} screens, about "
                     f"{len(members) * self.PROBE_MS * 2 // 1000 + 1} seconds ...")

        periods = []
        for screen in members:
            if screen.__leader is None:
                self.__unaligned(required, f"{screen} carries no tearing-effect signal a group can "
                                           "read, so build every member with te set to the "
                                           "DC line they share")
                return
            period = self.__period_of(screen, settle=True)
            if not period:
                self.__unaligned(required, f"{screen} returned no period, so its tearing-effect "
                                           "signal is not reaching the shared line")
                return
            periods.append(period)

        # A panel's line time is fixed by its oscillator; the porch moves how many a refresh spends
        line_us = [period / screen.__line_slots for period, screen in zip(periods, members)]
        slowest = periods.index(max(periods))
        frame_us = self.__display.wire_window_us()
        trims = [int(round((periods[slowest] - period) / line))
                 for period, line in zip(periods, line_us)]

        tightest, margins_us, quanta = __tightest_margin(members, trims, line_us,
                                                         [frame_us] * len(members))
        # A diagnostic; nothing on the frame path reads it
        self.__margins = margins_us
        margin_us = margins_us[tightest]
        dither_reserve_us = self.DITHER_FRACTION * margin_us

        if quanta + dither_reserve_us > margin_us or margin_us <= 0:
            self.__unaligned(required, f"{members[tightest]} is {margin_us:.0f}us from tearing "
                                       f"where the hold needs {quanta:.0f}us plus a reserve. "
                                       "Lengthen every member's porch, or drop the rate a step")
            return

        # Past the refusal, so nothing above has moved a panel
        self.__reference = members[slowest]
        self.__reference_index = slowest
        for screen, trim in zip(members, trims):
            if trim:
                back, front = screen.__porch
                screen.__set_porch(back + trim, front)

        # One verify pass: a reading that miscounts an edge lands whole porch lines out
        time.sleep_ms(self.SETTLE_MS)
        held = [self.__period_of(screen) for screen in members]
        if all(held):
            target = max(held)
            for index, screen in enumerate(members):
                correction = int(round((target - held[index]) / line_us[index]))
                if correction:
                    back, front = screen.__porch
                    screen.__set_porch(back + correction, front)
                # The rate error the hold integrates, under half a line either way
                self.__residual_us[index] = held[index] + correction * line_us[index] - target
            logging.debug(f"screens: verified at {held}, spread {max(held) - min(held)}us")
            self.__target_us = target

        self.__line_us = tuple(line_us)

        # What a phase spread has to fit inside: the tightest member's margin less the reserve
        self.__aim_us = (1.0 - self.DITHER_FRACTION) * margin_us

        # A held group writes half the tightest margin after the fall: at the fall itself
        # a member scanning later has no budget, so the write floats mid-window instead
        self.__centre_us = int(margin_us / 2)

        if self.__target_us and self.__acquire():
            self.__arm_hold()
        logging.info(f"screens: aligned on {self.__reference}, trims {trims} porch lines, "
                     f"{margin_us:.0f}us of margin at the tightest member")

    def __phases(self):
        # Every member's phase at one instant, or None where one went silent. A shared
        # line carries one panel at a time, so each capture's last fall is aged forward
        # by the held period onto the last capture's end. Two falls is the fewest that
        # names one; every extra fall ages the earlier members by another period.
        rows = []
        for index, screen in enumerate(self.screens):
            falls, finished = self.__solo_capture(screen, 2, 200)
            if not falls:
                return None
            rows.append((falls[-1], finished))
            self.__check_span(index, falls)

        # Aged by the held period, averaged over a settled probe, not by this capture's own
        reference = rows[-1][1]
        self.__swept_at = reference & TICKS_MASK
        return [((reference - fall) & 0xFFFFFFFF) % self.__target_us
                for fall, _ in rows]

    def __acquire(self):
        # Bring the members' scans together. The sweep's own ageing error is what the
        # retries are for; a group still past the aim when they run out is armed from
        # its last sweep regardless, and the hold walks the rest in. Only a member going
        # silent fails. One more check than rounds, so the last round's outcome is measured.
        for attempt in range(self.ACQUIRE_TRIES + 1):
            errors, target = self.__sweep_errors()
            if errors is None:
                logging.info("screens: a member went silent during the phase sweep, so "
                             "the group is not in phase")
                return False

            spread = max(errors) - min(errors)
            settled = spread <= self.__aim_us
            if settled or attempt == self.ACQUIRE_TRIES:
                self.__acquired_us = spread
                self.__seed_grid(errors, target)
                if settled:
                    logging.info(f"screens: members brought into phase, spread {spread}us "
                                 f"after {attempt} excursions. It decays at the residual "
                                 f"rate spread until a hold carries it")
                else:
                    logging.info(f"screens: the members are still {int(spread)}us apart "
                                 f"against a {self.__aim_us:.0f}us aim, so the hold "
                                 f"walks the rest in, about a line time a frame")
                return True

            # A phase is the time since that member last fell, so one further on than
            # the reference waits the difference out
            self.__excurse(errors)

    def __sweep_errors(self):
        # Every member's phase error against the reference, folded since phases are
        # modular. Returns (errors, the reference's phase), or (None, None) on silence.
        phases = self.__phases()
        if phases is None:
            return None, None

        target = phases[self.__reference_index]
        return [self.__fold(phase - target) for phase in phases], target

    def __seed_grid(self, errors, target):
        # The grid is common, every member's ideal falls being the reference's, and the
        # bookings carry the offsets the sweep measured
        self.__grid_at = self.__swept_at
        self.__grid_phases = tuple([target] * len(self.screens))
        self.__phase_us = [-error for error in errors]

    def __excurse(self, errors):
        # A positive error is cancelled by delaying the member: its porch runs long for
        # whole periods and goes back after. Each member takes the nearer direction, and
        # all run at once, so a round costs the longest one.
        members = self.screens
        plans = []
        for index in range(len(members)):
            stretch = self.EXCURSION_LINES * self.__line_us[index]
            plans.append(int(round(errors[index] / stretch)))

        logging.debug(f"screens: errors {[int(e) for e in errors]}, "
                      f"excursions {plans} periods")

        for index, screen in enumerate(members):
            if plans[index]:
                lines = self.EXCURSION_LINES if plans[index] > 0 else -self.EXCURSION_LINES
                back, front = screen.__porch
                screen.__set_porch(back + lines, front)

        elapsed = 0
        for index in sorted(range(len(members)), key=lambda i: abs(plans[i])):
            if not plans[index]:
                continue
            run = abs(plans[index])
            time.sleep_ms(int((run - elapsed) * self.__target_us / 1000) + 1)
            elapsed = run
            lines = self.EXCURSION_LINES if plans[index] > 0 else -self.EXCURSION_LINES
            back, front = members[index].__porch
            members[index].__set_porch(back - lines, front)

    @staticmethod
    def __solo_capture(screen, edges, timeout_ms):
        # This member alone asserting on the shared line
        screen.__command(screen.CONTROLLER.REG_TEON, b"\x00")
        falls, finished = screen.__display.te_capture(edges, timeout_ms)
        screen.__command(screen.CONTROLLER.REG_TEOFF)
        return falls, finished

    def __check_span(self, index, falls):
        # A phase comes from the last fall alone, so a spurious edge books a member
        # wherever it fell. Counted only, the sweep still using what it measured.
        if len(falls) < 2 or not self.__target_us:
            return

        spanned = (falls[-1] - falls[0]) & TICKS_MASK
        error = spanned - self.__target_us
        if abs(error) > self.CAPTURE_TOLERANCE_LINES * self.__line_us[index]:
            self.__suspect_sweeps += 1
            if abs(error) > abs(self.__worst_sweep_error_us):
                self.__worst_sweep_error_us = error
            logging.debug(f"screens: a capture spanned {spanned}us against a "
                          f"{self.__target_us}us period, so the phase it gives "
                          f"may not be this member's")

    def __fold(self, error):
        # Onto half a period either way
        error %= self.__target_us
        return error - self.__target_us if error > self.__target_us / 2 else error

    def update(self, image, *, rotation=None, mirror=None, pixel_double=False,
               offset=None, tile=False, bg_color=None,
               v_sync=None, to=None):
        """Stream a frame to every member, or to those named in to."""
        owner = self.__subset_of or self
        if owner.__holding:
            owner.__walk_in(self.screens if to is None else to)
        super().update(image, rotation=rotation, mirror=mirror,
                       pixel_double=pixel_double, offset=offset, tile=tile,
                       bg_color=bg_color, v_sync=v_sync, to=to)
        synced = self.__synced_frame
        owner.__frame_ticked(self.__display.stats(), synced, owner.__sync_delay_us)
        owner.__tick_trim(synced)

    def __walk_in(self, written):
        # Nothing is written while this runs, so the group presents in one piece. A tick
        # needs no measurement; past SWEEP_PAUSE_MS it sweeps first, and past
        # WALK_WAIT_MS the frame goes out regardless.
        if self.__out_of_phase(written):
            if ((time.ticks_us() - self.__held_stamp) & TICKS_MASK) > self.SWEEP_PAUSE_MS * 1000:
                self.__reseed()

            deadline = time.ticks_add(time.ticks_ms(), self.WALK_WAIT_MS)
            nap = int(self.__target_us / 1000) + 1
            waited = 0
            while self.__out_of_phase(written):
                if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                    logging.info("screens: some panels are still out of phase, so this frame goes "
                                 "out and tears on them rather than holding the group up any longer")
                    break
                time.sleep_ms(nap)
                self.__tick_hold(time.ticks_us() & TICKS_MASK, -1)
                waited += 1
            if waited:
                logging.debug(f"screens: held the frame {waited} periods for the members to come together")

        if self.__past_budget_us:
            self.__exposed_frames += 1
            if self.__past_budget_us > self.__worst_exposure_us:
                self.__worst_exposure_us = int(self.__past_budget_us)

    def __reseed(self):
        # Members drift independently while nothing measures them, so re-anchoring one
        # fixes one: a fresh sweep rebooks them all. A silent member keeps the bookings.
        errors, target = self.__sweep_errors()
        if errors is None:
            logging.debug("screens: a member did not answer the sweep, so the walk keeps its bookings")
            return

        self.__seed_grid(errors, target)
        self.__held_stamp = self.__swept_at
        logging.debug(f"screens: swept the members after a pause, spread "
                      f"{int(max(errors) - min(errors))}us for the walk to close")

    def __out_of_phase(self, written):
        # How far the worst written member is past what a wait tolerates, 0 for none.
        # The write starts centre_us into the synced member's scan, so that is how far
        # out a member may be before it leaves its margin, plus WAIT_SLACK_LINES.
        # __past_budget_us keeps the excess over the budget itself.
        self.__past_budget_us = 0
        members = self.screens
        synced = self.__leader
        if synced is None or synced not in written:
            return 0

        # Local copies and the fold written out: every frame runs this, and a walk each period
        phase_us = self.__phase_us
        residual_us = self.__residual_us
        dither = self.__dither
        line_us = self.__line_us
        target = self.__target_us
        half = target / 2
        centre = self.__centre_us
        slack = self.WAIT_SLACK_LINES
        periods = ((time.ticks_us() - self.__held_stamp) & TICKS_MASK) / target
        member_index = self.__member_index
        indices = (range(len(members)) if written is members
                   else [member_index[screen] for screen in written])

        base_index = member_index[synced]
        base = phase_us[base_index] + periods * (
            residual_us[base_index] + dither[base_index] * line_us[base_index])

        excess = 0
        worst = 0
        for index in indices:
            carried = phase_us[index] + periods * (
                residual_us[index] + dither[index] * line_us[index])
            error = (carried - base) % target
            if error > half:
                error -= target
            past = (error if error > 0 else -error) - centre
            if past > excess:
                excess = past
            # A few rows of clearance, where centre_us exactly would seam the last row
            past += slack * line_us[index]
            if past > worst:
                worst = past

        self.__past_budget_us = excess
        return worst

    def __frame_ticked(self, stats, synced, delay):
        if not self.__holding:
            return

        # The write trails the wait by the centring delay, so the delay comes back out
        stamp = stats.write_start_us
        anchored = -1
        if synced is not None:
            stamp -= delay
            # A stamp is a fall only where the frame waited and the wait did not time out
            if stats.te_wait_us < 2 * self.__target_us:
                anchored = self.__member_index.get(synced, -1)
        self.__tick_hold(stamp & TICKS_MASK, anchored)

    def __tick_hold(self, stamp, anchored):
        # Errors are held against the reference member, which is never dithered, so the
        # whole group warming together costs nothing. A dithered line lands with a
        # one-frame ambiguity, so an unmeasured hold would random-walk apart.
        if not self.__holding:
            return

        elapsed = (stamp - self.__held_stamp) & TICKS_MASK
        self.__held_stamp = stamp
        if elapsed > self.HOLD_PAUSE_MS * 1000 and self.__fresh_hold:
            # A first frame can arrive seconds behind the acquisition, and nothing has
            # drawn yet, so reacquire behind it. Any later pause is ridden out on the bookings.
            if self.__acquire():
                self.__arm_hold()
                self.__fresh_hold = False
            else:
                self.__release_hold(elapsed)
            return
        self.__fresh_hold = False

        # Every list and setting read once per frame
        members = self.screens
        dither = self.__dither
        line_us = self.__line_us
        residual_us = self.__residual_us
        phase_us = self.__phase_us
        anchor_dither = self.__anchor_dither
        periods = elapsed / self.__target_us
        for index in range(len(members)):
            applied = dither[index]
            if applied:
                anchor_dither[index] += applied * line_us[index] * periods
            if index == anchored:
                self.__anchor(index, stamp)
            else:
                phase_us[index] += (residual_us[index] + applied * line_us[index]) * periods

        # Read after the anchor above, which may have rebased the target
        target = self.__target_us
        centre = self.__centre_us
        walk_lines = self.WALK_LINES
        walk_floor = self.WALK_FLOOR_LINES
        anchor_skip = self.__anchor_skip
        fold = self.__fold
        reference = self.__reference_index
        anchor = phase_us[reference]
        drift = residual_us[reference] * periods
        walking = False
        for index in range(len(members)):
            if index == reference:
                continue
            screen = members[index]
            line = line_us[index]
            residual = residual_us[index]
            applied = dither[index]
            # Folded: the anchor wraps each booking at half a period. A positive error
            # is a booking ahead of the reference, closed by shortening the porch, so
            # lines below carries the opposite sign: positive lengthens, negative shortens.
            back, front = screen.__porch
            error = fold(phase_us[index] - anchor)
            # A member further out than centre_us is tearing whatever happens, so the
            # walk runs deep; inside, one line a frame is all the ripple asks for
            if abs(error) <= centre:
                limit = 1
            else:
                limit = walk_lines
                walking = True
                # Advancing stops at the porch floor, so a member with little porch in
                # hand goes the long way round
                if error > 0:
                    room = back - applied - walk_floor
                    long_way = (target - error) / (walk_lines * line)
                    if room < 1 or error / (room * line) > long_way:
                        error -= target
            lines = int(round(((drift - error) / periods - residual) / line))
            lines = limit if lines > limit else (-limit if lines < -limit else lines)
            # Clamped to the floor; skipping the write would stall a walk that has to advance
            floor_lines = walk_floor - back + applied
            if lines < floor_lines:
                lines = floor_lines
            if abs(lines) > 1:
                # Several lines at once is not a rate, so the next anchor is skipped
                anchor_skip[index] = True
            if lines != applied:
                screen.__set_porch(back + lines - applied, front)
                dither[index] = lines

        if walking != self.__walking:
            logging.debug(f"screens: walk {'engaged' if walking else 'done'}, "
                          f"dithers {self.__dither}")
        self.__walking = walking

    def __arm_hold(self):
        # From the last sweep, whose grid and bookings acquisition set
        count = len(self.screens)
        self.__anchor_stamp = [0] * count
        self.__anchor_dither = [0.0] * count
        self.__anchor_skip = [False] * count
        self.__held_stamp = self.__swept_at
        self.__sync_delay_us = self.__centre_us
        self.__fresh_hold = True
        self.__holding = True
        logging.debug(f"screens: writes start {self.__centre_us}us behind the tearing "
                      f"edge, centred in the tightest member's margin")

    def __anchor(self, index, stamp):
        # Replace one member's booking with its measured fall, and learn its rate.
        # Consecutive anchors are whole periods apart, so their gap less the dither spent
        # is a rate reading. A reference reading moves the group's target; any other
        # member's is smoothed into its model and corrected by a porch line past the deadband.
        members = self.screens
        gap = (stamp - self.__anchor_stamp[index]) & TICKS_MASK
        if self.__anchor_stamp[index] and gap < self.HOLD_PAUSE_MS * 1000:
            if self.__anchor_skip[index]:
                self.__anchor_skip[index] = False
            else:
                whole = int(round(gap / self.__target_us))
                if whole > 0:
                    observed = (gap - self.__anchor_dither[index]) / whole - self.__target_us
                    residual = self.__residual_us[index]
                    residual += self.RATE_GAIN * (observed - residual)
                    screen = members[index]
                    if screen is self.__reference:
                        moved = int(round(residual))
                        if moved:
                            self.__rebase(self.__target_us + moved, stamp)
                            residual -= moved
                    else:
                        line = self.__line_us[index]
                        lines = 0
                        if residual > self.TRIM_DEADBAND * line:
                            lines = -self.TRIM_LIMIT_LINES
                        elif residual < -self.TRIM_DEADBAND * line:
                            lines = self.TRIM_LIMIT_LINES
                        if lines and self.__trim_porch(index, lines):
                            residual += lines * line
                            logging.debug(f"screens: trimmed member {index} by "
                                          f"{lines:+} line to porch {screen.__porch}, "
                                          f"{residual:+.1f}us a period left")
                    self.__residual_us[index] = residual
        self.__anchor_stamp[index] = stamp
        self.__anchor_dither[index] = 0.0
        # Resolved nearest the booking, phases being modular: this is what rides out a pause
        booked = self.__phase_us[index]
        raw = (((stamp - self.__grid_at) & TICKS_MASK) + self.__grid_phases[index]) % self.__target_us
        self.__phase_us[index] = booked + self.__fold(raw - booked)

    def __rebase(self, target, stamp):
        # A booking is a phase against the grid, so the grid is re-expressed at stamp
        # and advances at the new period from there: booking minus grid, the error, is
        # the same number before and after
        self.__grid_phases = tuple(
            (((stamp - self.__grid_at) & TICKS_MASK) + phase) % self.__target_us
            for phase in self.__grid_phases)
        self.__grid_at = stamp
        self.__target_us = target

    def __release_hold(self, elapsed):
        for index, screen in enumerate(self.screens):
            applied = self.__dither[index]
            if applied:
                back, front = screen.__porch
                screen.__set_porch(back - applied, front)
                self.__dither[index] = 0
        # Back to the fall itself, only the nominated member coming out clean now
        self.__sync_delay_us = 0
        self.__holding = False
        logging.info("screens: the panels could not be brought back into phase after a "
                     f"{elapsed // 1000}ms pause, so they are no longer being held together")
        if self.__trim_mode == "rotate":
            # Rotating is only free while the members fall together
            self.__trim_mode = "probe"
            self.__trim_frames = 0

    def __tick_trim(self, synced=None):
        # A calibration goes stale as the panels warm. rotate moves the wait target to the
        # next member each frame, so every booking stays within a few periods of a
        # measurement; probe re-measures one member every TRIM_FRAMES, stalling that frame.
        if not self.__trim_mode:
            return

        members = self.screens
        if self.__trim_mode == "rotate":
            # Only a frame that waited on the leader measured it. Every member takes its
            # turn, walking or not; a skipped one drifts on a stale rate, seen as a tear that walks.
            if synced is self.__leader:
                self.__trim_at = (self.__member_index[self.__leader] + 1) % len(members)
                self.__leader = members[self.__trim_at]
            return

        self.__trim_frames += 1
        if self.__trim_frames <= self.TRIM_FRAMES:
            return

        self.__trim_frames = 0
        index = self.__trim_at
        screen = members[index]
        self.__trim_at = (index + 1) % len(members)
        falls, _ = self.__solo_capture(screen, 4, 200)
        if len(falls) > 1:
            measured = ((falls[-1] - falls[0]) & TICKS_MASK) / (len(falls) - 1)
            # Each captured period carries a dithered porch line whole
            self.__correct(screen, measured - self.__dither[index] * self.__line_us[index])

    def __correct(self, screen, measured):
        # Move one member a line closer to the held period. A held reference is not
        # moved: the target follows it and the grid is rebased, so the bookings carry over.
        if not measured or screen not in self.screens:
            return

        index = self.screens.index(screen)
        line = self.__line_us[index]
        if self.__holding and screen is self.__reference:
            # The target stays an int, the grid arithmetic being exact only in whole microseconds
            target = int(round(measured))
            if target != self.__target_us:
                self.__rebase(target, self.__held_stamp)
            self.__residual_us[index] = measured - target
            return
        lines = int(round((self.__target_us - measured) / line))
        limit = self.TRIM_LIMIT_LINES
        lines = limit if lines > limit else (-limit if lines < -limit else lines)
        if lines:
            lines = self.__trim_porch(index, lines)
            if lines:
                logging.debug(f"screens: trimmed member {index} by "
                              f"{lines:+} line to porch {screen.__porch}, "
                              f"{measured:.0f}us against {self.__target_us:.0f}")
        if self.__holding:
            self.__residual_us[index] = measured + lines * line - self.__target_us

    def __trim_porch(self, index, lines):
        # Returns the lines applied, 0 where the floor refused. A gap spanning a porch
        # move is not a rate, so the member's next anchor is skipped.
        screen = self.screens[index]
        back, front = screen.__porch
        if back + lines < 1:
            return 0

        screen.__set_porch(back + lines, front)
        self.__corrections += 1
        self.__anchor_skip[index] = True
        return lines

    def __period_of(self, screen, settle=False):
        # settle discards the first reading, which a panel fresh from bringup needs
        screen.__command(screen.CONTROLLER.REG_TEON, b"\x00")
        if settle:
            screen.__display.te_probe(self.PROBE_MS)
        period = screen.__display.te_probe(self.PROBE_MS)[0]
        screen.__command(screen.CONTROLLER.REG_TEOFF)
        return period

    def __unaligned(self, required, why):
        if required:
            raise ValueError(why)

        logging.info(f"screens: this group is not holding its panels in phase. {why}")

    def is_aligned(self):
        """Whether the members' refreshes are being held together, not whether that was asked."""
        if self.__subset_of is not None:
            return self.__subset_of.is_aligned()
        return self.__holding

    def subset(self, *screens, leader=None, reveal_together=False):
        """A group over some of these members, sharing this one's display; cheap enough to make per frame."""
        if not screens:
            raise ValueError("a subset needs at least one screen")

        return ScreenGroup(*screens, leader=leader, parent=self.__subset_of or self,
                           reveal_together=reveal_together)
