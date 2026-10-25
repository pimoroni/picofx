# The drive's FAT read straight from its flash, as a reader, a stream and a view

import errno
import rp2
import time

# The stat modes of a folder and a file
S_IFDIR = 0x4000
S_IFREG = 0x8000

# The error numbers VfsFat gives these, which MicroPython's errno does not name
ENOTDIR = 20
EROFS = 30


class FatReader:
    # The drive's FAT12 or FAT16 tables and folders, read straight from its flash
    # with no FatFs involved, so they read on while the computer holds the drive

    # FAT directory entries and the attribute bits read from them
    __ENTRY_SIZE = 32
    __ATTR_VOLUME_ID = 0x08
    __ATTR_DIRECTORY = 0x10
    __ATTR_LONG_NAME = 0x0F
    __ATTR_LONG_NAME_MASK = 0x3F

    # Where a long name's characters sit in each of its entries, two bytes apiece
    __LONG_NAME_SPANS = ((1, 11), (14, 26), (28, 32))

    # How much of a folder or the table is read at once, sixteen entries of a folder. A sector
    # is a whole number of these, so a window never crosses into the next region
    __WINDOW = 512

    def __init__(self):
        self.__flash = rp2.Flash(msc=True)
        self.__fat_window = bytearray(self.__WINDOW)
        self.__fat_window_at = None
        self.__boot = bytearray(36)
        self.__signature = bytearray(2)
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
        boot = self.__boot
        self.__flash.readblocks(0, boot, 0)
        self.__flash.readblocks(0, self.__signature, 510)
        if self.__signature != b"\x55\xaa":
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

    def __fat_u16(self, offset):
        # The table's bytes come from the window holding them, read afresh only on leaving it
        into = offset % self.__WINDOW
        if into == self.__WINDOW - 1:
            # A FAT12 entry straddling two windows
            return self.__u16(self.__read(self.__fat_at + offset, 2), 0)
        window_at = offset - into
        if window_at != self.__fat_window_at:
            self.__flash.readblocks(0, self.__fat_window, self.__fat_at + window_at)
            self.__fat_window_at = window_at
        return self.__u16(self.__fat_window, into)

    def __next_cluster(self, cluster):
        if self.__fat12:
            # Twelve bits an entry, so two entries share every three bytes
            value = self.__fat_u16(cluster + cluster // 2)
            return value >> 4 if cluster & 1 else value & 0xFFF
        return self.__fat_u16(cluster * 2)

    def __first_cluster(self, entry):
        return self.__u16(entry, 26)

    def __runs_from(self, cluster, size=None):
        # A cluster chain as runs of contiguous flash, each (position in the file, offset
        # on the drive, length). Without a size the chain is followed to its end, as a
        # directory's is. A chain leaving the volume, looping or ending early raises
        runs = []
        position = 0
        steps = 0
        # The computer may have rewritten the table since the last walk
        self.__fat_window_at = None
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
        # The checksum of the 8.3 name that each of its long name entries carries
        total = 0
        for byte in entry[:11]:
            total = (((total & 1) << 7) + (total >> 1) + byte) & 0xFF
        return total

    def __long_name_part(self, entry):
        # A long name entry's UTF-16 units
        return b"".join(bytes(entry[start:end]) for start, end in self.__LONG_NAME_SPANS)

    @staticmethod
    def __cut(units):
        # A long name ends at its first zero unit, 0xFFFF filling the rest of its last entry
        end = units.find(b"\x00\x00")
        while end > 0 and end & 1:
            end = units.find(b"\x00\x00", end + 1)
        return units if end < 0 else units[:end]

    def __decoded(self, units):
        # A long name's UTF-16 units as text, or None where one is beyond what chr() takes
        name = ""
        for at in range(0, len(units), 2):
            code = self.__u16(units, at)
            # Half of a surrogate pair
            if 0xD800 <= code <= 0xDFFF:
                return None
            name += chr(code)
        return name

    @staticmethod
    def __units_of(text):
        # Text as the UTF-16 units a long name stores it in
        units = bytearray()
        for character in text:
            code = ord(character)
            if code <= 0xFFFF:
                halves = (code,)
            else:
                halves = (0xD800 + ((code - 0x10000) >> 10), 0xDC00 + ((code - 0x10000) & 0x3FF))
            for half in halves:
                units.append(half & 0xFF)
                units.append(half >> 8)
        return bytes(units)

    @staticmethod
    def __short_name(entry):
        base = bytes(entry[:8]).rstrip(b" ")
        extension = bytes(entry[8:11]).rstrip(b" ")
        # A name starting 0xE5 is stored as 0x05, since 0xE5 marks a deleted entry
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
        # Each entry in a directory as its drive offset, its bytes and its long name as
        # UTF-16 units, None where it has none. Deleted entries and the volume label are
        # left out
        parts = None
        checksum = None
        window = bytearray(self.__WINDOW)
        for _, start, length in runs:
            for at in range(start, start + length, self.__ENTRY_SIZE):
                into = (at - start) % self.__WINDOW
                if into == 0:
                    count = min(self.__WINDOW, start + length - at)
                    self.__flash.readblocks(0, memoryview(window)[:count], at)
                entry = window[into:into + self.__ENTRY_SIZE]
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
                if parts and sorted(parts) == list(range(1, len(parts) + 1)) and \
                        checksum == self.__checksum(entry):
                    long_name = self.__cut(b"".join(parts[order] for order in sorted(parts)))
                parts = None

                if attributes & self.__ATTR_VOLUME_ID:
                    continue
                yield at, entry, long_name

    @staticmethod
    def __ascii_lowered(units):
        # The units with A to Z lowered and every other unit as stored, as str.lower() lowers
        lowered = bytearray(units)
        for at in range(0, len(lowered), 2):
            if lowered[at + 1] == 0 and 0x41 <= lowered[at] <= 0x5A:
                lowered[at] += 0x20
        return lowered

    def __find_in(self, runs, wanted):
        # The drive offset and bytes of the entry named `wanted` in a directory, matched
        # by its long name or its short one, ASCII case ignored. None where it is absent

        # Long names are compared as stored, so none need be decoded. wanted arrives lowered,
        # and bytes.lower() is the quick test, but it also lowers bytes of units beyond ASCII,
        # so a long name it passes is confirmed unit by unit
        wanted_units = self.__units_of(wanted)
        quick_units = wanted_units.lower()
        # A short name is eight characters, a dot and three more at most
        could_be_short = len(wanted) <= 12
        for at, entry, long_name in self.__entries(runs):
            if long_name is not None and long_name.lower() == quick_units \
                    and self.__ascii_lowered(long_name) == wanted_units:
                return at, entry
            if could_be_short:
                short_name = self.__short_name(entry)
                if short_name is not None and short_name.lower() == wanted:
                    return at, entry
        return None

    def __find(self, name, directory=False):
        # The drive offset and bytes of the entry a path leads to, through any folders.
        # `directory` says what the last part must be, None taking either
        runs = [(0, self.__root_at, self.__root_bytes)]
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


class Lookup(FatReader):
    """
    A reader answering the view and the save watcher with what a path names, a folder's
    contents, the drive's capacity and one root entry's bytes.
    """

    def __init__(self):
        super().__init__()
        # Made by the first root_entry_bytes(), since only the save watcher calls it
        self.__probe = None
        self.__root_window = None

    @staticmethod
    def __is_root(path):
        return not [part for part in path.split("/") if part and part != "."]

    def __runs_of_directory(self, path):
        # Where a folder's entries sit, the root being a fixed region before the data
        if self.__is_root(path):
            return [(0, self.__root_at, self.__root_bytes)]
        _, entry = self.__find(path, directory=True)
        return self.__runs_from(self.__first_cluster(entry))

    def kind(self, path):
        """The stat mode and size of what a path names."""
        if self.__is_root(path):
            return S_IFDIR, 0
        _, entry = self.__find(path, directory=None)
        if entry[11] & self.__ATTR_DIRECTORY:
            return S_IFDIR, 0
        return S_IFREG, self.__u32(entry, 28)

    def listing(self, path):
        """A folder's contents as (name, stat mode, size), its own . and .. left out."""
        listed = []
        for _, entry, long_name in self.__entries(self.__runs_of_directory(path)):
            name = (self.__decoded(long_name) if long_name else None) or self.__short_name(entry)
            if name is None or name in (".", ".."):
                continue
            if entry[11] & self.__ATTR_DIRECTORY:
                listed.append((name, S_IFDIR, 0))
            else:
                listed.append((name, S_IFREG, self.__u32(entry, 28)))
        return listed

    def root_entry_bytes(self, short_name, start, end):
        """Bytes start to end of the root folder's entry with this 11-byte short name, or None."""
        flash = self.__flash
        if self.__root_window is None:
            self.__probe = bytearray(36)
            self.__root_window = bytearray(self.__WINDOW)

        # A reformat by the computer changes the boot sector's fields, so the layout is read again
        flash.readblocks(0, self.__probe, 0)
        flash.readblocks(0, self.__signature, 510)
        if self.__signature != b"\x55\xaa":
            return None
        if self.__probe != self.__boot:
            self.__read_layout()

        window = self.__root_window
        first, second = short_name[0], short_name[1]
        root_end = self.__root_at + self.__root_bytes
        for at in range(self.__root_at, root_end, self.__WINDOW):
            count = min(self.__WINDOW, root_end - at)
            flash.readblocks(0, window if count == self.__WINDOW else memoryview(window)[:count], at)
            for into in range(0, count, self.__ENTRY_SIZE):
                lead = window[into]
                if lead == 0x00:
                    return None
                # Two bytes are tested before the name is sliced, as names often share a first
                # letter and each slice is an allocation
                if lead == first and window[into + 1] == second \
                        and window[into:into + 11] == short_name:
                    return window[into + start:into + end]
        return None

    def capacity(self):
        """The cluster size and count, which is what statvfs() reports."""
        return self.__cluster_bytes, self.__clusters


class Stream(FatReader):
    """
    A file on the drive read straight from its flash, which reads on while the computer
    holds the drive. A file opened through the board's mount goes stale at every
    handover, so this finds the file's clusters once, from the tables on the flash, and
    reads them directly from then on. Read-only, and blind to the computer rewriting
    the file, which reads as whatever then fills its clusters. changed() says when that
    has happened.
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
    holds the drive. None where it cannot be found that way, for a name differing in
    case beyond ASCII, a path through "..", or a volume the computer reformatted as
    other than FAT12 or FAT16. The mount then answers, and a file the computer then
    takes will not read on.
    """
    try:
        return Stream(name)
    except OSError:
        return None


class View:
    """
    The drive read straight from its flash, mounted at the mount point while the
    computer holds the drive so a program still finds its files by path. Read-only.
    Finding a file waits while the computer writes, and a file read once it writes
    raises OSError.
    """

    # What a read raises once the computer has written to the drive since its file was opened
    __CHANGED_BENEATH = "the FX drive changed while this file was being read"

    def __init__(self):
        self.__cwd = ""

    def __resolve(self, path):
        return path if path.startswith("/") else self.__cwd + "/" + path

    @staticmethod
    def __settled(lookup, path):
        # Looks again where a write landed during the lookup, since nothing it found has
        # reached the program yet. Returns what it found and the write count it was found under
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
        # vfs.mount() and vfs.umount() call these, and there is nothing to set up
        pass

    def umount(self):
        pass

    def open(self, path, mode):
        if "w" in mode or "a" in mode or "x" in mode or "+" in mode:
            raise OSError(EROFS)
        stream, writes = self.__settled(Stream, self.__resolve(path))
        # Read in C, every read checking the write count against this one
        return rp2.MSCFile(stream.extents(), stream.size, writes, text="b" not in mode,
                           message=self.__CHANGED_BENEATH)

    def stat(self, path):
        (mode, size), _ = self.__settled(lambda name: Lookup().kind(name), self.__resolve(path))
        return (mode, 0, 0, 0, 0, 0, size, 0, 0, 0)

    def ilistdir(self, path):
        listed, _ = self.__settled(lambda name: Lookup().listing(name), self.__resolve(path))
        return iter([(name, mode, 0, size) for name, mode, size in listed])

    def statvfs(self, _path):
        cluster_bytes, clusters = Lookup().capacity()
        return (cluster_bytes, cluster_bytes, clusters, 0, 0, 0, 0, 0, 0, 255)

    def chdir(self, path):
        path = self.__resolve(path)
        if self.__settled(lambda name: Lookup().kind(name), path)[0][0] != S_IFDIR:
            raise OSError(ENOTDIR)
        self.__cwd = "/" + "/".join(part for part in path.split("/") if part)
        if self.__cwd == "/":
            self.__cwd = ""

    def getcwd(self):
        return self.__cwd or "/"

    def mkdir(self, _path):
        raise OSError(EROFS)

    def remove(self, _path):
        raise OSError(EROFS)

    def rename(self, _old_path, _new_path):
        raise OSError(EROFS)

    def rmdir(self, _path):
        raise OSError(EROFS)
