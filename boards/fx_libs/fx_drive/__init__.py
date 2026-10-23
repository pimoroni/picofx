"""
The FX drive is a small FAT partition holding effects.txt, editable from a connected
computer over USB mass storage, and room for the assets a program reads. The mount
is read-write whenever the board holds the drive, and released while the computer
does, so the two writers can never meet. While the computer holds it, the mount
point is a read-only view read straight from the flash, so a program still finds
its files there.

The drive is shown at boot and controlled from then on by the button passed to
service(). A double press shows or hides it, and hiding it, or ejecting it on the
computer, re-reads the file. An eject does not show it again.
"""

import errno
import machine
import os
import time
import rp2
import sys
import vfs

import fx_defaults

from .fat import Stream, __ENOTDIR, __FatReader, __S_IFDIR, __View, stream
from .pages import __pages, __write_page

MOUNT_POINT = "/fx"
FILE_PATH = MOUNT_POINT + "/effects.txt"
README_NAME = "README.txt"
SECRETS_PATH = MOUNT_POINT + "/secrets.py"

# The drive's examples folder, and where it is also mounted
EXAMPLES_DIR = MOUNT_POINT + "/examples"
EXAMPLES_MOUNT_POINT = "/examples"

VOLUME_LABEL = "FX"

# How much of a shipped document is compared. A shorter one is read to the end, and a
# longer one is met at both ends
__READ_TO_END = 4096
__EDGE = 512

# FAT attribute bits, per VfsFat.chmod.
__ATTR_READ_ONLY = 0x01

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

# How long the board stays off the bus before rejoining, on the second reload and after.
# The first activation of the runtime USB device disconnects and reconnects by itself,
# with the 50ms hold TinyUSB applies, so only a later expose() waits here. Measured
# working on macOS 15.5 and Windows 11 at this value, and not tried lower.
__OFF_BUS_MS = 500

# How long after a bus reset the computer may take to enumerate the board before
# enumerating() gives up on it, so a host that never configures it cannot keep the
# effects standing aside for good
ENUMERATION_LIMIT_MS = 3000

# How often the save watcher compares effects.txt's directory entry while the computer
# holds the drive. Every kind of save updates the entry, and copying other files never
# does. A change counts once two polls in a row see it, so a half-finished save or a
# read torn by a host write cannot act.
WATCH_POLL_MS = 500

__exposed = False
__was_pressed = False   # The button as the last service() call saw it
__last_edge = None      # When a press began that a second may make a double, else None
__withdrawn = False     # Whether the drive has been taken back, so expose() rejoins the bus
__watching = False
__entry_seen = None     # effects.txt's directory entry as last shown or acted on
__entry_pending = None  # A changed entry seen once, counting when the next look matches it
__watch_at = None       # When service() last looked at the entry
__watch_reader = None   # The reader the save watcher keeps while the drive is shown
__reset_at = None       # When the last bus reset came, None once enumeration is over
__on_reset = None
__save_timer = None

# What the board told mount() it has, for the remount when the computer hands the drive back
__screens = True
__wireless = False


def __ends(text):
    # A document's length and the two ends __holds() compares, the whole of a short one
    if len(text) <= __READ_TO_END:
        return len(text), text, ""
    return len(text), text[:__EDGE], text[-__EDGE:]


def __holds(path, size, head, tail):
    # Whether the file is size long, starting with head and ending with tail. Size first, so
    # a missing or half-written file answers without a read. A long document is met at both
    # ends, since reading the manual to the end took 424ms per mount on a Mighty FX against
    # 40ms for its ends, and every mount and button press would pay it. That misses only a
    # rebuild differing in its middle at the same length, which nothing here produces. Every
    # document is ASCII, enforced by the build tools, so its length in characters is in bytes
    try:
        if os.stat(path)[6] != size:
            return False
        with open(path) as f:
            if f.read(len(head)) != head:
                return False
            f.seek(size - len(tail))
            return f.read(len(tail)) == tail
    except OSError:
        return False


# Filled by __heal(), emptied by each mount
__unhealed = []


def unhealed():
    """
    The shipped documents the last mount could not bring up to date, for a caller to
    report on the drive itself, since a console line reaches nobody with only the drive
    in front of them.
    """
    return tuple(__unhealed)


