# The board's own mount of the drive, and the shipped files it heals onto it

import errno
import os
import rp2
import sys
import vfs

import fx_defaults

from .fat import ENOTDIR, S_IFDIR
from .pages import pages, write_page

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

# What the board told mount() it has, for the remount when the computer hands the drive back
__screens = True
__wireless = False
__sound = True


def __ends(text):
    # A document's length and the two ends __holds() compares, the whole of a short one
    if len(text) <= __READ_TO_END:
        return len(text), text, ""
    return len(text), text[:__EDGE], text[-__EDGE:]


def __holds(path, size, head, tail):
    # Whether the file is size long, starting with head and ending with tail. Size first, so
    # a missing or half-written file answers without a read. A long document is met at both
    # ends, since reading the manual to the end took 424ms per mount on a Mighty FX against
    # 40ms for its ends, and every mount and button press would pay it. A page that changed
    # only in its middle at the same length would pass, so the build tools end every page
    # with a hash of its content. Every document is ASCII, enforced by the build tools, so its
    # length in characters is in bytes
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
                write_page(document, f)
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
    # save. macOS writes a ._ sidecar beside every file it touches, and its log folder and
    # its bin each have a sweep of their own. Names are listed as bytes, since listed as str
    # one name outside ASCII raises UnicodeError for the whole listing, and the drive would
    # never be shown
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
    # Make the files that ask macOS not to write to the drive, where they are missing. Each
    # write macOS makes after a save holds back the save watcher, so a save plays later on
    # a Mac. A full drive goes without them, and macOS writes to it as it did before
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


def mount(screens=True, wireless=False, sound=True):
    """
    Mount the drive read-write at /fx, rebuilding it when the filesystem is blank,
    effects.txt is missing, or any shipped document differs from the text the board
    carries. Returns whether the drive ended up mounted.

    `screens` is False for a board found to have no screen ports, which is then given
    the catalogue without them where its pages carry one, and no pictures or drawings
    folder. `wireless` is True for a board with a wireless module, which is given the
    WiFi credentials. `sound` is False for a board that cannot play sound, which is given
    no sounds folder.
    """
    global __screens, __wireless, __sound
    __screens, __wireless, __sound = screens, wireless, sound
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
    __make_folders(screens, sound)
    del __unhealed[:]
    __heal(fs, README_NAME, fx_defaults.README)
    for name, document in pages(screens):
        __heal(fs, name, document)
    __sweep_host_litter()
    __mark_for_mac(fs)
    return True


def remount():
    """Mount again with what the board last told mount()."""
    return mount(__screens, __wireless, __sound)


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


def __make_folders(screens, sound):
    # Make the folders the user's own files go in where the drive has none, so it shows where
    # each belongs, only for parts the board has. One already there is left as it is
    folders = ["programs"]
    if screens:
        folders += ["pictures", "drawings"]
    if sound:
        folders.append("sounds")
    for folder in folders:
        try:
            os.mkdir(MOUNT_POINT + "/" + folder)
        except OSError:
            # Already there, or a full drive, where the picker makes it as a file is added
            pass


def __mount_examples():
    # Mount the examples folder at /examples, once, staying through every handover
    try:
        vfs.mount(Examples(), EXAMPLES_MOUNT_POINT)
    except OSError as e:
        # Already mounted answers EPERM
        if e.args[0] != errno.EPERM:
            raise
