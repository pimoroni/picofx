"""
The FX drive: a small FAT partition holding effects.txt, editable from a connected
computer over USB mass storage, and room for the assets a program reads. The mount
is read-write whenever the board holds the drive, and released while the computer
does, so the two writers can never meet.

The drive is shown at boot and controlled by the button from then on: a double press
of the button passed to service() shows or hides it, and hiding it, or ejecting it on
the computer, re-reads the file. An eject does not show it again.
"""

import errno
import os
import time
import rp2
import vfs

import fx_defaults
import fx_editor
import fx_manual

MOUNT_POINT = "/fx"
FILE_PATH = MOUNT_POINT + "/effects.txt"
README_NAME = "README.txt"
MANUAL_NAME = "MANUAL.html"
PICKER_NAME = "PICKER.html"
CATALOGUE_NAME = "catalogue.js"
ERRORS_PATH = MOUNT_POINT + "/errors.txt"

VOLUME_LABEL = "FX"

# How much of a shipped document is compared. Anything shorter is read to the end;
# anything longer is met at both ends, measured at 40ms against 424ms for a mount.
__READ_TO_END = 4096
__EDGE = 512

# FAT attribute bits, per VfsFat.chmod.
__ATTR_READ_ONLY = 0x01

DOUBLE_PRESS_MS = 400

# service() events. HIDDEN, EJECTED and RELOADED all mean the drive is back with the
# board and effects.txt can be read. They differ in what should happen next: HIDDEN
# and EJECTED leave it hidden, since a user who hid or ejected it is done, while
# RELOADED wants it shown again once the caller has read the file. BUSY is a request
# refused because the computer was mid-write; the user retries once it finishes.
IDLE = 0
SHOWN = 1
HIDDEN = 2
EJECTED = 3
BUSY = 4
RELOADED = 5

# How long to wait out a write the computer still has in flight before taking the
# volume back. Ejecting on the computer first is the only guaranteed save.
SETTLE_MS = 1500

# How long the drive stays away before it can be shown again. A computer that wrote
# effects.txt itself keeps its own copy of the directory, and will write that back over
# ours unless it sees the volume leave, which costs the edit the board just read. It
# notices within a second on the computers measured; the rest is margin for those that
# look less often.
HIDDEN_MS = 1500

# How often the save watcher compares effects.txt's directory entry while the
# computer holds the drive. Every kind of save updates the entry, where copying
# other files onto the drive never does, so this is what "the file was saved"
# looks like from the board. A change must be seen on two polls in a row before
# it counts, so a half-finished save or a read torn by a host write cannot act.
WATCH_POLL_MS = 500

__exposed = False
__was_pressed = False
__last_edge = None
__withdrawn_at = None
__watching = False
__entry_seen = None
__entry_pending = None
__watch_at = None
__watch_buffer = None


def __holds(path, text):
    """Whether the file already reads as the text.

    Size first, so a missing or half-written file answers without a read. A short
    document is then compared to its end; a long one by its first and last piece,
    since reading the manual to the end costs about 400ms on this volume and every
    mount and every button press would pay it. What that trades away is a rebuilt
    document differing only in its middle at exactly the same length, which nothing
    here produces. Both are ASCII, which build_manual.py enforces, so a length in
    characters is a length in bytes.
    """
    try:
        if os.stat(path)[6] != len(text):
            return False
        with open(path) as f:
            if len(text) <= __READ_TO_END:
                return f.read() == text
            if f.read(__EDGE) != text[:__EDGE]:
                return False
            f.seek(len(text) - __EDGE)
            return f.read(__EDGE) == text[-__EDGE:]
    except OSError:
        return False


def __heal(fs, name, text):
    """Put a shipped file back on the drive, unless it is already there."""
    path = MOUNT_POINT + "/" + name
    if __holds(path, text):
        return
    try:
        # A read-only file refuses opens for write, so clear the bit to rewrite.
        fs.chmod(name, 0, __ATTR_READ_ONLY)
    except OSError:
        pass
    try:
        with open(path, "w") as f:
            f.write(text)
        fs.chmod(name, __ATTR_READ_ONLY, __ATTR_READ_ONLY)
    except OSError:
        # A full drive has nowhere to put it. The board comes up regardless, since a
        # missing document costs a reader nothing and a dead board costs them
        # everything. A part-written file is left for the next mount to finish
        print("the FX drive is full, so {} could not be rebuilt".format(name))