def __heal(fs, name, document):
    # Put a shipped file back on the drive, unless it is already there. The document is its
    # text, or a packed page from fx_editor or fx_manual, which opens with its length and
    # its two ends, those of the page as written to the drive
    path = MOUNT_POINT + "/" + name
    if isinstance(document, str):
        size, head, tail = __ends(document)
    else:
        size, head, tail = document[:3]
    if __holds(path, size, head, tail):
        return
    # A document that will not fit is left as it stands: stale and whole beats
    # part-written, and opening for write would truncate it before failing
    try:
        stats = os.statvfs(MOUNT_POINT)
        room = stats[0] * stats[3]
        try:
            room += os.stat(path)[6]
        except OSError:
            pass
        if room < size:
            print("the FX drive is full, so {} was left as it was".format(name))
            __unhealed.append(name)
            return
    except OSError:
        pass
    try:
        # A read-only file refuses opens for write, so clear the bit to rewrite.
        fs.chmod(name, 0, __ATTR_READ_ONLY)
    except OSError:
        pass
    try:
        with open(path, "w" if isinstance(document, str) else "wb") as f:
            if isinstance(document, str):
                f.write(document)
            else:
                __write_page(document, f)
        fs.chmod(name, __ATTR_READ_ONLY, __ATTR_READ_ONLY)
    except OSError:
        # A full drive has nowhere to put it. The board comes up regardless, since a
        # missing document costs a reader nothing and a dead board costs them
        # everything. A part-written file is left for the next mount to finish
        print("the FX drive is full, so {} could not be rebuilt".format(name))
        __unhealed.append(name)


def __remove_tree(path):
    # Remove a file, or a directory and everything in it, ignoring what will not go
    try:
        if os.stat(path)[0] & __S_IFDIR:
            for name in os.listdir(path):
                __remove_tree(path + b"/" + name)
            os.rmdir(path)
        else:
            os.remove(path)
    except OSError:
        pass


def __sweep_host_litter():
    # Remove what a computer leaves on the drive that the board has no use for. Chromium
    # saves through a .crswap and renames on close, so one still present is an unfinished
    # save. macOS writes a ._ sidecar beside every file it touches and a .fseventsd folder
    # at the root. Names are listed as bytes, since listed as str one name outside ASCII
    # raises UnicodeError for the whole listing, and the drive would never be shown
    root = MOUNT_POINT.encode()
    for name in os.listdir(root):
        lower = name.lower()
        if lower.endswith(b".crswap") or name.startswith(b"._") or lower == b".fseventsd":
            __remove_tree(root + b"/" + name)


def __has_boot_signature(bdev):
    # Whether sector zero still ends 0x55 0xAA, so something formatted this once
    sector = bytearray(512)
    try:
        bdev.readblocks(0, sector)
    except OSError:
        return False
    return sector[510] == 0x55 and sector[511] == 0xAA


def mount(screens=True, wireless=False):
    """
    Mount the drive read-write at /fx, rebuilding it when the filesystem is blank,
    effects.txt is missing, or any shipped document differs from the text the board
    carries. Returns whether the drive ended up mounted.

    `screens` is False for a board found to have no screen ports, which is then given
    the catalogue without them where its pages carry one. `wireless` is True for a board
    with a wireless module, which is given the WiFi credentials.
    """
    global __screens, __wireless
    __screens, __wireless = screens, wireless
    bdev = rp2.Flash(msc=True)
    fs = vfs.VfsFat(bdev)
    try:
        vfs.mount(fs, MOUNT_POINT)
    except OSError as e:
        # Already mounted answers EPERM, and anything other than a blank volume is
        # raised rather than papered over with a reformat
        if e.args[0] == errno.EPERM:
            return True
        if e.args[0] != errno.ENODEV:
            raise
        # A volume that still carries a boot signature was formatted by someone, so it is
        # damaged rather than blank. Formatting would take the user's files with it, so it
        # is left alone for the computer to offer a repair
        if __has_boot_signature(bdev):
            print("the FX drive is damaged, so it has been left alone")
            print("connect a computer and let it repair or format the drive")
            return False
        vfs.VfsFat.mkfs(bdev)
        fs = vfs.VfsFat(bdev)
        vfs.mount(fs, MOUNT_POINT)
        fs.label(VOLUME_LABEL)
    __mount_examples()
    if MOUNT_POINT not in sys.path:
        # The drive's modules import after the board's own, the WiFi credentials among them
        sys.path.append(MOUNT_POINT)
    try:
        os.stat(FILE_PATH)
    except OSError:
        try:
            with open(FILE_PATH, "w") as f:
                f.write(fx_defaults.EFFECTS)
        except OSError:
            # A full drive with the file already deleted. Raising would leave nothing
            # playing, where mounting anyway leaves the drive to be emptied. The empty
            # file a failed write leaves has to go, as an empty effects.txt asks for a
            # dark board and would stop this mount restoring the default
            print("the FX drive is full, so effects.txt could not be restored")
            print("delete a file from the drive and the default comes back")
            try:
                os.remove(FILE_PATH)
            except OSError:
                pass
    if wireless:
        __restore_secrets()
    del __unhealed[:]
    __heal(fs, README_NAME, fx_defaults.README)
    for name, document in __pages(screens):
        __heal(fs, name, document)
    __sweep_host_litter()
    return True


