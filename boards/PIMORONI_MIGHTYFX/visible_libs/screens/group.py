# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Several of a port's screens driven as one, sharing a frame. A group calibrates its
# members onto one refresh rate, brings their scans together, and holds them there
# from the frames it already writes, so the panels change as one.

import logging
import time

from .base import ScreenBase, __tightest_margin

# time.ticks_us() wraps at 2**30 where the C module's stamps wrap at 2**32, and
# their low bits agree, so a group's hold reduces every stamp it keeps to 30 bits
# and takes every difference there. That lets a frame's own stamp and a plain
# clock reading serve the same arithmetic, and holds to about seventeen minutes.
TICKS_MASK = 0x3FFFFFFF


class ScreenGroup(ScreenBase):
    """Several of a port's screens driven as one, sharing a frame."""

    # The first probe after bringup reads long and settles within a second, so each
    # panel's first reading is discarded, as ScreenPair does. 300ms is about 13
    # periods: at 100 a single miscounted edge moved a trim by three porch lines,
    # which is more than the spread the trim exists to null.
    PROBE_MS = 300
    SETTLE_MS = 100

    # Of the fastest member's margin, what the hold may spend. ScreenPair holds its
    # dither to the same fraction and slips at 0.6.
    DITHER_FRACTION = 0.4

    # Frames between one probe-mode measurement and the next. 30 is about two
    # seconds at a group's frame rate, so six members come round in twelve.
    TRIM_FRAMES = 30

    # How far one gap between a member's anchors moves its modelled rate. The
    # panels' rates wander around 10us a period over seconds, which no calibration
    # can pin, so the model leans on the newest reading; the reading is good to
    # about 1us a period, the TE jitter over the dozen periods between anchors.
    RATE_GAIN = 0.5

    # Of a line, how far a member's modelled rate drifts before a whole porch line
    # corrects it. Half a line is the rounding point, but the 1.54's half-line is
    # 27us where its rate wanders about 10, so rounding fires corrections on noise
    # that a deadband this wide does not, each one a real rate step.
    TRIM_DEADBAND = 0.75

    # The most one correction moves a member. A stale calibration is worth whole
    # lines, and applying them at once is a visible step where a line at a time is
    # inside the sawtooth the hold carries anyway.
    TRIM_LIMIT_LINES = 1

    # Porch lines an acquisition's excursion rounds run at, and the depth the
    # hold's dither reaches while walking a straggler back in behind flowing
    # frames. Both move a member whichever way is nearer, since neither writes to
    # the member while it travels: an acquisition runs between frames, and a
    # walking member is held out of the write until it fits. Lengthening is
    # measured usable to 56 blanking lines, and shortening stops at the porch
    # floor, which the walk clamps to rather than overshooting.
    EXCURSION_LINES = 8
    WALK_LINES = 24

    # The shortest back porch a walk may leave. Blanking is the porch, so it is
    # also the tearing pulse: with the 12-line front porch this holds the pulse
    # above a millisecond on both panel types, clear of te_short_waits' 700us
    # and of the controller's own minimum, so a walking member is still readable
    # as the wait target and keeps taking its turn at being measured.
    WALK_FLOOR_LINES = 8

    # The longest a frame waits for the members to come together before it goes
    # out regardless. update() presents on every member before it returns, so a
    # straggler is waited for rather than dropped, and past this the frame is
    # written and tears on whoever is still out: one spoiled frame beats a
    # stalled wall. A pause long enough to need the whole budget is a pause the
    # caller has already spent seconds on, so the wait costs nothing it notices.
    WALK_WAIT_MS = 600

    # Scan lines of clearance a frame is held for beyond coming into the window.
    # At centre_us exactly the following scan overtakes the write on the panel's
    # last row, so a member released there seams at the edge and the seam walks
    # off as the hold closes the rest: the reserve keeps that crossing off the
    # glass instead. Two lines, since a dithered porch line lands with a
    # one-frame ambiguity and a reserve under one would ask for what the
    # mechanism cannot resolve.
    WAIT_SLACK_LINES = 2

    # How far a capture's own two falls may span from a period before the phase it
    # gives is counted as suspect. Eight lines sits between the two measured cases,
    # 14us of spread across 25 settled captures and a blanking's 1,480us on the one
    # that missed, so neither the panel's jitter nor a residual reaches it.
    CAPTURE_TOLERANCE_LINES = 8

    # Sweeps allowed to bring the phases together before the group gives up. It
    # converges in two and the third is noise, so more buys nothing.
    ACQUIRE_TRIES = 3

    # Past this gap between frames a rate reading is not trusted, the panels'
    # rates wandering while nothing measures them, and a hold not yet fed its
    # first frame reacquires outright. The bookings themselves survive any pause:
    # an anchor resolves its measurement nearest the booking and phases are
    # modular, so however far extrapolation drifted, the members walk back in.
    HOLD_PAUSE_MS = 1000

    # Past this gap a resume sweeps the members' phases before walking them
    # together, an extrapolation over it being worth less than a measurement:
    # a 1s prediction spends 42% of the 280's margin and overruns the 154's,
    # and a walk aimed from a stale booking arrives somewhere else.
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

        # A subset is a member set over its parent's display, so it claims no
        # members, builds no display, and leaves ownership where it is. subset()
        # is the friendly way in; the membership check lives here so neither
        # route can name a screen the parent does not hold.
        if parent is not None:
            for screen in screens:
                if screen not in parent.screens:
                    raise ValueError(f"{screen} is not a member of this group, so it cannot be in a subset of it")
            # A subset inherits its parent's nomination, since alignment and the
            # panel state stay the parent's; leader=False declines the wait for this
            # set alone. A nominated member outside the set is resolved per write.
            nominated = parent.__leader if leader is None else leader
            if nominated is False:
                nominated = None
            # Placement is the parent's too, a subset writing into the parent's
            # display and so carrying the same one stream
            super().__init__(port, parent.__display, parent.width, parent.height,
                             parent.__bitdepth, parent.backlight, nominated is not None,
                             nominated is not None, parent.__reserve,
                             members=tuple(screens), leader=nominated,
                             rotation=parent.rotation if rotation is None else rotation,
                             mirror=parent.mirror if mirror is None else mirror)
            self.__subset_of = parent
            self.__subset_displays = tuple(screen.__display for screen in screens)
            # These answer through a subset as the parent would; the hold is
            # asked live instead, is_aligned() forwarding to the parent, since
            # its members are held whether or not this set writes them.
            self.__reference = parent.__reference
            self.__acquired_us = parent.__acquired_us
            self.__trim_mode = parent.__trim_mode
            return

        for screen in screens:
            if screen.__group is not None:
                raise ValueError("a screen belongs to one group at a time, and one of these is already in another. Take a subset of the group it is in, or build a single group over every panel that shares a frame.")

        # One member's TE, not all of them: a hub's panels scan independently, so no
        # edge is safe for every one and the nominated panel comes out clean while
        # the rest tear. Naming a member is a request and refuses if it cannot be
        # met; None takes the first that can, and False declines the wait outright.
        nominated = None
        if leader is not False:
            shared = [screen for screen in screens if screen.__shared_te]
            if leader is not None:
                if leader not in screens:
                    raise ValueError(f"{leader} is not a member of this group, so it cannot be the one its frames wait on")
                if not leader.__shared_te:
                    raise ValueError(f"{leader} does not read its tearing-effect signal from the line this group's frames read. Build every member with te set to the DC line they share, which needs the diode fitted to each breakout.")
                nominated = leader
            elif shared:
                nominated = shared[0]
            else:
                logging.info("screens: this group's panels carry no shared tearing-effect signal, so its frames will not wait and every panel may tear. Build the members with te set to the DC line they share to nominate one.")

        first = screens[0]
        display = port.__bus.broadcast(*[screen.__display for screen in screens])

        # A group places its own frames and does not read its members', so an unnamed
        # rotation is upright rather than the first member's. Saying so where they
        # differ is what stops a member's setting going quietly unused.
        rotation = 0 if rotation is None else rotation
        mirror = False if mirror is None else bool(mirror)
        if any(screen.rotation != rotation or screen.mirror != mirror for screen in screens):
            logging.info(f"screens: this group places its own frames, at rotation {rotation}"
                         f"{' and mirrored' if mirror else ''}, so its members' own placement is"
                         f" not used. Create the group with the placement all of its panels want,"
                         f" or update a panel on its own to get the one it was created with.")

        # The backlight is the first member's, since screens on a port share the one
        # PWM.
        super().__init__(port, display, first.width, first.height, first.__bitdepth,
                         first.backlight, nominated is not None, nominated is not None,
                         first.__reserve, members=tuple(screens), leader=nominated,
                         rotation=rotation, mirror=mirror)

        # Position by member, so a frame's bookkeeping never scans the tuple
        self.__member_index = {screen: index for index, screen in enumerate(screens)}
        self.__reference_index = 0
        # Three states, not two. Nulling the members' rates stops them drifting apart
        # quickly; an acquisition brings their scans together at one instant; only a
        # hold keeps them there. The residual rate spread separates them again at 30
        # to 90us a period, which is past the aim inside two of them, so an
        # acquisition on its own is worth a tenth of a second.
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
        # Frames written with a member past its own tearing budget, and how far
        # the worst of them was past it. A tear is brief and only shows where the
        # content changed, so this is what a diagnostic reads instead of an eye.
        self.__exposed_frames = 0
        self.__worst_exposure_us = 0
        self.__past_budget_us = 0
        # Captures whose own two falls did not span a plausible period, and the
        # worst miss. A phase comes from the last fall alone, so nothing else
        # notices a spurious edge putting a member's booking milliseconds out.
        self.__suspect_sweeps = 0
        self.__worst_sweep_error_us = 0
        # The hold's state, per member: the sub-line rate error calibration left,
        # the phase error that rate has built since acquisition, and the porch line
        # currently dithered on. Armed by a successful acquisition.
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
        # A lone member is in phase with itself, so there is nothing to calibrate and a
        # required alignment is already met. It reports unaligned, holding no period.
        if align is not False and len(screens) > 1:
            if nominated is None:
                # The leader block above already said why there is no signal to hold
                # these panels by, so only a required alignment speaks again.
                if align is True:
                    raise ValueError("align holds a group's panels in phase by their tearing-effect signal, so it needs every member built with te set to the DC line they share")
            else:
                self.__calibrate(align is True)

        # A trim holds members to the period calibration settled on, so a group with
        # no settled period has nothing to correct toward and does not trim.
        #
        # None rotates only once the members are held in phase, which is what makes
        # moving the wait target free: any member serves when they all fall together.
        # Held to one rate but not one phase, rotating moves which panel comes out
        # clean and jumps every other panel's tear with it, seen on the glass. So
        # until phase is held, None is off and probe is the way to ask for freshness.
        if trim not in (None, True, False, "rotate", "probe"):
            raise ValueError(f"{trim} is not a valid trim. Expected None, False, 'rotate', or 'probe'.")

        if not self.__target_us:
            if trim not in (None, False):
                logging.info("screens: this group holds no period for its members, so there is nothing for a trim to correct toward")
            self.__trim_mode = False
        elif trim in (None, True):
            self.__trim_mode = "rotate" if self.__holding else False
        else:
            self.__trim_mode = trim

        # Last, so a construction that raised claims nothing: a member left holding a
        # group that does not exist refuses every later attempt to group it.
        for screen in screens:
            screen.__group = self

    def __calibrate(self, required):
        """Probe every member's period, trim each toward the slowest, and price it.

        The reference is the slowest member, so every trim lengthens a porch, which
        is the direction that also adds margin to the panel with least of it. One
        porch line is one line time, measured, so the quantum needs no probing: what
        is probed is each member's own period, which no table gives.

        required refuses where the members will not hold; otherwise an unmet request
        says why and the group falls back to the member leader names, which is a
        legitimate outcome and not a failure.
        """
        members = self.screens
        logging.info(f"> Calibrating {len(members)} screens, about"
                     f" {len(members) * self.PROBE_MS * 2 // 1000 + 1} seconds ...")

        periods = []
        for screen in members:
            if screen.__leader is None:
                self.__unaligned(required, f"{screen} carries no tearing-effect signal a group can read, so build every member with te set to the DC line they share")
                return
            period = self.__period_of(screen, settle=True)
            if not period:
                self.__unaligned(required, f"{screen} returned no period, so its tearing-effect signal is not reaching the shared line")
                return
            periods.append(period)

        # Each panel's line time is its own and fixed by its oscillator; the porch
        # moves how many of them a refresh spends, not how long one lasts.
        line_us = [period / screen.__line_slots for period, screen in zip(periods, members)]
        slowest = periods.index(max(periods))
        frame_us = self.__display.wire_window_us()
        trims = [int(round((periods[slowest] - period) / line))
                 for period, line in zip(periods, line_us)]

        tightest, margins_us, quanta = __tightest_margin(members, trims, line_us,
                                                         [frame_us] * len(members))
        # Kept per member as a diagnostic: which panel is the constraint, and
        # by how much. Nothing on the frame path reads it.
        self.__margins = margins_us
        margin_us = margins_us[tightest]
        reserve = self.DITHER_FRACTION * margin_us

        if quanta + reserve > margin_us or margin_us <= 0:
            self.__unaligned(required, f"{members[tightest]} keeps only {margin_us:.0f}us of tearing margin, and holding a group costs {quanta:.0f}us of granularity plus a reserve. Lengthen every member's porch, or drop the rate a step")
            return

        # Past the refusal, so nothing above has moved a panel: a group that declines
        # to align leaves every porch where bringup left it and names no reference.
        self.__reference = members[slowest]
        self.__reference_index = slowest
        for screen, trim in zip(members, trims):
            if trim:
                back, front = screen.__porch
                screen.__set_porch(back + trim, front)

        # One verify pass. A trim is priced from a single reading, and a reading that
        # miscounts an edge lands whole porch lines out; measuring the trimmed panels
        # and correcting the residual costs one probe each and leaves the static trim
        # actually static, with only a fraction of a line for the hold to carry.
        time.sleep_ms(self.SETTLE_MS)
        held = [self.__period_of(screen) for screen in members]
        if all(held):
            target = max(held)
            for index, screen in enumerate(members):
                correction = int(round((target - held[index]) / line_us[index]))
                if correction:
                    back, front = screen.__porch
                    screen.__set_porch(back + correction, front)
                # What the member runs at against the target, under half a line
                # either way: the rate error the hold's accumulator integrates.
                self.__residual_us[index] = held[index] + correction * line_us[index] - target
            logging.debug(f"screens: verified at {held}, spread {max(held) - min(held)}us")
            self.__target_us = target

        self.__line_us = tuple(line_us)

        # What a phase spread has to fit inside. A member out of phase spends that
        # much of its own tearing margin, so the aim is the tightest member's less
        # the reserve the hold keeps, rather than a figure picked to suit a result.
        self.__aim_us = (1.0 - self.DITHER_FRACTION) * margin_us

        # Half the tightest member's margin, which is where a held group starts its
        # writes: at the fall itself the synced member's own budget is whole but a
        # member scanning later has none, and the constellation straddles that
        # edge, so the write floats in the middle of the window instead.
        self.__centre_us = int(margin_us / 2)

        # One rate stops them drifting apart; acquisition brings them together, and
        # the hold is what keeps them there, the residual rate spread passing the
        # aim inside half a second otherwise.
        if self.__target_us and self.__acquire():
            self.__arm_hold()
        logging.info(f"screens: aligned on {self.__reference}, trims {trims} porch lines,"
                     f" {margin_us:.0f}us of margin at the tightest member")

    def __phases(self):
        """Every member's phase at one instant, swept one at a time behind TEON.

        A shared line carries one panel's signal at a time, so the captures do not
        share a moment and ageing is what brings them onto one: each member's last
        fall is carried forward by the period the group holds them all to. The
        reference instant is the last capture's own end, so every member is aged
        forward and none backward.

        Returns the time since each member last fell, or None where one went silent.
        """
        # Two falls, which is the fewest that names one: the sweep serialises, so
        # every extra fall ages the members swept before it by another period and the
        # ageing error is what limits the aim. Four falls tripled the sweep and made
        # the acquisition worse.
        rows = []
        for index, screen in enumerate(self.screens):
            falls, finished = self.__solo_capture(screen, 2, 200)
            if not falls:
                return None
            rows.append((falls[-1], finished))
            self.__check_span(index, falls)

        # Aged by the period the group holds them all to, not by one read from this
        # capture: a period from two adjacent falls carries the panel's own jitter,
        # where the group's is averaged over a settled probe. The error left is the
        # residual rate spread times the periods aged, so a tight trim is what makes
        # a close aim possible.
        reference = rows[-1][1]
        self.__swept_at = reference & TICKS_MASK
        return [((reference - fall) & 0xFFFFFFFF) % self.__target_us
                for fall, _ in rows]

    def __acquire(self):
        """Bring the members' scans together, which one rate alone does not do.

        A member is moved by running its porch long for a while: a period stretched
        by EXCURSION_LINES for k of them delays that member by k times the stretch,
        and the porch goes back afterwards. Only ever lengthened, so a member is
        always delayed into place and its margin grows while it travels rather than
        shrinking, which the 1.54 has no room for.

        Sweeping serialises behind TEON and the members drift while it runs, so the
        aim carries the sweep's own ageing error. That is what the retries are for,
        and a group still past the aim when they run out is armed from its final
        sweep regardless: any measured sweep is a working grid, and the hold walks
        the remainder in at about a line time a frame, where refusing would leave
        every panel but one tearing indefinitely. Only a member going silent fails.
        """
        # One more check than excursion rounds: the last round's outcome has to be
        # measured, or a converged group is judged on the state before it.
        for attempt in range(self.ACQUIRE_TRIES + 1):
            errors, target = self.__sweep_errors()
            if errors is None:
                logging.info("screens: a member went silent during the phase sweep, so the group is not in phase")
                return False

            spread = max(errors) - min(errors)
            settled = spread <= self.__aim_us
            if settled or attempt == self.ACQUIRE_TRIES:
                self.__acquired_us = spread
                self.__seed_grid(errors, target)
                if settled:
                    logging.info(f"screens: members brought into phase, spread {spread}us"
                                 f" after {attempt} excursions. It decays at the residual"
                                 f" rate spread until a hold carries it")
                else:
                    logging.info(f"screens: the members are still {int(spread)}us apart"
                                 f" against a {self.__aim_us:.0f}us aim, so the hold"
                                 f" walks the rest in, about a line time a frame")
                return True

            # Delay each member until its fall meets the reference's. A phase is the
            # time since that member last fell, so one further through its frame than
            # the reference has to wait the difference out.
            self.__excurse(errors)

    def __sweep_errors(self):
        """Every member's folded phase error against the reference, from one sweep.

        Folded, since phases are modular: a member one step behind the reference
        reads a whole period ahead of it, and a plain difference calls a
        converged group maximally spread. Returns (errors, the reference's
        phase), or (None, None) where a member went silent.
        """
        phases = self.__phases()
        if phases is None:
            return None, None

        target = phases[self.__reference_index]
        return [self.__fold(phase - target) for phase in phases], target

    def __seed_grid(self, errors, target):
        """Rebuild the grid at the last sweep's instant, booking what it measured.

        The grid the hold measures against is common: every member's ideal falls
        are the reference's, and the bookings carry the offsets the sweep
        measured, so the hold walks every member onto the grid rather than
        holding it where it landed.
        """
        self.__grid_at = self.__swept_at
        self.__grid_phases = tuple([target] * len(self.screens))
        self.__phase_us = [-error for error in errors]

    def __excurse(self, errors):
        """One concurrent excursion round cancelling the given phase errors.

        errors carry the sweep's sign, positive being a member ahead of the
        reference, cancelled by delaying it that long: its porch runs long for
        whole periods, EXCURSION_LINES at a time, and goes back after. Each
        member takes whichever direction is nearer, which halves the worst case
        against delaying alone. Shortening a porch spends tearing margin while
        it runs, and that costs nothing here: no frame is written during an
        excursion, so there is no write for the margin to protect. Every
        excursion runs at once and each is lifted at its own count, so a round
        costs the longest one and not their sum.
        """
        members = self.screens
        plans = []
        for index in range(len(members)):
            stretch = self.EXCURSION_LINES * self.__line_us[index]
            plans.append(int(round(errors[index] / stretch)))

        logging.debug(f"screens: errors {[int(e) for e in errors]},"
                      f" excursions {plans} periods")

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
        """One member's TE falls, it alone asserting on the shared line."""
        screen.__command(screen.CONTROLLER.REG_TEON, b"\x00")
        falls, finished = screen.__display.te_capture(edges, timeout_ms)
        screen.__command(screen.CONTROLLER.REG_TEOFF)
        return falls, finished

    def __check_span(self, index, falls):
        """Count a capture whose own two falls do not span a plausible period.

        A phase is taken from the last fall alone, so a fall that lands on the wrong
        edge reads as a real one and books that member wherever it fell. The pair
        prices itself, and the two cases are far apart: 25 captures on a settled 2.80
        spanned within 14us of each other and one came in 1,480us short, a blanking.
        Counted only, the sweep still using what it measured.
        """
        if len(falls) < 2 or not self.__target_us:
            return

        spanned = (falls[-1] - falls[0]) & TICKS_MASK
        error = spanned - self.__target_us
        if abs(error) > self.CAPTURE_TOLERANCE_LINES * self.__line_us[index]:
            self.__suspect_sweeps += 1
            if abs(error) > abs(self.__worst_sweep_error_us):
                self.__worst_sweep_error_us = error
            logging.debug(f"screens: a capture spanned {spanned}us against a"
                          f" {self.__target_us}us period, so the phase it gives"
                          f" may not be this member's")

    def __fold(self, error):
        """A modular phase difference brought onto +-half a period."""
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
        """Wait for the members to come together before a frame goes out.

        Nothing is written while this runs, so the group presents in one piece
        rather than in waves. Over a frame or two of streaming the wait needs no
        measurement, a tick asking only for an elapsed time and the rates the
        hold already carries; past SWEEP_PAUSE_MS it sweeps first, an
        extrapolation that far being worth less than what the panels say. Past
        WALK_WAIT_MS the frame goes out and tears on whoever is still out,
        update() being a promise that the group has presented by the time it
        returns.
        """
        if self.__out_of_phase(written):
            if ((time.ticks_us() - self.__held_stamp) & TICKS_MASK) > self.SWEEP_PAUSE_MS * 1000:
                self.__reseed()

            deadline = time.ticks_add(time.ticks_ms(), self.WALK_WAIT_MS)
            nap = int(self.__target_us / 1000) + 1
            waited = 0
            while self.__out_of_phase(written):
                if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                    logging.info("screens: some panels are still out of phase, so this frame goes out and tears on them rather than holding the group up any longer")
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
        """Replace the bookings with a fresh sweep, so a walk aims at the truth.

        Every member drifts by its own residual while nothing measures it, which
        after a few seconds is milliseconds apiece and independent between them,
        so re-anchoring one member fixes only that one. The grid is rebuilt
        around the sweep's own instant and the bookings carry the offsets it
        measured, leaving the hold's dither to close what is left. A silent
        member keeps the bookings, the walk then being the only recovery left.
        """
        errors, target = self.__sweep_errors()
        if errors is None:
            logging.debug("screens: a member did not answer the sweep, so the walk keeps its bookings")
            return

        self.__seed_grid(errors, target)
        self.__held_stamp = self.__swept_at
        logging.debug(f"screens: swept the members after a pause, spread"
                      f" {int(max(errors) - min(errors))}us for the walk to close")

    def __out_of_phase(self, written):
        """How far the worst written member is past what a wait tolerates, 0 for none.

        The write starts centre_us into the synced member's scan, so that is how
        far out of phase a member may be before it leaves its own tearing
        margin, and WAIT_SLACK_LINES sits on top of that. Bookings are carried to
        this instant, so the first frame after a pause is judged on where the
        panels are and not where they were. __past_budget_us is left holding the
        worst excess over the budget itself, which is what a frame written now
        would risk on the glass.
        """
        self.__past_budget_us = 0
        members = self.screens
        synced = self.__leader
        if synced is None or synced not in written:
            return 0

        # Held against a local copy of each booking, and the fold written out: every
        # written frame runs this, and a walk runs it again each period it waits.
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

        budget = 0
        worst = 0
        for index in indices:
            carried = phase_us[index] + periods * (
                residual_us[index] + dither[index] * line_us[index])
            error = (carried - base) % target
            if error > half:
                error -= target
            past = (error if error > 0 else -error) - centre
            if past > budget:
                budget = past
            # The reserve sits inside the window rather than outside it. A frame
            # released at centre_us exactly puts the following scan's overtake on the
            # panel's last row, so the wait asks for a few rows of clearance instead
            # of allowing a few rows of seam.
            past += slack * line_us[index]
            if past > worst:
                worst = past

        self.__past_budget_us = budget
        return worst

    def __frame_ticked(self, stats, synced, delay):
        """Advance the hold from a written frame's own stamp."""
        if not self.__holding:
            return

        # The write trails the wait by the group's centring delay and the stamp
        # moves with it, so the delay comes back out: the clock and the grid are
        # both fall-referenced, whichever path the frame took.
        stamp = stats.write_start_us
        anchored = -1
        if synced is not None:
            stamp -= delay
            # A stamp is a fall only where the frame waited and the wait did not
            # time out, a timeout releasing at whatever phase its budget expired.
            if stats.te_wait_us < 2 * self.__target_us:
                anchored = self.__member_index.get(synced, -1)
        self.__tick_hold(stamp & TICKS_MASK, anchored)

    def __tick_hold(self, stamp, anchored):
        """Walk each member onto the group's grid and hold it, a porch line at a time.

        Between frames each member's booked phase advances by its modelled rate
        error, but the frame's own write stamp is the synced member's TE fall, so
        that member's booking is replaced by a measurement for free and the trim's
        rotation carries the measurement round the group. The model alone cannot
        serve: a dithered porch line lands with a one-frame ambiguity, so each
        toggle mis-books up to a line and an unmeasured hold random-walks apart.

        Errors are held against the reference member, which is never dithered, so
        the whole group warming together costs nothing. Each other member takes
        the dither, -1, 0 or +1 porch lines, predicted to leave its error nearest
        zero, which centres the ripple instead of walking one side of it.
        """
        if not self.__holding:
            return

        elapsed = (stamp - self.__held_stamp) & TICKS_MASK
        self.__held_stamp = stamp
        if elapsed > self.HOLD_PAUSE_MS * 1000 and self.__fresh_hold:
            # A group's first frame can arrive seconds behind its acquisition,
            # another group's construction being that long, and nothing has drawn
            # yet so the backlight is dark: reacquire by sweeping behind the
            # frame. Released only when the reacquisition itself fails. Any later
            # pause is ridden out instead, the bookings extrapolating across it
            # and the dither's deep end walking the stragglers back in.
            if self.__acquire():
                self.__arm_hold()
                self.__fresh_hold = False
            else:
                self.__release_hold(elapsed)
            return
        self.__fresh_hold = False

        # Per frame, so every list and setting is read once: an attribute or an
        # index scan per member per frame is what a hold's latency is made of.
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
            # Folded: the whole group walks the grid as the panels warm, and the
            # anchor wraps each member's booking at half a period, so two members
            # either side of a wrap differ by a period while their scans do not.
            back, front = screen.__porch
            error = fold(phase_us[index] - anchor)
            # The write starts centre_us into the synced member's scan, so a
            # member further out than that has it outside its own budget and is
            # tearing whatever happens: the walk runs deep, its margin no longer
            # being worth protecting. Inside, one line a frame is all the ripple
            # asks for.
            if abs(error) <= centre:
                limit = 1
            else:
                limit = walk_lines
                walking = True
                # Advancing gives porch back and stops at the walk's floor, where
                # delaying has the whole depth to spend. A member with little
                # porch in hand therefore goes the long way round, which on these
                # panels closes a half-period error sooner than crawling.
                if error > 0:
                    room = back - applied - walk_floor
                    long_way = (target - error) / (walk_lines * line)
                    if room < 1 or error / (room * line) > long_way:
                        error -= target
            lines = int(round(((drift - error) / periods - residual) / line))
            lines = limit if lines > limit else (-limit if lines < -limit else lines)
            # Shortening stops at the walk's porch floor, which keeps this
            # member's tearing pulse readable while it travels. Clamp to it
            # rather than skipping the write, which would stall a walk that has
            # to advance.
            floor_lines = walk_floor - back + applied
            if lines < floor_lines:
                lines = floor_lines
            if abs(lines) > 1:
                # A porch moving whole excursions lands with the same one-frame
                # ambiguity a line does, several lines at a time: not a rate.
                anchor_skip[index] = True
            if lines != applied:
                screen.__set_porch(back + lines - applied, front)
                dither[index] = lines

        if walking != self.__walking:
            logging.debug(f"screens: walk {'engaged' if walking else 'done'},"
                          f" dithers {self.__dither}")
        self.__walking = walking

    def __arm_hold(self):
        """Start holding from the last sweep, whose grid and bookings acquisition set."""
        count = len(self.screens)
        self.__anchor_stamp = [0] * count
        self.__anchor_dither = [0.0] * count
        self.__anchor_skip = [False] * count
        self.__held_stamp = self.__swept_at
        self.__sync_delay_us = self.__centre_us
        self.__fresh_hold = True
        self.__holding = True
        logging.debug(f"screens: writes start {self.__centre_us}us behind the tearing"
                      f" edge, centred in the tightest member's margin")

    def __anchor(self, index, stamp):
        """Replace one member's booking with its measured fall, and learn its rate.

        Consecutive anchors of one member are whole periods apart, so their gap,
        less the dither lines the hold spent between them, is also a rate reading.
        A reference reading moves the group's target, so the whole fleet warming
        together is one number tracking; any other member's is smoothed into its
        model, corrected by a whole porch line where the model has drifted past
        the deadband. A gap spanning a correction is not a rate, the porch moving
        at a boundary only the panel knows, so the reading after one is discarded.
        """
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
                            logging.debug(f"screens: trimmed member {index} by"
                                          f" {lines:+} line to porch {screen.__porch},"
                                          f" {residual:+.1f}us a period left")
                    self.__residual_us[index] = residual
        self.__anchor_stamp[index] = stamp
        self.__anchor_dither[index] = 0.0
        # Resolved nearest the booking: phases are modular, so a measurement is
        # only defined to within whole periods and the booking names which one.
        # That is what lets the bookings ride out a pause of any length.
        booked = self.__phase_us[index]
        raw = (((stamp - self.__grid_at) & TICKS_MASK) + self.__grid_phases[index]) % self.__target_us
        self.__phase_us[index] = booked + self.__fold(raw - booked)

    def __rebase(self, target, stamp):
        """Move the grid to a new period without disturbing the bookings.

        The grid's ideal falls keep their phase at the given instant and advance
        at the new period from it, so every booked error carries over unchanged.
        """
        self.__grid_phases = tuple(
            (((stamp - self.__grid_at) & TICKS_MASK) + phase) % self.__target_us
            for phase in self.__grid_phases)
        self.__grid_at = stamp
        self.__target_us = target

    def __release_hold(self, elapsed):
        """Stop holding the members' phases: they could not be brought back."""
        for index, screen in enumerate(self.screens):
            applied = self.__dither[index]
            if applied:
                back, front = screen.__porch
                screen.__set_porch(back - applied, front)
                self.__dither[index] = 0
        # Back to the fall itself: with the constellation loose only the nominated
        # member comes out clean, and the fall is its own tuned phase.
        self.__sync_delay_us = 0
        self.__holding = False
        logging.info(f"screens: the panels could not be brought back into phase after a {elapsed // 1000}ms pause, so they are no longer being held together")
        if self.__trim_mode == "rotate":
            # Moving the wait target is only free while the members fall together,
            # so freshness falls back to measuring one panel between frames.
            self.__trim_mode = "probe"
            self.__trim_frames = 0

    def __tick_trim(self, synced=None):
        """Keep the members' rate models current between frames.

        A calibration goes stale as the panels warm, and a stale period costs an
        order of magnitude in what a prediction is worth, measured 2026-08-08.
        rotate moves the wait target to the next member each frame: each frame's
        stamp anchors the member it waited on, so every booking stays within a few
        periods of a measurement and nothing is probed. probe re-measures one
        member every TRIM_FRAMES through a capture, stalling the frame it lands on.
        """
        if not self.__trim_mode:
            return

        members = self.screens
        if self.__trim_mode == "rotate":
            # A frame that waited on someone else, or not at all, measured nothing,
            # so the target stays for the next frame to anchor.
            # Every member takes its turn, walking or not: the anchor is the only
            # thing that measures a member, so skipping one leaves it drifting on
            # a stale rate, which shows as a tear that walks. What a deep walk
            # needs is a porch floor that keeps its pulse readable, not a turn
            # missed.
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
        """Move one member a line closer to the period the group holds.

        A held reference is not moved: the group's target follows it instead, so
        the whole fleet warming together is one number tracking and not several
        porches fighting it, and the grid is re-based so the bookings carry over.
        The reading also refreshes the rate the hold extrapolates with, whole
        lines or not: a stale one costs an order of magnitude, measured 2026-08-08.
        """
        if not measured or screen not in self.screens:
            return

        index = self.screens.index(screen)
        line = self.__line_us[index]
        if self.__holding and screen is self.__reference:
            # The target stays an int: the grid arithmetic is exact only while a
            # stamp's modulo is taken against whole microseconds.
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
                logging.debug(f"screens: trimmed member {index} by"
                              f" {lines:+} line to porch {screen.__porch},"
                              f" {measured:.0f}us against {self.__target_us:.0f}")
        if self.__holding:
            self.__residual_us[index] = measured + lines * line - self.__target_us

    def __trim_porch(self, index, lines):
        """Move one member's porch by whole lines, where its floor allows.

        Counts the correction and skips the member's next anchor, a gap spanning
        a porch move not being a rate. Returns the lines actually applied, so a
        refused move corrects nothing. The caller owns the residual it is
        correcting, the two trims deriving theirs differently.
        """
        screen = self.screens[index]
        back, front = screen.__porch
        if back + lines < 1:
            return 0

        screen.__set_porch(back + lines, front)
        self.__corrections += 1
        self.__anchor_skip[index] = True
        return lines

    @property
    def __trim(self):
        """How the group keeps its members' periods current: rotate, probe or False."""
        return self.__trim_mode

    @__trim.setter
    def __trim(self, value):
        if value not in (None, True, False, "rotate", "probe"):
            raise ValueError(f"{value} is not a valid trim. Expected None, False, 'rotate', or 'probe'.")

        if not self.__target_us:
            raise ValueError("this group holds no period for its members, so there is nothing for a trim to correct toward")

        if value in (None, True):
            value = "rotate" if self.__holding else False

        if value == "rotate" and not self.__holding:
            logging.info("screens: rotating the trim moves which member comes out clean, and these are held to one rate but not one phase, so every panel's tear moves with it")

        # A run of probe counts belongs to the mode that gathered it, so a change
        # begins its own run.
        self.__trim_frames = 0
        self.__trim_mode = value

    def __period_of(self, screen, settle=False):
        """One member's refresh period, it alone asserting on the shared line.

        settle discards a first reading, which a panel fresh from bringup needs: it
        comes back about 3.4% long and settles within a second.
        """
        screen.__command(screen.CONTROLLER.REG_TEON, b"\x00")
        if settle:
            screen.__display.te_probe(self.PROBE_MS)
        period = screen.__display.te_probe(self.PROBE_MS)[0]
        screen.__command(screen.CONTROLLER.REG_TEOFF)
        return period

    def __unaligned(self, required, why):
        """Refuse an alignment that was required, or say why one asked for is unmet."""
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
