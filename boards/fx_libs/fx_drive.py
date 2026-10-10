"""
The FX drive: a small FAT partition holding effects.txt, editable from a connected
computer over USB mass storage, and room for the assets a program reads. The mount
is read-write whenever the board holds the drive, and released while the computer
does, so the two writers can never meet. While the computer holds it, the mount
point is a read-only view read straight from the flash, so a program still finds
its files there.

The drive is shown at boot and controlled by the button from then on: a double press
of the button passed to service() shows or hides it, and hiding it, or ejecting it on
the computer, re-reads the file. An eject does not show it again.
"""

import binascii
import deflate
import errno
import io
import machine
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
EDITOR_NAME = "EDITOR.html"
CATALOGUE_NAME = "catalogue.js"
ERRORS_PATH = MOUNT_POINT + "/errors.txt"

# The drive's examples folder, and where it is also mounted
EXAMPLES_DIR = MOUNT_POINT + "/examples"
EXAMPLES_MOUNT_POINT = "/examples"

VOLUME_LABEL = "FX"

# The stat modes of a folder and a file
__S_IFDIR = 0x4000
__S_IFREG = 0x8000

# The error numbers VfsFat gives these, which MicroPython's errno does not name
__ENOTDIR = 20
__EROFS = 30

# How much of a shipped document is compared. Anything shorter is read to the end;
# anything longer is met at both ends, measured at 40ms against 424ms for a mount.
__READ_TO_END = 4096
__EDGE = 512

# How much of a packed page is inflated onto the drive at a time
__INFLATE_CHUNK = 4096

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

# How long the board stays off the bus before rejoining, on the second reload and after.
# The first activation of the runtime USB device disconnects and reconnects by itself,
# with the 50ms hold TinyUSB applies, so only a later expose() waits here. Measured
# working on macOS 15.5 and Windows 11 at this value; not tried lower.
__OFF_BUS_MS = 500

# How long after a bus reset the computer may take to enumerate the board before
# enumerating() gives up on it, so a host that never configures it cannot keep the
# effects standing aside for good
ENUMERATION_LIMIT_MS = 3000

# How often the save watcher compares effects.txt's directory entry while the
# computer holds the drive. Every kind of save updates the entry, where copying
# other files onto the drive never does, so this is what "the file was saved"
# looks like from the board. A change must be seen on two polls in a row before
# it counts, so a half-finished save or a read torn by a host write cannot act.
WATCH_POLL_MS = 500

__exposed = False
__was_pressed = False
__last_edge = None
__withdrawn = False
__watching = False
__entry_seen = None
__entry_pending = None
__watch_at = None
__watch_buffer = None
__reset_at = None
__on_reset = None
__save_timer = None


def __ends(text):
    """A document's length and the two ends __holds() compares, the whole of a short one."""
    if len(text) <= __READ_TO_END:
        return len(text), text, ""
    return len(text), text[:__EDGE], text[-__EDGE:]


def __holds(path, size, head, tail):
    """Whether the file is size long, starting with head and ending with tail.

    Size first, so a missing or half-written file answers without a read. A long
    document is met at both ends, since reading the manual to the end costs about
    400ms on this volume and every mount and every button press would pay it. What
    that trades away is a rebuilt document differing only in its middle at exactly the
    same length, which nothing here produces. Every document is ASCII, which the build
    tools enforce, so a length in characters is a length in bytes.
    """
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


def __inflate(packed, f):
    """Write a zlib stream to the open file, a chunk at a time."""
    # BytesIO reads a frozen bytes object in place, where a read() of the whole
    # stream would put the page on the heap
    stream = deflate.DeflateIO(io.BytesIO(packed), deflate.ZLIB)
    chunk = bytearray(__INFLATE_CHUNK)
    while True:
        count = stream.readinto(chunk)
        if not count:
            return
        f.write(memoryview(chunk)[:count])


def __encode(packed, f):
    """Write a zlib stream to the open file as base64, a chunk at a time."""
    # A multiple of three bytes encodes without padding, so the chunks join up
    step = __INFLATE_CHUNK // 4 * 3
    view = memoryview(packed)
    for at in range(0, len(packed), step):
        f.write(binascii.b2a_base64(view[at:at + step], newline=False))


# The shipped documents the last mount left stale for want of room, for autofx to
# say beside the file's own problems: a console line reaches nobody with only the
# drive in front of them
__unhealed = []


def unhealed():
    """The shipped documents the last mount could not bring up to date."""
    return tuple(__unhealed)


