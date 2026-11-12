# The drive's handover between board and computer, and the save watcher that runs while
# the computer holds it

import machine
import time
import rp2
import vfs

from .fat import Lookup, View
from .heal import FILE_PATH, MOUNT_POINT, mount as __mount_for_board, remount

DOUBLE_PRESS_MS = 400

# service() events. HIDDEN, EJECTED and RELOADED all mean the drive is back with the
# board and effects.txt can be read. HIDDEN and EJECTED leave it hidden, since a user
# who hid or ejected it is done, while RELOADED wants it shown again once the caller
# has read the file. BUSY is a request refused because the computer was mid-write,
# which the user retries once it finishes.
IDLE = 0
SHOWN = 1
HIDDEN = 2
EJECTED = 3
BUSY = 4
RELOADED = 5

# How long to wait out a write the computer still has in flight before taking the
# volume back. Ejecting on the computer first is the only guaranteed save.
SETTLE_MS = 1500

# How long the board stays off the bus before rejoining. The first activation of the
# runtime USB device in a session does not wait here, as it disconnects and reconnects by
# itself with the 50ms hold TinyUSB applies. Measured working on macOS 15.5 and Windows 11
# at this value, and not tried lower.
__OFF_BUS_MS = 500

# How long after a bus reset the computer may take to enumerate the board before
# enumerating() gives up on it, so a host that never configures it cannot keep the
# effects standing aside for good
ENUMERATION_LIMIT_MS = 3000

# How often the save watcher compares effects.txt's directory entry while the computer
# holds the drive. Every kind of save updates the entry, and copying other files never
# does. A change counts once two polls in a row see it, so a half-finished save or a
# read torn by a host write cannot act. A poll only reads the entry where the computer
# has written since the last, which is what keeps it out of a screen's frame.
WATCH_POLL_MS = 500

__exposed = False
__was_pressed = False   # The button as the last service() call saw it
__last_edge = None      # When a press began that a second may make a double, else None
__watching = False
__entry_seen = None     # effects.txt's directory entry as last shown or acted on
__entry_pending = None  # A changed entry seen once, counting when the next look matches it
__writes_seen = None    # The computer's write count at the last look, None before the first
__watch_at = None       # When service() last polled
__watch_reader = None   # The reader the save watcher keeps while the drive is shown
__reset_at = None       # When the last bus reset came, None once enumeration is over
__on_reset = None
__save_timer = None

def watch(enabled):
    """
    Set whether a save to effects.txt re-reads it without waiting for an eject.
    service() then answers a save with RELOADED, exactly as it answers a single press.
    """
    global __watching
    __watching = bool(enabled)


def __short_form(name):
    # A name that fits 8.3 as the 11 bytes its directory entry stores
    base, _, extension = name.upper().partition(".")
    return (base + "        ")[:8].encode() + (extension + "   ")[:3].encode()


# effects.txt's short name, which the save watcher matches its directory entry by
__EFFECTS_SHORT = __short_form(FILE_PATH.rsplit("/", 1)[1])


def __effects_entry():
    # The bytes that change when effects.txt is saved: time, date, first cluster and
    # size from its directory entry, read straight from the flash, so the volume the
    # computer holds is never touched. None where the volume or the entry is absent
    global __watch_reader
    try:
        if __watch_reader is None:
            __watch_reader = Lookup()
        return __watch_reader.root_entry_bytes(__EFFECTS_SHORT, 22, 32)
    except OSError:
        return None


def __entry_settled():
    # Whether effects.txt's directory entry has changed and read the same on two
    # looks in a row, so a save has landed. Each call is one poll
    global __entry_seen, __entry_pending, __writes_seen

    # Has the computer written nothing since the last look, with no change waiting on a
    # second one? The entry cannot have moved, and reading it takes longer than a
    # screen's frame has to spare
    writes = rp2.msc_write_count()
    if writes == __writes_seen and __entry_pending is None:
        return False

    # The count is read before the entry, so a write landing between the two moves the
    # count past what is kept here and the next poll looks again
    entry = __effects_entry()
    __writes_seen = writes
    if __entry_seen is None:
        __entry_seen = entry
    elif entry != __entry_seen:
        if entry == __entry_pending:
            return True
        __entry_pending = entry
    else:
        __entry_pending = None
    return False