def __remount():
    # Mount again with what the board last told mount()
    return mount(__screens, __wireless)


class __Examples:
    # The drive's examples folder, mounted at /examples so an example finds its files by
    # the same path on every board, those without a drive keeping the folder on their
    # own filesystem. Each call is passed on to whatever is mounted at the mount point,
    # the board's own mount or the view, and answers as that does

    def __init__(self):
        self.__cwd = ""

    def __target(self, path):
        path = path if path.startswith("/") else self.__cwd + "/" + path
        return (EXAMPLES_DIR + path).rstrip("/")

    def mount(self, readonly, mkfs):
        # vfs.mount() and vfs.umount() call these, and there is nothing to set up
        pass

    def umount(self):
        pass

    def open(self, path, mode):
        return open(self.__target(path), mode)

    def stat(self, path):
        return os.stat(self.__target(path))

    def ilistdir(self, path):
        return os.ilistdir(self.__target(path))

    def statvfs(self, _path):
        return os.statvfs(MOUNT_POINT)

    def chdir(self, path):
        target = self.__target(path)
        if not os.stat(target)[0] & __S_IFDIR:
            raise OSError(__ENOTDIR)
        self.__cwd = target[len(EXAMPLES_DIR):]

    def getcwd(self):
        return self.__cwd or "/"

    def mkdir(self, path):
        os.mkdir(self.__target(path))

    def remove(self, path):
        os.remove(self.__target(path))

    def rename(self, old_path, new_path):
        os.rename(self.__target(old_path), self.__target(new_path))

    def rmdir(self, path):
        os.rmdir(self.__target(path))


def __restore_secrets():
    # Write the empty WiFi credentials where the drive has none
    try:
        os.stat(SECRETS_PATH)
    except OSError:
        try:
            with open(SECRETS_PATH, "w") as f:
                f.write(fx_defaults.SECRETS)
        except OSError:
            # A full drive. The empty file the failed write leaves would stop the next mount
            # restoring it
            try:
                os.remove(SECRETS_PATH)
            except OSError:
                pass


def __mount_examples():
    # Mount the examples folder at /examples, once, staying through every handover
    try:
        vfs.mount(__Examples(), EXAMPLES_MOUNT_POINT)
    except OSError as e:
        # Already mounted answers EPERM
        if e.args[0] != errno.EPERM:
            raise


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
            __watch_reader = __FatReader()
        return __watch_reader.__root_entry_bytes(__EFFECTS_SHORT, 22, 32)
    except OSError:
        return None


def __entry_settled():
    # Whether effects.txt's directory entry has changed and read the same on two
    # looks in a row, so a save has landed. Each call is one look
    global __entry_seen, __entry_pending
    entry = __effects_entry()
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
    # A computer that missed the media leaving keeps serving its old view of the volume
    # and fails every read that reaches the device, and nothing on its side recovers.
    # Leaving the bus it cannot miss. The serial console drops and returns with it, and
    # macOS reports the drive as not ejected properly, which is true
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

    After a withdraw, also rejoins the USB bus, so the computer enumerates the board
    afresh and reads the drive as it now is. Not at boot, when nothing has been taken
    back. Anything the caller runs from a timer carries on through the rejoin.
    Anything it drives itself, such as a screen, holds its last frame.
    """
    global __exposed, __withdrawn, __entry_seen, __entry_pending, __watch_at
    if __exposed:
        return False
    rejoin = __withdrawn
    __withdrawn = False
    try:
        vfs.umount(MOUNT_POINT)
    except OSError:
        pass
    rp2.enable_msc()
    vfs.mount(__View(), MOUNT_POINT)
    if rejoin:
        __rejoin_bus()
    __exposed = True
    __entry_seen = __effects_entry() if __watching else None
    __entry_pending = None
    __watch_at = None
    return True


def withdraw():
    """
    Take the drive back from the computer and re-read it, waiting out any
    write still in flight. Returns True when effects.txt may have changed.
    """
    global __exposed, __withdrawn, __watch_reader
    if not __exposed:
        return False
    deadline = time.ticks_add(time.ticks_ms(), SETTLE_MS)
    while rp2.is_msc_busy() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        time.sleep_ms(50)
    rp2.disable_msc()
    __exposed = False
    __withdrawn = True
    __watch_reader = None
    # The view goes first, since mount() takes a mount point already in use as done
    try:
        vfs.umount(MOUNT_POINT)
    except OSError:
        pass
    __remount()
    return True


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
    window has passed, so it lands DOUBLE_PRESS_MS after the release.
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