def __heal(fs, name, document):
    """Put a shipped file back on the drive, unless it is already there.

    The document is its text, or a packed page from fx_editor, which is its length,
    its two ends and its zlib stream. A packed page may also carry the opening and
    closing of a page that inflates itself in the browser, and is then written as
    those around its stream in base64, the length and ends being that page's.
    """
    path = MOUNT_POINT + "/" + name
    packed = None
    opening = closing = None
    if isinstance(document, str):
        size, head, tail = __ends(document)
    elif len(document) == 6:
        size, head, tail, packed, opening, closing = document
    else:
        size, head, tail, packed = document
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
        with open(path, "w" if packed is None else "wb") as f:
            if packed is None:
                f.write(document)
            elif opening is None:
                __inflate(packed, f)
            else:
                f.write(opening)
                __encode(packed, f)
                f.write(closing)
        fs.chmod(name, __ATTR_READ_ONLY, __ATTR_READ_ONLY)
    except OSError:
        # A full drive has nowhere to put it. The board comes up regardless, since a
        # missing document costs a reader nothing and a dead board costs them
        # everything. A part-written file is left for the next mount to finish
        print("the FX drive is full, so {} could not be rebuilt".format(name))
        __unhealed.append(name)


def __remove_tree(path):
    """Remove a file, or a directory and everything in it, ignoring what will not go."""
    try:
        if os.stat(path)[0] & 0x4000:
            for name in os.listdir(path):
                __remove_tree(path + b"/" + name)
            os.rmdir(path)
        else:
            os.remove(path)
    except OSError:
        pass


def __sweep_host_litter():
    """
    Remove what a computer leaves on the drive that the board has no use for.

    Chromium writes a save through a .crswap beside the file and renames on close,
    so one still present is a save the drive left with, unfinished by definition.
    macOS writes a ._ sidecar beside every file it touches and a .fseventsd
    directory at the root, neither of which anything here reads.

    Names are listed as bytes, undecoded. Listed as str, one name outside ASCII can
    raise UnicodeError for the whole listing, and the drive would never be shown.
    """
    root = MOUNT_POINT.encode()
    for name in os.listdir(root):
        lower = name.lower()
        if lower.endswith(b".crswap") or name.startswith(b"._") or lower == b".fseventsd":
            __remove_tree(root + b"/" + name)


def __has_boot_signature(bdev):
    """Whether sector zero still ends 0x55 0xAA, so something formatted this once."""
    sector = bytearray(512)
    try:
        bdev.readblocks(0, sector)
    except OSError:
        return False
    return sector[510] == 0x55 and sector[511] == 0xAA