def __reset_if_saved(_timer):
    # The save watcher for while nothing calls service(), run by reset_on_save()
    global __entry_pending
    # Timer callbacks arrive via the scheduler, so one already in flight at deinit
    # can still run after the watcher is turned off
    if __save_timer is None or not (__exposed and __watching):
        return
    if rp2.is_msc_busy():
        # A save may still be in flight, so nothing seen counts yet
        __entry_pending = None
    elif __entry_settled():
        machine.reset()


def reset_on_save(enabled):
    """
    Set whether a save that watch() would answer resets the board instead, for a caller
    that hands the board to something which never calls service(). A soft timer does
    the polling, so it runs wherever the computer can save at all, the USB task
    being scheduled the same way. An eject resets nothing.
    """
    global __save_timer
    if __save_timer is not None:
        __save_timer.deinit()
        __save_timer = None
    if enabled:
        __save_timer = machine.Timer(period=WATCH_POLL_MS, callback=__reset_if_saved)


def exposed():
    """Whether the connected computer currently owns the drive."""
    return __exposed


def busy():
    """
    Whether the computer is mid-transfer. Worth standing aside for, since a transfer
    costs anything running from a timer on a Mighty FX most of a tenth of a second in
    one hitch, which reads as a lurch.
    """
    return __exposed and rp2.is_msc_busy()


def enumerating():
    """
    Whether the computer is still enumerating the board after a bus reset.

    Enumeration's replies are due within tens of milliseconds, and the board answers
    them between other scheduled work, so anything busy on the board stands aside
    until it is over. A reset can come at any time, from a rejoin, the computer
    waking, or a port it reset after an error.
    """
    global __reset_at
    if __reset_at is None:
        return False
    if rp2.usb_mounted() or \
            time.ticks_diff(time.ticks_ms(), __reset_at) >= ENUMERATION_LIMIT_MS:
        __reset_at = None
        return False
    return True


def on_bus_reset(callback):
    """
    Have callback called on every USB bus reset, with no arguments, or None to stop.

    It runs in the USB task, ahead of enumeration's first reply, so it can quiet the
    board at once rather than at its caller's next look.
    """
    global __on_reset
    __on_reset = callback


def __bus_reset():
    # The reset callback __rejoin_bus() configures, run in the USB task
    global __reset_at
    __reset_at = time.ticks_ms()
    if __on_reset is not None:
        __on_reset()


def __rejoin_bus():
    # Leave the USB bus and return, so the computer enumerates the board afresh.
    #
    # A computer can keep its view of the volume from before the board took it back,
    # serving it, failing reads, or writing it over what the board wrote since, and
    # nothing on its side recovers. Leaving the bus it cannot miss. The serial console
    # drops and returns with it, and macOS reports the drive as not ejected properly,
    # which is true
    usbd = machine.USBDevice()
    if usbd.active():
        usbd.active(False)
        time.sleep_ms(__OFF_BUS_MS)
    else:
        # The first activation disconnects and reconnects by itself, with the
        # built-in serial and drive descriptors since nothing else is configured
        usbd.builtin_driver = usbd.BUILTIN_DEFAULT
    # The built-in descriptors unchanged, configured here for the reset callback, which
    # sees every bus reset from now on
    usbd.config(usbd.builtin_driver.desc_dev, usbd.builtin_driver.desc_cfg,
                desc_strs=None, reset_cb=__bus_reset)
    usbd.active(True)


def expose():
    """
    Show the drive to the connected computer, releasing the board's own
    mount while the computer owns it.

    The board stays on the USB bus and the computer finds the drive as it arrives. It
    let go of the drive when the board took it. Only a session's first show rejoins the
    bus, which drops the serial console once. Anything the caller runs from a timer
    carries on through that rejoin. Anything it drives itself, such as a screen, holds
    its last frame.
    """
    global __exposed, __entry_seen, __entry_pending, __writes_seen, __watch_at
    if __exposed:
        return False
    try:
        vfs.umount(MOUNT_POINT)
    except OSError:
        pass
    rp2.enable_msc()
    vfs.mount(View(), MOUNT_POINT)
    # Is this the session's first show?
    if not machine.USBDevice().active():
        # Activating the runtime USB device leaves the bus and returns by itself, and its
        # reset callback sees every bus reset from then on
        __rejoin_bus()
    __exposed = True
    # Counted before the entry is read, as every poll does. Not watching, the first poll looks
    __writes_seen = rp2.msc_write_count() if __watching else None
    __entry_seen = __effects_entry() if __watching else None
    __entry_pending = None
    __watch_at = None
    return True


