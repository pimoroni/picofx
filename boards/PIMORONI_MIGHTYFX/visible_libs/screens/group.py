# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# Several of a port's screens driven as one, sharing a frame. A group calibrates its
# members onto one refresh rate, brings their scans together, and holds them there
# from the frames it already writes, so the panels change as one.

import logging
import time

from .base import ScreenBase

# time.ticks_us() wraps at 2**30 where the C module's stamps wrap at 2**32, and
# their low bits agree, so a group's hold reduces every stamp it keeps to 30 bits
# and takes every difference there. That lets a frame's own stamp and a plain
# clock reading serve the same arithmetic, and holds to about seventeen minutes.
TICKS_MASK = 0x3FFFFFFF


class ScreenGroup(ScreenBase):
    """Several of a port's screens driven as one, sharing a frame.

    One stream reaches every member, so a wall of panels renders in the time one of
    them takes. The members keep their identity, so each can still be brought up and
    updated on its own.

    Built directly over panels agreeing on bit depth, dimensions, rate and tuning.
    Those are copied once, so a member that later re-rates itself moves only itself.
    A screen belongs to one group at a time, which is what keeps ownership of the
    panel state a group holds single.

    subset() names fewer of the members over the same display, for a frame that
    reaches only some of them. A subset owns nothing and costs no display.

    sync names the one member whose tearing-effect signal a frame waits on, which
    needs every member built te=SHARED_DC. That panel comes out clean and the rest
    tear, panels on a hub scanning independently with no edge safe for all of them.
    None takes the first member that can, saying so if none can; False declines the
    wait, so a frame goes out at once.
    """

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

    def __init__(self, *screens, sync=None, align=None, trim=None, parent=None):
        if len(screens) < 2 and parent is None:
            raise ValueError("a broadcast group needs at least two screens")

        port = screens[0].port
        if port.selector is not None:
            raise ValueError("a selector reaches one screen at a time, so a port with one cannot broadcast")

        for screen in screens:
            if screen.port is not port:
                raise ValueError("a broadcast group has to be on one port, since two ports are two streams")

        # A subset is a member set over its parent's display, so it claims no
        # members, builds no display, and leaves ownership where it is.
        if parent is not None:
            # A subset inherits its parent's nomination, since alignment and the
            # panel state stay the parent's; sync=False declines the wait for this
            # set alone. A nominated member outside the set is resolved per write.
            nominated = parent.sync if sync is None else sync
            if nominated is False:
                nominated = None
            super().__init__(port, parent.display, parent.width, parent.height,
                             parent.bitdepth, parent.backlight, nominated is not None,
                             nominated is not None, None, parent.reserve,
                             members=tuple(screens), sync=nominated)
            self.__subset_of = parent
            # Alignment stays the parent's, so a subset reports it rather than
            # owning it: its members are held whether or not this set writes them.
            self.__aligned = parent.is_aligned
            self.__reference = parent.reference
            self.__floor_us = parent.align_floor_us
            self.__trim = parent.trim
            return

        for screen in screens:
            if screen.__group is not None:
                raise ValueError("a screen belongs to one group at a time, and one of these is already in another. Take a subset of the group it is in, or build a single group over every panel that shares a frame.")

        # One member's TE, not all of them: a hub's panels scan independently, so no
        # edge is safe for every one and the nominated panel comes out clean while
        # the rest tear. Naming a member is a request and refuses if it cannot be
        # met; None takes the first that can, and False declines the wait outright.
        nominated = None
        if sync is not False:
            shared = [screen for screen in screens if screen.__shared_te]
            if sync is not None:
                if sync not in screens:
                    raise ValueError(f"{sync} is not a member of this group, so it cannot be the one its frames wait on")
                if not sync.__shared_te:
                    raise ValueError(f"{sync} was not built te=SHARED_DC, so its tearing-effect signal is not on the line this group's frames read. Build every member te=SHARED_DC, which needs the diode fitted.")
                nominated = sync
            elif shared:
                nominated = shared[0]
            else:
                logging.info("screens: this group's panels carry no shared tearing-effect signal, so its frames will not wait and every panel may tear. Build the members te=SHARED_DC to nominate one.")

        first = screens[0]
        display = port.bus.broadcast(*[screen.display for screen in screens])

        # The backlight is the first member's, since screens on a port share the one
        # PWM.
        super().__init__(port, display, first.width, first.height, first.bitdepth,
                         first.backlight, nominated is not None, nominated is not None,
                         None, first.reserve, members=tuple(screens), sync=nominated)

        self.__aligned = False
        # Three states, not two. Nulling the members' rates stops them drifting apart
        # quickly; an acquisition brings their scans together at one instant; only a
        # hold keeps them there. The residual rate spread separates them again at 30
        # to 90us a period, which is past the aim inside two of them, so an
        # acquisition on its own is worth a tenth of a second.
        self.__acquired_us = 0
        self.__holding = False
        self.__reference = None
        self.__floor_us = 0
        self.__target_us = 0
        self.__margins = ()
        self.__aim_us = 0
        self.__line_us = ()
        self.__trim_at = 0
        self.__starts = []
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
        if align is not False:
            if nominated is None:
                # The sync block above already said why there is no signal to hold
                # these panels by, so only a required alignment speaks again.
                if align is True:
                    raise ValueError("align holds a group's panels in phase by their tearing-effect signal, so it needs every member built te=SHARED_DC")
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
            self.__trim = False
        elif trim in (None, True):
            self.__trim = "rotate" if self.__holding else False
        else:
            self.__trim = trim

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
        says why and the group falls back to the member sync nominated, which is a
        legitimate outcome and not a failure.
        """
        members = self.screens
        logging.info(f"> Calibrating {len(members)} screens, about"
                     f" {len(members) * self.PROBE_MS * 2 // 1000 + 1} seconds ...")

        periods = []
        for screen in members:
            if screen.sync is None:
                self.__unaligned(required, f"{screen} carries no tearing-effect signal a group can read, so build every member te=SHARED_DC")
                return
            period = self.__period_of(screen, settle=True)
            if not period:
                self.__unaligned(required, f"{screen} returned no period, so its tearing-effect signal is not reaching the shared line")
                return
            periods.append(period)

        # Each panel's line time is its own and fixed by its oscillator; the porch
        # moves how many of them a refresh spends, not how long one lasts.
        line_us = [period / screen.line_slots for period, screen in zip(periods, members)]
        slowest = periods.index(max(periods))
        frame_us = self.display.wire_window_us()
        trims = [int(round((periods[slowest] - period) / line))
                 for period, line in zip(periods, line_us)]

        # The budget is the fastest member's, not the reference's: a written frame
        # costs fixed microseconds while a fast panel's lines are shorter, so the
        # same write eats more of them.
        margins = [(screen.line_slots + trim + screen.height - frame_us / line)
                   for screen, trim, line in zip(members, trims, line_us)]
        tightest = margins.index(min(margins))
        quanta = 2 * line_us[tightest]
        margin_us = margins[tightest] * line_us[tightest]
        reserve = self.DITHER_FRACTION * margin_us

        if quanta + reserve > margin_us or margin_us <= 0:
            self.__unaligned(required, f"{members[tightest]} keeps only {margin_us:.0f}us of tearing margin, and holding a group costs {quanta:.0f}us of granularity plus a reserve. Lengthen every member's porch, or drop the rate a step")
            return

        # Past the refusal, so nothing above has moved a panel: a group that declines
        # to align leaves every porch where bringup left it and names no reference.
        self.__reference = members[slowest]
        for screen, trim in zip(members, trims):
            if trim:
                back, front = screen.porch
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
                    back, front = screen.porch
                    screen.__set_porch(back + correction, front)
                # What the member runs at against the target, under half a line
                # either way: the rate error the hold's accumulator integrates.
                self.__residual_us[index] = held[index] + correction * line_us[index] - target
            logging.debug(f"screens: verified at {held}, spread {max(held) - min(held)}us")
            self.__target_us = target

        self.__aligned = True
        self.__floor_us = quanta
        self.__line_us = tuple(line_us)
        # In microseconds, per member, so an acquisition can tell which of them can
        # afford to be advanced and which has to be delayed the long way round.
        self.__margins = tuple(margin * line for margin, line in zip(margins, line_us))

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
            screen.command(screen.CONTROLLER.REG_TEON, b"\x00")
            falls, finished = screen.display.te_capture(2, 200)
            screen.command(screen.CONTROLLER.REG_TEOFF)
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
        members = self.screens
        # One more check than excursion rounds: the last round's outcome has to be
        # measured, or a converged group is judged on the state before it.
        for attempt in range(self.ACQUIRE_TRIES + 1):
            phases = self.__phases()
            if phases is None:
                logging.info("screens: a member went silent during the phase sweep, so the group is not in phase")
                return False

            # Phases are modular, so the spread is taken on the circle: a member one
            # step behind the reference reads a whole period ahead of it, and a plain
            # max minus min calls a converged group maximally spread.
            target = phases[members.index(self.__reference)]
            errors = [self.__fold(phase - target) for phase in phases]
            spread = max(errors) - min(errors)
            settled = spread <= self.__aim_us
            if settled or attempt == self.ACQUIRE_TRIES:
                self.__acquired_us = spread
                # The grid the hold measures against is common: every member's
                # ideal falls are the reference's, and the bookings are seeded
                # with the offsets this sweep measured, so the hold walks every
                # member onto the grid rather than holding it where it landed.
                self.__grid_at = self.__swept_at
                self.__grid_phases = tuple([target] * len(members))
                self.__phase_us = [-error for error in errors]
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
        costs the longest one and not their sum. Returns how far each member
        moved, in microseconds, later being positive.
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
                back, front = screen.porch
                screen.__set_porch(back + lines, front)

        elapsed = 0
        for index in sorted(range(len(members)), key=lambda i: abs(plans[i])):
            if not plans[index]:
                continue
            run = abs(plans[index])
            time.sleep_ms(int((run - elapsed) * self.__target_us / 1000) + 1)
            elapsed = run
            lines = self.EXCURSION_LINES if plans[index] > 0 else -self.EXCURSION_LINES
            back, front = members[index].porch
            members[index].__set_porch(back - lines, front)

        return [plans[index] * self.EXCURSION_LINES * self.__line_us[index]
                for index in range(len(members))]

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

    def __phase_spread(self):
        """How far apart the members' falls are, on the circle. 0 where unreadable."""
        phases = self.__phases()
        if phases is None:
            return 0

        target = phases[self.screens.index(self.__reference)]
        errors = [self.__fold(phase - target) for phase in phases]
        return int(max(errors) - min(errors))

    def update(self, image, *args, **kwargs):
        """Stream a frame to every member, then advance the hold and the trim.

        Takes what ScreenBase.update() takes. Every member the caller named is
        written, whatever its phase: update() is a promise that the group has
        presented by the time it returns, and a member held back to spare it a
        tear breaks that promise where a tear only spoils one frame. A member
        out of phase therefore tears until the hold walks it back, which takes a
        few frames. Both ticks run here rather than on a timer, the windows
        between written frames being the only ones a register write may sit in;
        a subset's frames tick its parent, since a member not being written
        still scans and still drifts.
        """
        owner = self.__subset_of or self
        if owner.__holding:
            to = args[6] if len(args) > 6 else kwargs.get("to")
            owner.__walk_in(self.screens if to is None else to)
        super().update(image, *args, **kwargs)
        synced = self.__synced_frame
        owner.__frame_ticked(self.display.stats(), synced, owner.__sync_delay_us)
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
        phases = self.__phases()
        if phases is None:
            logging.debug("screens: a member did not answer the sweep, so the walk keeps its bookings")
            return

        members = self.screens
        target = phases[members.index(self.__reference)]
        errors = [self.__fold(phase - target) for phase in phases]
        self.__grid_at = self.__swept_at
        self.__grid_phases = tuple([target] * len(members))
        self.__phase_us = [-error for error in errors]
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
        synced = self.__sync
        if synced is None or synced not in written:
            return 0

        # Held against a local copy of each booking, and the fold written out: every
        # written frame runs this, and a walk runs it again each period it waits.
        phase_us = self.__phase_us
        residual_us = self.__residual_us
        dither = self.__dither
        line_us = self.__line_us
        target = self.__target_us
        centre = self.__centre_us
        slack = self.WAIT_SLACK_LINES
        periods = ((time.ticks_us() - self.__held_stamp) & TICKS_MASK) / target
        indices = (range(len(members)) if written is members
                   else [members.index(screen) for screen in written])

        base_index = members.index(synced)
        base = phase_us[base_index] + periods * (
            residual_us[base_index] + dither[base_index] * line_us[base_index])

        budget = 0
        worst = 0
        for index in indices:
            carried = phase_us[index] + periods * (
                residual_us[index] + dither[index] * line_us[index])
            error = (carried - base) % target
            if error > target / 2:
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
        members = self.screens
        anchored = -1
        if synced is not None:
            stamp -= delay
            # A stamp is a fall only where the frame waited and the wait did not
            # time out, a timeout releasing at whatever phase its budget expired.
            if synced in members and stats.te_wait_us < 2 * self.__target_us:
                anchored = members.index(synced)
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

        members = self.screens
        periods = elapsed / self.__target_us
        for index in range(len(members)):
            applied = self.__dither[index]
            if applied:
                self.__anchor_dither[index] += applied * self.__line_us[index] * periods
            if index == anchored:
                self.__anchor(index, stamp)
            else:
                self.__phase_us[index] += (self.__residual_us[index] + applied * self.__line_us[index]) * periods

        reference = members.index(self.__reference)
        anchor = self.__phase_us[reference]
        drift = self.__residual_us[reference] * periods
        walking = False
        for index, screen in enumerate(members):
            if index == reference:
                continue
            line = self.__line_us[index]
            residual = self.__residual_us[index]
            applied = self.__dither[index]
            # Folded: the whole group walks the grid as the panels warm, and the
            # anchor wraps each member's booking at half a period, so two members
            # either side of a wrap differ by a period while their scans do not.
            back, front = screen.porch
            error = self.__fold(self.__phase_us[index] - anchor)
            # The write starts centre_us into the synced member's scan, so a
            # member further out than that has it outside its own budget and is
            # tearing whatever happens: the walk runs deep, its margin no longer
            # being worth protecting. Inside, one line a frame is all the ripple
            # asks for.
            if abs(error) <= self.__centre_us:
                limit = 1
            else:
                limit = self.WALK_LINES
                walking = True
                # Advancing gives porch back and stops at the walk's floor, where
                # delaying has the whole depth to spend. A member with little
                # porch in hand therefore goes the long way round, which on these
                # panels closes a half-period error sooner than crawling.
                if error > 0:
                    room = back - applied - self.WALK_FLOOR_LINES
                    long_way = (self.__target_us - error) / (self.WALK_LINES * line)
                    if room < 1 or error / (room * line) > long_way:
                        error -= self.__target_us
            lines = int(round(((drift - error) / periods - residual) / line))
            lines = limit if lines > limit else (-limit if lines < -limit else lines)
            # Shortening stops at the walk's porch floor, which keeps this
            # member's tearing pulse readable while it travels. Clamp to it
            # rather than skipping the write, which would stall a walk that has
            # to advance.
            floor_lines = self.WALK_FLOOR_LINES - back + applied
            if lines < floor_lines:
                lines = floor_lines
            if abs(lines) > 1:
                # A porch moving whole excursions lands with the same one-frame
                # ambiguity a line does, several lines at a time: not a rate.
                self.__anchor_skip[index] = True
            if lines != applied:
                screen.__set_porch(back + lines - applied, front)
                self.__dither[index] = lines

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
                        if lines:
                            back, front = screen.porch
                            if back + lines >= 1:
                                screen.__set_porch(back + lines, front)
                                self.__corrections += 1
                                self.__anchor_skip[index] = True
                                residual += lines * line
                                logging.debug(f"screens: trimmed member {index} by"
                                              f" {lines:+} line to porch {screen.porch},"
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
                back, front = screen.porch
                screen.__set_porch(back - applied, front)
                self.__dither[index] = 0
        # Back to the fall itself: with the constellation loose only the nominated
        # member comes out clean, and the fall is its own tuned phase.
        self.__sync_delay_us = 0
        self.__holding = False
        logging.info(f"screens: the panels could not be brought back into phase after a {elapsed // 1000}ms pause, so they are no longer being held together")
        if self.__trim == "rotate":
            # Moving the wait target is only free while the members fall together,
            # so freshness falls back to measuring one panel between frames.
            self.__trim = "probe"
            self.__starts = []

    def __tick_trim(self, synced=None):
        """Keep the members' rate models current between frames.

        A calibration goes stale as the panels warm, and a stale period costs an
        order of magnitude in what a prediction is worth, measured 2026-08-08.
        rotate moves the wait target to the next member each frame: each frame's
        stamp anchors the member it waited on, so every booking stays within a few
        periods of a measurement and nothing is probed. probe re-measures one
        member every TRIM_FRAMES through a capture, stalling the frame it lands on.
        """
        if not self.__trim:
            return

        members = self.screens
        if self.__trim == "rotate":
            # A frame that waited on someone else, or not at all, measured nothing,
            # so the target stays for the next frame to anchor.
            # Every member takes its turn, walking or not: the anchor is the only
            # thing that measures a member, so skipping one leaves it drifting on
            # a stale rate, which shows as a tear that walks. What a deep walk
            # needs is a porch floor that keeps its pulse readable, not a turn
            # missed.
            if synced is self.__sync:
                self.__trim_at = (members.index(self.__sync) + 1) % len(members)
                self.__sync = members[self.__trim_at]
            return

        self.__starts.append(0)
        if len(self.__starts) <= self.TRIM_FRAMES:
            return

        self.__starts = []
        index = self.__trim_at
        screen = members[index]
        self.__trim_at = (index + 1) % len(members)
        screen.command(screen.CONTROLLER.REG_TEON, b"\x00")
        falls, _ = screen.display.te_capture(4, 200)
        screen.command(screen.CONTROLLER.REG_TEOFF)
        if len(falls) > 1:
            measured = ((falls[-1] - falls[0]) & 0x3FFFFFFF) / (len(falls) - 1)
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
            back, front = screen.porch
            if back + lines < 1:
                lines = 0
            else:
                screen.__set_porch(back + lines, front)
                self.__corrections += 1
                logging.debug(f"screens: trimmed member {index} by"
                              f" {lines:+} line to porch {screen.porch},"
                              f" {measured:.0f}us against {self.__target_us:.0f}")
        if self.__holding:
            self.__residual_us[index] = measured + lines * line - self.__target_us
            if lines:
                self.__anchor_skip[index] = True

    @property
    def trim(self):
        """How the group keeps its members' periods current: rotate, probe or False."""
        return self.__trim

    @trim.setter
    def trim(self, value):
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
        self.__starts = []
        self.__trim = value

    @property
    def corrections(self):
        """Porch lines the trim has applied since construction, for a diagnostic."""
        return self.__corrections

    @property
    def exposed_frames(self):
        """Frames written with a member past its own tearing budget, for a diagnostic.

        A frame counted here may show a seam on that member; whether it does
        depends on how much the content changed. Only a held group counts, an
        unheld one having no phase to be outside of.
        """
        return self.__exposed_frames

    @property
    def worst_exposure_us(self):
        """How far past its budget the worst member of any exposed frame sat.

        Read against the group's tearing margin: a few tens of microseconds puts
        the seam within a line or two of an edge, where milliseconds put it in
        the middle of the glass.
        """
        return self.__worst_exposure_us

    @property
    def suspect_sweeps(self):
        """Captures whose own two falls did not span a plausible period, cumulative.

        Counted and not acted on. A sweep books a member from its last fall, so a
        bad one puts that member out of phase while is_in_phase and exposed_frames,
        which both price the bookings, go on reporting healthy.
        """
        return self.__suspect_sweeps

    @property
    def worst_sweep_error_us(self):
        """How far the worst such capture's span missed the period, signed."""
        return self.__worst_sweep_error_us

    def __period_of(self, screen, settle=False):
        """One member's refresh period, it alone asserting on the shared line.

        settle discards a first reading, which a panel fresh from bringup needs: it
        comes back about 3.4% long and settles within a second.
        """
        screen.command(screen.CONTROLLER.REG_TEON, b"\x00")
        if settle:
            screen.display.te_probe(self.PROBE_MS)
        period = screen.display.te_probe(self.PROBE_MS)[0]
        screen.command(screen.CONTROLLER.REG_TEOFF)
        return period

    def __unaligned(self, required, why):
        """Refuse an alignment that was required, or say why one asked for is unmet."""
        if required:
            raise ValueError(why)

        logging.info(f"screens: this group is not holding its panels in phase. {why}")

    @property
    def is_aligned(self):
        """Whether the members are held to one refresh rate.

        Their rates, not their phases: this stops them drifting apart, and on the
        glass it slows a tear band rather than removing one. is_in_phase is the
        state that makes a panel come out clean.
        """
        return self.__aligned

    @property
    def is_in_phase(self):
        """Whether the members' scans are being held together, not merely their rates.

        Held, not reached: acquisition brings them together at one instant and the
        residual rate spread pulls them apart again inside two periods, so only a
        hold makes this true for longer than a tenth of a second. It is what lets the
        wait target move, which is why the trim rotates on it.
        """
        if self.__subset_of is not None:
            return self.__subset_of.is_in_phase
        return self.__holding

    @property
    def acquired_us(self):
        """The phase spread the last acquisition reached, or 0 where it did not.

        A construction-time figure and not a running one: read is_in_phase for
        whether the members are together now.
        """
        if self.__subset_of is not None:
            return self.__subset_of.acquired_us
        return self.__acquired_us

    @property
    def reference(self):
        """The member every other is trimmed toward, the slowest of them, or None.

        None where the group is not aligned, since nothing was trimmed toward
        anything. is_aligned says the same thing and is the one to read.
        """
        return self.__reference

    @property
    def align_floor_us(self):
        """The skew the hold is predicted to settle within, or 0 when not aligned.

        An unmet align request is an outcome and not an error, so this reports zero
        where ScreenPair raises: a group falls back to its nominated member and
        carries on, and is_aligned is what distinguishes the two.
        """
        return self.__floor_us

    def subset(self, *screens, sync=None):
        """A member set over this group's display, writing only what it names.

        Cheap enough to make per frame: no display and no finaliser, just this
        group's own with a narrower set of members. A subset of one is allowed, so
        a loop over subsets does not break at the last.

        sync defaults to the group's own nomination, resolved per write since the
        nominated member need not be in the set. sync=False declines the wait for
        this set alone, leaving the group's nomination where it is.
        """
        if not screens:
            raise ValueError("a subset needs at least one screen")

        members = self.screens
        for screen in screens:
            if screen not in members:
                raise ValueError(f"{screen} is not a member of this group, so it cannot be in a subset of it")

        return ScreenGroup(*screens, sync=sync, parent=self.__subset_of or self)