def mount(screens=True):
    """
    Mount the drive read-write at /fx, rebuilding it when the filesystem is blank,
    effects.txt is missing, or either shipped document differs from the text the
    board carries. Returns whether the drive ended up mounted.

    `screens` is False for a board found to have no screen ports, which is then given
    the catalogue without them where its pages carry one.
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
    __mount_examples()
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
    del __unhealed[:]
    __heal(fs, README_NAME, fx_defaults.README)
    __heal(fs, MANUAL_NAME, fx_manual.MANUAL)
    __heal(fs, PICKER_NAME, fx_editor.PICKER)
    __heal(fs, EDITOR_NAME, fx_editor.EDITOR)
    catalogue = fx_editor.CATALOGUE
    if not screens:
        catalogue = getattr(fx_editor, "CATALOGUE_WITHOUT_SCREENS", catalogue)
    __heal(fs, CATALOGUE_NAME, catalogue)
    __sweep_host_litter()
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


class __FatReader:
    """
    The drive's FAT12 or FAT16 tables and folders, read straight from its flash
    with no FatFs involved, so they read on while the computer holds the drive.
    """

    # FAT directory entries and the attribute bits read from them
    __ENTRY_SIZE = 32
    __ATTR_VOLUME_ID = 0x08
    __ATTR_DIRECTORY = 0x10
    __ATTR_LONG_NAME = 0x0F
    __ATTR_LONG_NAME_MASK = 0x3F

    # Where a long name's characters sit in each of its entries, two bytes apiece
    __LONG_NAME_SPANS = ((1, 11), (14, 26), (28, 32))

    def __init__(self):
        self.__flash = rp2.Flash(msc=True)
        self.__read_layout()

    def __read(self, offset, length):
        data = bytearray(length)
        self.__flash.readblocks(0, data, offset)
        return data

    @staticmethod
    def __u16(data, at):
        return data[at] | (data[at + 1] << 8)

    @staticmethod
    def __u32(data, at):
        return data[at] | (data[at + 1] << 8) | (data[at + 2] << 16) | (data[at + 3] << 24)

    def __read_layout(self):
        boot = self.__read(0, 36)
        if self.__read(510, 2) != b"\x55\xaa":
            raise OSError(errno.ENODEV)
        sector = self.__u16(boot, 11)
        per_cluster = boot[13]
        reserved = self.__u16(boot, 14)
        fats = boot[16]
        root_entries = self.__u16(boot, 17)
        total = self.__u16(boot, 19) or self.__u32(boot, 32)
        fat_sectors = self.__u16(boot, 22)

        # FAT32 keeps neither a fixed root directory nor a 16-bit table size
        if not (sector and per_cluster and root_entries and fat_sectors):
            raise OSError(errno.ENODEV)

        root_sectors = (root_entries * self.__ENTRY_SIZE + sector - 1) // sector
        self.__fat_at = reserved * sector
        self.__root_at = (reserved + fats * fat_sectors) * sector
        self.__root_bytes = root_entries * self.__ENTRY_SIZE
        self.__data_at = self.__root_at + root_sectors * sector
        self.__cluster_bytes = sector * per_cluster
        self.__clusters = (total - reserved - fats * fat_sectors - root_sectors) // per_cluster

        # The cluster count alone decides the table's width
        if self.__clusters >= 65525:
            raise OSError(errno.ENODEV)
        self.__fat12 = self.__clusters < 4085
        self.__end_of_chain = 0xFF8 if self.__fat12 else 0xFFF8

    def __next_cluster(self, cluster):
        if self.__fat12:
            # Twelve bits an entry, so two entries share every three bytes
            pair = self.__read(self.__fat_at + cluster + cluster // 2, 2)
            value = self.__u16(pair, 0)
            return value >> 4 if cluster & 1 else value & 0xFFF
        return self.__u16(self.__read(self.__fat_at + cluster * 2, 2), 0)

    def __first_cluster(self, entry):
        return self.__u16(entry, 26)

    def __runs_from(self, cluster, size=None):
        """
        A cluster chain as runs of contiguous flash, each (position in the file, offset
        on the drive, length). Without a size the chain is followed to its end, as a
        directory's is. A chain leaving the volume, looping or ending early raises.
        """
        runs = []
        position = 0
        steps = 0
        while size is None or position < size:
            if size is None and cluster >= self.__end_of_chain:
                break
            if not 2 <= cluster < self.__clusters + 2 or steps > self.__clusters:
                raise OSError(errno.EIO)
            at = self.__data_at + (cluster - 2) * self.__cluster_bytes
            length = self.__cluster_bytes if size is None else min(self.__cluster_bytes,
                                                                   size - position)
            if runs and runs[-1][1] + runs[-1][2] == at:
                last = runs[-1]
                runs[-1] = (last[0], last[1], last[2] + length)
            else:
                runs.append((position, at, length))
            position += length
            cluster = self.__next_cluster(cluster)
            steps += 1
        return runs

    @staticmethod
    def __checksum(entry):
        total = 0
        for byte in entry[:11]:
            total = (((total & 1) << 7) + (total >> 1) + byte) & 0xFF
        return total

    def __long_name_part(self, entry):
        """A long name entry's characters, or None where one is beyond what chr() takes."""
        part = ""
        for start, end in self.__LONG_NAME_SPANS:
            for at in range(start, end, 2):
                code = self.__u16(entry, at)
                if code == 0x0000 or code == 0xFFFF:
                    return part
                # Half of a surrogate pair
                if 0xD800 <= code <= 0xDFFF:
                    return None
                part += chr(code)
        return part

    @staticmethod
    def __short_name(entry):
        base = bytes(entry[:8]).rstrip(b" ")
        extension = bytes(entry[8:11]).rstrip(b" ")
        if base[:1] == b"\x05":
            base = b"\xe5" + base[1:]
        # A lowercase 8.3 name is stored in capitals with these flags, and no long name
        if entry[12] & 0x08:
            base = base.lower()
        if entry[12] & 0x10:
            extension = extension.lower()
        try:
            name = base.decode()
            return name + "." + extension.decode() if extension else name
        except UnicodeError:
            return None

    def __entries(self, runs):
        """
        Each entry in a directory as its drive offset, its bytes and its long name,
        None where it has none. Deleted entries and the volume label are left out.
        """
        parts = None
        checksum = None
        for _, start, length in runs:
            for at in range(start, start + length, self.__ENTRY_SIZE):
                entry = self.__read(at, self.__ENTRY_SIZE)
                first = entry[0]
                if first == 0x00:
                    return
                if first == 0xE5:
                    parts = None
                    continue

                attributes = entry[11]
                if attributes & self.__ATTR_LONG_NAME_MASK == self.__ATTR_LONG_NAME:
                    # Stored last part first, the first stored carrying 0x40
                    if first & 0x40:
                        parts = {}
                        checksum = entry[13]
                    if parts is not None and entry[13] == checksum:
                        parts[first & 0x1F] = self.__long_name_part(entry)
                    else:
                        parts = None
                    continue

                long_name = None
                # A long name belongs to the short entry after it only where the
                # checksum matches, so one orphaned by a host without long names is
                # not taken for this file's
                if parts and None not in parts.values() and \
                        sorted(parts) == list(range(1, len(parts) + 1)) and \
                        checksum == self.__checksum(entry):
                    long_name = "".join(parts[order] for order in sorted(parts))
                parts = None

                if attributes & self.__ATTR_VOLUME_ID:
                    continue
                yield at, entry, long_name

    def __find_in(self, runs, wanted):
        """
        The drive offset and bytes of the entry named `wanted` in a directory, matched
        by its long name or its short one, ASCII case ignored. None where it is absent.
        """
        for at, entry, long_name in self.__entries(runs):
            for name in (long_name, self.__short_name(entry)):
                if name is not None and name.lower() == wanted:
                    return at, entry
        return None

    def __find(self, name, directory=False):
        """
        The drive offset and bytes of the entry a path leads to, through any folders.
        `directory` says what the last part must be, None taking either.
        """
        runs =[(0, self.__root_at, self.__root_bytes)]
        parts = [part for part in name.split("/") if part]
        if not parts or ".." in parts:
            raise OSError(errno.ENOENT)
        for depth, part in enumerate(parts):
            if part == ".":
                continue
            found = self.__find_in(runs, part.lower())
            if found is None:
                raise OSError(errno.ENOENT)
            at, entry = found
            last = depth == len(parts) - 1
            # Every part before the last is a folder
            wanted = directory if last else True
            if wanted is not None and bool(entry[11] & self.__ATTR_DIRECTORY) != wanted:
                raise OSError(errno.ENOENT)
            if not last:
                runs = self.__runs_from(self.__first_cluster(entry))
        return at, entry

    @staticmethod
    def __is_root(path):
        return not [part for part in path.split("/") if part and part != "."]

    def __runs_of_directory(self, path):
        """Where a folder's entries sit, the root being a fixed region before the data."""
        if self.__is_root(path):
            return [(0, self.__root_at, self.__root_bytes)]
        _, entry = self.__find(path, directory=True)
        return self.__runs_from(self.__first_cluster(entry))

    def kind(self, path):
        """The stat mode and size of what a path names."""
        if self.__is_root(path):
            return __S_IFDIR, 0
        _, entry = self.__find(path, directory=None)
        if entry[11] & self.__ATTR_DIRECTORY:
            return __S_IFDIR, 0
        return __S_IFREG, self.__u32(entry, 28)

    def listing(self, path):
        """A folder's contents as (name, stat mode, size), its own . and .. left out."""
        listed = []
        for _, entry, long_name in self.__entries(self.__runs_of_directory(path)):
            name = long_name or self.__short_name(entry)
            if name is None or name in (".", ".."):
                continue
            if entry[11] & self.__ATTR_DIRECTORY:
                listed.append((name, __S_IFDIR, 0))
            else:
                listed.append((name, __S_IFREG, self.__u32(entry, 28)))
        return listed

    def capacity(self):
        """The cluster size and count, which is what statvfs() reports."""
        return self.__cluster_bytes, self.__clusters