def __sweep_swap_files():
    """
    Remove the temporary files a browser save leaves when it is interrupted.
    Chromium writes through a .crswap beside the file and renames on close, so
    one still present is a save the drive left with. Its content is unfinished
    by definition; the real file still holds the last completed save.
    """
    for name in os.listdir(MOUNT_POINT):
        if name.lower().endswith(".crswap"):
            try:
                os.remove(MOUNT_POINT + "/" + name)
            except OSError:
                pass


def __has_boot_signature(bdev):
    """Whether sector zero still ends 0x55 0xAA, so something formatted this once."""
    sector = bytearray(512)
    try:
        bdev.readblocks(0, sector)
    except OSError:
        return False
    return sector[510] == 0x55 and sector[511] == 0xAA


def mount():
    """
    Mount the drive read-write at /fx, rebuilding it when the filesystem is blank,
    effects.txt is missing, or either shipped document differs from the text the
    board carries. Returns whether the drive ended up mounted.
    """
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
        # A volume that still carries a boot signature was formatted by someone, so
        # it is damaged rather than blank. Formatting would take the user's files
        # with it; leave it alone and let the computer offer to repair it
        if __has_boot_signature(bdev):
            print("the FX drive is damaged, so it has been left alone")
            print("connect a computer and let it repair or format the drive")
            return False
        vfs.VfsFat.mkfs(bdev)
        fs = vfs.VfsFat(bdev)
        vfs.mount(fs, MOUNT_POINT)
        fs.label(VOLUME_LABEL)
    try:
        os.stat(FILE_PATH)
    except OSError:
        try:
            with open(FILE_PATH, "w") as f:
                f.write(fx_defaults.EFFECTS)
        except OSError:
            # A full drive with the file already deleted. Unguarded this reaches
            # main.py and the board plays nothing, where mounting anyway leaves the
            # drive there to be emptied and autofx to say it could not be read.
            # The empty file the failed write leaves behind has to go: an empty
            # effects.txt is a board asked to stay dark, and it would keep this
            # mount from restoring the default once there is room again
            print("the FX drive is full, so effects.txt could not be restored")
            print("delete a file from the drive and the default comes back")
            try:
                os.remove(FILE_PATH)
            except OSError:
                pass
    __heal(fs, README_NAME, fx_defaults.README)
    __heal(fs, MANUAL_NAME, fx_manual.MANUAL)
    __heal(fs, PICKER_NAME, fx_editor.PICKER)
    __heal(fs, CATALOGUE_NAME, fx_editor.CATALOGUE)
    __sweep_swap_files()
    return True


def path(name):
    """Where a file on the drive lives, so nothing has to name the mount point."""
    return MOUNT_POINT + "/" + name


class __Writable:
    def __enter__(self):
        return MOUNT_POINT

    def __exit__(self, *args):
        return False


def writable():
    """
    A block in which the drive may be written. The mount is read-write whenever the
    board holds the drive, so the block changes nothing; it marks the writes that
    must not happen while the computer has it, where they raise OSError.
    """
    return __Writable()


def watch(enabled):
    """
    Whether a save to effects.txt re-reads it without waiting for an eject, which
    is the file's own reload=auto. service() answers a save with RELOADED, exactly
    as it answers a single press.
    """
    global __watching
    __watching = bool(enabled)


