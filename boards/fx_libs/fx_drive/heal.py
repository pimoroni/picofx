# The board mounts the drive for itself here, and puts back the shipped files it carries

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
__ATTR_HIDDEN = 0x02
__ATTR_SYSTEM = 0x04

# The folder macOS logs the drive's changes in, writing to it after every save. A file named
# no_log inside it asks macOS to keep no log
__MAC_LOG_FOLDER = ".fseventsd"
__NO_LOG = b"no_log"

# The name of macOS's bin on the drive. A file of this name leaves macOS nowhere to keep one,
# so Finder asks first and then deletes a file at once. A bin kept on a drive this small
# fills it with files the user believes are gone
__MAC_BIN = ".Trashes"

# The empty files __mark_for_mac() makes, as paths from the drive's root. .metadata_never_index
# asks Spotlight not to index the drive, which it otherwise does after a save
__MAC_MARKERS = (".metadata_never_index", __MAC_LOG_FOLDER + "/no_log", __MAC_BIN)

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
    # Check if the document fits. One that does not is left stale and whole, since opening
    # it for write would truncate it before failing
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
    # Remove what a computer leaves in the drive's root that the board has no use for, such
    # as an unfinished Chromium save (.crswap) or a macOS ._ sidecar
    #
    # Names are listed as bytes, as one non-ASCII name makes a str listing raise UnicodeError
    root = MOUNT_POINT.encode()
    for name in os.listdir(root):
        lower = name.lower()
        if lower == __MAC_LOG_FOLDER.encode():
            __sweep_mac_log(root + b"/" + name)
        elif lower == __MAC_BIN.lower().encode():
            __sweep_mac_bin(root + b"/" + name)
        elif lower.endswith(b".crswap") or name.startswith(b"._"):
            __remove_tree(root + b"/" + name)


def __sweep_mac_log(path):
    # Remove macOS's log of the drive's changes. A .fseventsd holding no_log is the one
    # __mark_for_mac() made, so it stays and only what else is in it goes
    try:
        names = os.listdir(path)
    except OSError:
        # A file of that name stops the folder being made, so it goes
        __remove_tree(path)
        return
    # Is this macOS's own log, holding no no_log?
    if __NO_LOG not in [name.lower() for name in names]:
        # It goes whole, and __mark_for_mac() makes the board's in its place
        __remove_tree(path)
        return
    for name in names:
        if name.lower() != __NO_LOG:
            __remove_tree(path + b"/" + name)


def __holds_files(path):
    # Whether a folder has a file anywhere in it, searching the folders inside it too. A ._
    # sidecar holds only macOS's metadata and does not count. A folder that cannot be read
    # answers True, so it is never taken for empty
    try:
        for name in os.listdir(path):
            if name.startswith(b"._"):
                continue
            inner = path + b"/" + name
            if not os.stat(inner)[0] & S_IFDIR or __holds_files(inner):
                return True
    except OSError:
        return True
    return False


def __sweep_mac_bin(path):
    # Remove macOS's bin once no file is left in it, so __mark_for_mac() can put its file
    # there. An emptied bin still holds a folder for each user, so only files count. A bin
    # holding files is the user's to empty or restore from, and is left alone
    try:
        # Is it already the board's file?
        if not os.stat(path)[0] & S_IFDIR:
            return
    except OSError:
        return
    if not __holds_files(path):
        __remove_tree(path)


def __mark_for_mac(fs):
    # Make the files that ask macOS not to write to the drive, where they are missing. Its
    # writes after a save hold up a reload. A full drive goes without them
    made = []
    try:
        os.mkdir(MOUNT_POINT + "/" + __MAC_LOG_FOLDER)
        made.append(__MAC_LOG_FOLDER)
    except OSError:
        # Already there, or a full drive
        pass
    for name in __MAC_MARKERS:
        path = MOUNT_POINT + "/" + name
        try:
            os.stat(path)
            continue
        except OSError:
            pass
        try:
            with open(path, "w"):
                pass
            made.append(name)
        except OSError:
            # A full drive, or a .fseventsd that could not be made
            pass
    # Hide what this mount made. Hidden and system together keep a name out of Windows
    # Explorer even where it shows hidden files. Setting them rewrites the directory entry
    # whether or not they change, so a file that was already there is left as it is
    for name in made:
        try:
            # A path from the volume's root, as a program may have changed the current folder
            fs.chmod("/" + name, __ATTR_HIDDEN | __ATTR_SYSTEM, __ATTR_HIDDEN | __ATTR_SYSTEM)
        except OSError:
            pass


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
        # Is the drive already mounted? That answers EPERM, and anything other than a blank
        # volume is raised rather than papered over with a reformat
        if e.args[0] == errno.EPERM:
            return True
        if e.args[0] != errno.ENODEV:
            raise
        # Has the volume been formatted before? Then it is damaged, not blank, and is left for
        # the computer to repair rather than formatted over the user's files
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
        # The drive's modules, such as secrets.py, import after the board's own
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
    __mark_for_mac(fs)
    return True


def remount():
    """Mount again with what the board last told mount()."""
    return mount(__wireless)


class Examples:
    """
    The drive's examples folder, mounted at /examples so an example finds its files by
    the same path on every board. A board without a drive keeps the folder on its own
    filesystem. Each call is passed on to whatever is mounted at /fx, the board's own
    mount or the view, and answers as that does.
    """

    def __init__(self):
        self.__cwd = ""

    def __target(self, path):
        path = path if path.startswith("/") else self.__cwd + "/" + path
        return (EXAMPLES_DIR + path).rstrip("/")

    def mount(self, readonly, mkfs):
        # vfs.mount() calls this, and there is nothing to set up
        pass

    def umount(self):
        # vfs.umount() calls this, and there is nothing to release
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
            # A full drive. The empty file a failed write leaves would stop the next mount
            # restoring the template, so it is removed
            try:
                os.remove(SECRETS_PATH)
            except OSError:
                pass


def __mount_examples():
    # Mount the examples folder at /examples, once, staying through every handover
    try:
        vfs.mount(Examples(), EXAMPLES_MOUNT_POINT)
    except OSError as e:
        # Is it already mounted? That answers EPERM
        if e.args[0] != errno.EPERM:
            raise