class Stream(__FatReader):
    """
    A file on the drive read straight from its flash, which reads on while the
    computer holds the drive. The board's mount is released at every handover and
    a file opened through it goes stale, so this finds the file's clusters once,
    from the tables on the flash, and reads them directly from then on.

    Read-only, and blind to the computer rewriting the file, which reads as whatever
    then fills its clusters. changed() says when that has happened.
    """

    def __init__(self, name):
        super().__init__()
        self.__entry_at, self.__entry = self.__find(name)
        self.size = self.__u32(self.__entry, 28)
        self.__runs = self.__runs_from(self.__first_cluster(self.__entry), self.size)
        self.__position = 0
        self.__run = 0

    @staticmethod
    def __identity(entry):
        # The name, attributes, write time, first cluster and size. Reading the file
        # can move its access date, which is left out
        return bytes(entry[:12]) + bytes(entry[20:32])

    def changed(self):
        """Whether the computer has rewritten, moved or deleted the file since it was opened."""
        try:
            entry = self.__read(self.__entry_at, self.__ENTRY_SIZE)
            if self.__identity(entry) != self.__identity(self.__entry):
                return True
            return self.__runs_from(self.__first_cluster(entry), self.size) != self.__runs
        except OSError:
            return True

    def __run_holding(self, position):
        # Reads run forwards, so the run last read from, or the next, almost always holds it
        runs = self.__runs
        index = self.__run
        if not runs[index][0] <= position < runs[index][0] + runs[index][2]:
            index = 0
            while position >= runs[index][0] + runs[index][2]:
                index += 1
        self.__run = index
        return runs[index]

    def readinto(self, buffer):
        if self.__runs is None:
            raise OSError(errno.EBADF)
        view = memoryview(buffer)
        wanted = max(0, min(len(view), self.size - self.__position))
        done = 0
        while done < wanted:
            start, at, length = self.__run_holding(self.__position)
            into = self.__position - start
            count = min(length - into, wanted - done)
            self.__flash.readblocks(0, view[done:done + count], at + into)
            done += count
            self.__position += count
        return done

    def read(self, size=-1):
        remaining = max(0, self.size - self.__position)
        data = bytearray(remaining if size < 0 else min(size, remaining))
        self.readinto(data)
        return bytes(data)

    def seek(self, offset, whence=0):
        if whence == 1:
            offset += self.__position
        elif whence == 2:
            offset += self.size
        self.__position = max(0, offset)
        return self.__position

    def tell(self):
        return self.__position

    def close(self):
        self.__runs = None

    def extents(self):
        """The file's runs of contiguous flash, each (position in the file, offset on the drive, length)."""
        return self.__runs