def __effects_entry():
    """
    The bytes that change when effects.txt is saved: time, date, first cluster and
    size from its directory entry, read straight from the flash, so the volume the
    computer holds is never touched. None where the volume or the entry is absent.
    """
    global __watch_buffer

    bdev = rp2.Flash(msc=True)
    if __watch_buffer is None:
        __watch_buffer = bytearray(bdev.ioctl(5, 0))
    block = __watch_buffer
    size = len(block)

    try:
        bdev.readblocks(0, block)
        if block[510] != 0x55 or block[511] != 0xAA:
            return None
        sector = block[11] | (block[12] << 8)
        reserved = block[14] | (block[15] << 8)
        fats = block[16]
        root_entries = block[17] | (block[18] << 8)
        fat_sectors = block[22] | (block[23] << 8)

        # The FAT12 root directory sits behind the reserved sectors and the FATs,
        # at a fixed size, 32 bytes an entry
        start = (reserved + fats * fat_sectors) * sector
        loaded = None
        for offset in range(start, start + root_entries * 32, 32):
            wanted = offset // size
            if wanted != loaded:
                bdev.readblocks(wanted, block)
                loaded = wanted
            at = offset % size
            if block[at:at + 11] == b"EFFECTS TXT":
                return bytes(block[at + 22:at + 32])
    except OSError:
        return None
    return None


def exposed():
    """Whether the connected computer currently owns the drive."""
    return __exposed


def busy():
    """
    Whether the computer is mid-transfer. Worth standing aside for: a transfer costs
    a running effect most of a tenth of a second in one hitch, which reads as a lurch.
    """
    return __exposed and rp2.is_msc_busy()


def expose():
    """
    Show the drive to the connected computer, releasing the board's own
    mount while the computer owns it.

    Waits out the rest of HIDDEN_MS since the drive was taken back, so the computer
    has seen it leave. Effects run from a timer and carry on; anything the caller
    drives itself, a screen being the one, holds its last frame for the wait.
    """
    global __exposed, __withdrawn_at
    if __exposed:
        return False
    if __withdrawn_at is not None:
        remaining = HIDDEN_MS - time.ticks_diff(time.ticks_ms(), __withdrawn_at)
        if remaining > 0:
            time.sleep_ms(remaining)
        __withdrawn_at = None
    try:
        vfs.umount(MOUNT_POINT)
    except OSError:
        pass
    rp2.enable_msc()
    __exposed = True
    global __entry_seen, __entry_pending, __watch_at
    __entry_seen = __effects_entry() if __watching else None
    __entry_pending = None
    __watch_at = None
    return True


def withdraw():
    """
    Take the drive back from the computer and re-read it, waiting out any
    write still in flight. Returns True when effects.txt may have changed.
    """
    global __exposed, __withdrawn_at
    if not __exposed:
        return False
    deadline = time.ticks_add(time.ticks_ms(), SETTLE_MS)
    while rp2.is_msc_busy() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        time.sleep_ms(50)
    rp2.disable_msc()
    __exposed = False
    __withdrawn_at = time.ticks_ms()
    mount()
    return True


def service(pressed):
    """
    Call regularly with the button state.

    A double press shows the drive to the connected computer, and another, or an
    eject on the computer, takes it back. A single press while the drive is showing
    takes it back too, but asks for it to be shown again, which is the quick way to
    try an edit without putting the drive away. Either answers BUSY instead while
    the computer is mid-write, and the user retries once it finishes.

    Returns IDLE, SHOWN, HIDDEN, EJECTED, BUSY or RELOADED. HIDDEN, EJECTED and
    RELOADED all mean the board holds the drive and effects.txt can be read; only
    RELOADED expects the caller to show it again afterwards.

    With watch() on, a save landing on effects.txt answers RELOADED as a single
    press does, read from the file's directory entry, so nothing else written to
    the drive ever takes it back.

    Note that a single press cannot be told from the first of a double until the
    double press window has passed, so it lands DOUBLE_PRESS_MS after the release.
    """
    global __was_pressed, __last_edge
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
        global __watch_at, __entry_seen, __entry_pending
        if rp2.is_msc_busy():
            # A save may still be in flight, so nothing seen counts yet
            __entry_pending = None
        elif __watch_at is None or time.ticks_diff(now, __watch_at) >= WATCH_POLL_MS:
            __watch_at = now
            entry = __effects_entry()
            if __entry_seen is None:
                __entry_seen = entry
            elif entry != __entry_seen:
                if entry == __entry_pending:
                    withdraw()
                    return RELOADED
                __entry_pending = entry
            else:
                __entry_pending = None

    return event