def __take_from_computer():
    # Take the media from a computer that has it, then leave the USB bus and return. A
    # write still in flight is waited out first. Returns whether the computer had the media.
    #
    # A computer that stays connected learns the media has gone only from a failed
    # transfer. macOS retries that for as long as the board stays on the bus, and
    # everything reading the drive waits with it. Leaving the bus makes the computer drop
    # its view of the volume at once
    deadline = time.ticks_add(time.ticks_ms(), SETTLE_MS)
    while rp2.is_msc_busy() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        time.sleep_ms(50)
    # Has the computer the media? It has not at a cold boot, nor once it has ejected the drive
    if not rp2.disable_msc():
        # Nothing was taken, so the board stays on the bus
        return False
    __rejoin_bus()
    # Enumeration's replies are due within tens of milliseconds, so whatever the caller
    # does next waits until the computer has the board again
    deadline = time.ticks_add(time.ticks_ms(), ENUMERATION_LIMIT_MS)
    while not rp2.usb_mounted() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        time.sleep_ms(20)
    return True


def __forget_shown():
    # Clear what this session knew of a drive it had shown, and unmount the view at its
    # mount point. The mount in heal.py would take the view as the drive already mounted
    global __exposed, __watch_reader
    __exposed = False
    __watch_reader = None
    try:
        vfs.umount(MOUNT_POINT)
    except OSError:
        pass


def withdraw():
    """
    Take the drive back from the computer and re-read it, waiting out any write still
    in flight. Returns True when effects.txt may have changed.

    The board leaves the USB bus and returns, which drops the serial console once. It
    stays on the bus where the computer ejected the drive itself.
    """
    if not __exposed:
        return False
    __take_from_computer()
    __forget_shown()
    remount()
    return True


def mount(screens=True, wireless=False, sound=True):
    """
    Mount the drive read-write at /fx. Returns whether the drive ended up mounted.

    A soft reset or a stopped program can leave the drive with the computer. It is then
    taken back first, which drops the serial console once.

    `screens`, `wireless` and `sound` say which parts the board has, and decide the
    shipped files and folders the drive is given.
    """
    if __take_from_computer() or __exposed:
        __forget_shown()
    return __mount_for_board(screens, wireless, sound)


def service(pressed):
    """
    Call regularly with the button state.

    A double press shows the drive to the connected computer, and another, or an
    eject on the computer, takes it back. A single press while the drive is showing
    takes it back too, but asks for it to be shown again, which is the quick way to
    try an edit without putting the drive away. Either answers BUSY instead while
    the computer is mid-write, and the user retries once it finishes.

    Returns one of the events declared above.

    With watch() on, a save landing on effects.txt answers RELOADED as a single
    press does, read from the file's directory entry, so nothing else written to
    the drive ever takes it back.

    A single press cannot be told from the first of a double until the double press
    window has passed, so it lands DOUBLE_PRESS_MS after the press began.
    """
    global __was_pressed, __last_edge, __watch_at, __entry_pending
    if __exposed and rp2.msc_ejected():
        withdraw()
        return EJECTED

    event = IDLE
    now = time.ticks_ms()

    if pressed and not __was_pressed:
        if __last_edge is not None and time.ticks_diff(now, __last_edge) <= DOUBLE_PRESS_MS:
            __last_edge = None
            if __exposed:
                if rp2.is_msc_busy():
                    event = BUSY
                else:
                    withdraw()
                    event = HIDDEN
            else:
                expose()
                event = SHOWN
        else:
            __last_edge = now

    elif __last_edge is not None and time.ticks_diff(now, __last_edge) > DOUBLE_PRESS_MS:
        # The window closed with no second press, so that was a single one. It only
        # means something while the drive is showing, since the file cannot have been
        # edited otherwise
        __last_edge = None
        if __exposed:
            if rp2.is_msc_busy():
                event = BUSY
            else:
                withdraw()
                event = RELOADED

    __was_pressed = pressed

    # The save watcher, under everything the button asked for
    if event == IDLE and __exposed and __watching:
        if rp2.is_msc_busy():
            # A save may still be in flight, so nothing seen counts yet
            __entry_pending = None
        elif __watch_at is None or time.ticks_diff(now, __watch_at) >= WATCH_POLL_MS:
            __watch_at = now
            if __entry_settled():
                withdraw()
                return RELOADED

    return event