def stream(name):
    """
    Open a file on the drive for reading in a form that reads on while the computer
    holds the drive. None where it cannot be found that way, which leaves the mount to
    answer, and a file the computer then takes will not read on. That is a name
    differing in case beyond ASCII, a path through "..", or a volume the computer
    reformatted as something other than FAT12 or FAT16.
    """
    try:
        return Stream(name)
    except OSError:
        return None


# What a read raises once the computer has written to the drive since its file was opened
__CHANGED_BENEATH = "the FX drive changed while this file was being read"


class __View:
    """
    The drive read straight from its flash, mounted at the mount point while the
    computer holds the drive so a program still finds its files by path. Read-only.
    Finding a file waits while the computer writes, and a file read once it writes
    raises OSError.
    """

    def __init__(self):
        self.__cwd = ""

    def __resolve(self, path):
        return path if path.startswith("/") else self.__cwd + "/" + path

    @staticmethod
    def __settled(lookup, path):
        # Looks again where a write landed during the lookup, since nothing it found has
        # reached the program yet. Returns what it found and the write count it holds for
        while True:
            while rp2.is_msc_busy():
                time.sleep_ms(10)
            writes = rp2.msc_write_count()
            try:
                found = lookup(path)
            except OSError:
                if rp2.msc_write_count() == writes:
                    raise
                continue
            if rp2.msc_write_count() == writes:
                return found, writes

    def mount(self, readonly, mkfs):
        pass

    def umount(self):
        pass

    def open(self, path, mode):
        if "w" in mode or "a" in mode or "x" in mode or "+" in mode:
            raise OSError(__EROFS)
        stream, writes = self.__settled(Stream, self.__resolve(path))
        # Read in C, every read checking the write count against this one
        return rp2.MSCFile(stream.extents(), stream.size, writes, text="b" not in mode,
                           message=__CHANGED_BENEATH)

    def stat(self, path):
        (mode, size), _ = self.__settled(lambda name: __FatReader().kind(name), self.__resolve(path))
        return (mode, 0, 0, 0, 0, 0, size, 0, 0, 0)

    def ilistdir(self, path):
        listed, _ = self.__settled(lambda name: __FatReader().listing(name), self.__resolve(path))
        return iter([(name, mode, 0, size) for name, mode, size in listed])

    def statvfs(self, _path):
        cluster_bytes, clusters = __FatReader().capacity()
        return (cluster_bytes, cluster_bytes, clusters, 0, 0, 0, 0, 0, 0, 255)

    def chdir(self, path):
        path = self.__resolve(path)
        if self.__settled(lambda name: __FatReader().kind(name), path)[0][0] != __S_IFDIR:
            raise OSError(__ENOTDIR)
        self.__cwd = "/" + "/".join(part for part in path.split("/") if part)
        if self.__cwd == "/":
            self.__cwd = ""

    def getcwd(self):
        return self.__cwd or "/"

    def mkdir(self, _path):
        raise OSError(__EROFS)

    def remove(self, _path):
        raise OSError(__EROFS)

    def rename(self, _old_path, _new_path):
        raise OSError(__EROFS)

    def rmdir(self, _path):
        raise OSError(__EROFS)


