# The board's own mount of the drive, and the shipped files it heals onto it

import errno
import os
import rp2
import sys
import vfs

import fx_defaults

from .fat import ENOTDIR, S_IFDIR

MOUNT_POINT = "/fx"
FILE_PATH = MOUNT_POINT + "/effects.txt"
README_NAME = "README.txt"
SECRETS_PATH = MOUNT_POINT + "/secrets.py"

# The drive's examples folder, and where it is also mounted
EXAMPLES_DIR = MOUNT_POINT + "/examples"
EXAMPLES_MOUNT_POINT = "/examples"

VOLUME_LABEL = "FX"

# FAT attribute bits, per VfsFat.chmod.
__ATTR_READ_ONLY = 0x01

# What the board told mount() it has, for the remount when the computer hands the drive back
__wireless = False


def __holds(path, text):
    # Whether the file holds exactly the text. Size first, so a missing or half-written file
    # answers without a read. Every document is ASCII, so its length in characters is in bytes
    try:
        if os.stat(path)[6] != len(text):
            return False
        with open(path) as f:
            return f.read() == text
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
    # Put a shipped file back on the drive, unless it is already there
    path = MOUNT_POINT + "/" + name
    if __holds(path, document):
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
        if room < len(document):
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
        with open(path, "w") as f:
            f.write(document)
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
        if os.stat(path)[0] & S_IFDIR:
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


def mount(wireless=False):
    """
    Mount the drive read-write at /fx, rebuilding it when the filesystem is blank,
    effects.txt is missing, or any shipped document differs from the text the board
    carries. Returns whether the drive ended up mounted.

    `wireless` is True for a board with a wireless module, which is given the WiFi
    credentials.
    """
    global __wireless
    __wireless = wireless
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
    __sweep_host_litter()
    return True


def remount():
    """Mount again with what the board last told mount()."""
    return mount(__wireless)


class Examples:
    """
    The drive's examples folder, mounted at /examples so an example finds its files by
    the same path on every board, those without a drive keeping the folder on their
    own filesystem. Each call is passed on to whatever is mounted at the mount point,
    the board's own mount or the view, and answers as that does
    """

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
        if not os.stat(target)[0] & S_IFDIR:
            raise OSError(ENOTDIR)
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
        vfs.mount(Examples(), EXAMPLES_MOUNT_POINT)
    except OSError as e:
        # Already mounted answers EPERM
        if e.args[0] != errno.EPERM:
            raise