class __Examples:
    """
    The drive's examples folder, mounted at /examples so an example finds its files by
    the same path on every board, those without a drive keeping the folder on their
    own filesystem. Each call is passed on to whatever is mounted at the mount point,
    the board's own mount or the view, and answers as that does.
    """

    def __init__(self):
        self.__cwd = ""

    def __target(self, path):
        path = path if path.startswith("/") else self.__cwd + "/" + path
        return (EXAMPLES_DIR + path).rstrip("/")

    def mount(self, readonly, mkfs):
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


def __mount_examples():
    """Mount the examples folder at /examples, once, staying through every handover."""
    try:
        vfs.mount(__Examples(), EXAMPLES_MOUNT_POINT)
    except OSError as e:
        # Already mounted answers EPERM
        if e.args[0] != errno.EPERM:
            raise


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


def __entry_settled():
    """
    Whether effects.txt's directory entry has changed and read the same on two
    looks in a row, so a save has landed. Each call is one look.
    """
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
    """The save watcher for while nothing calls service(), run by reset_on_save()."""
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
    Whether a save that watch() would answer resets the board instead, for a caller
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
    Whether the computer is mid-transfer. Worth standing aside for: a transfer costs
    a running effect most of a tenth of a second in one hitch, which reads as a lurch.
    """
    return __exposed and rp2.is_msc_busy()


def enumerating():
    """
    Whether the computer is still enumerating the board after a bus reset.

    Enumeration's replies are due within tens of milliseconds, and the board answers
    them between other scheduled work, so anything busy on the board stands aside
    until it is over. A reset can come at any time: a rejoin, the computer waking, or
    a port it reset after an error.
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
    global __reset_at
    __reset_at = time.ticks_ms()
    if __on_reset is not None:
        __on_reset()


def __rejoin_bus():
    """
    Leave the USB bus and return, so the computer enumerates the board afresh.

    A computer that missed the media leaving keeps serving its old view of the volume
    and fails every read that reaches the device, and nothing on its side recovers.
    Leaving the bus it cannot miss. The serial console drops and returns with it, and
    macOS reports the drive as not ejected properly, which is true.
    """
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
    back. Effects run from a timer and carry on through the rejoin; anything the
    caller drives itself, a screen being the one, holds its last frame.
    """
    global __exposed, __withdrawn
    if __exposed:
        return False
    rejoin = __withdrawn
    __withdrawn = False
    try:
        vfs.umount(MOUNT_POINT)
    except OSError:
        pass
    rp2.enable_msc()
    try:
        vfs.mount(__View(), MOUNT_POINT)
    except OSError:
        pass                # Still in use, which leaves a program without the drive's files
    if rejoin:
        __rejoin_bus()
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
    global __exposed, __withdrawn
    if not __exposed:
        return False
    deadline = time.ticks_add(time.ticks_ms(), SETTLE_MS)
    while rp2.is_msc_busy() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        time.sleep_ms(50)
    rp2.disable_msc()
    __exposed = False
    __withdrawn = True
    # The view goes first, since mount() takes a mount point already in use as done
    try:
        vfs.umount(MOUNT_POINT)
    except OSError:
        pass
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
        global __watch_at, __entry_pending
        if rp2.is_msc_busy():
            # A save may still be in flight, so nothing seen counts yet
            __entry_pending = None
        elif __watch_at is None or time.ticks_diff(now, __watch_at) >= WATCH_POLL_MS:
            __watch_at = now
            if __entry_settled():
                withdraw()
                return RELOADED

    return event
