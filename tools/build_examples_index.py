#!/usr/bin/env python3
"""Writes the index of a board's examples that its picker checks the FX drive against.

The picker fetches the index from GitHub when asked, and offers the examples the drive lacks, or
holds an older version of, to download. The index lists every example program, drawing, picture
and sound the repository holds for the board, each with the files it brings: a program's or
drawing's Python file, its thumbnails, a picture its Picture: line names and the pictures its
source names by their path on the drive; a slideshow's pictures; a picture or sound itself.

Each file has its size and hash, the one git gives the file's contents, which the picker can work
out from a copy on the drive to tell one that matches from one that does not. Each also keeps the hashes and sizes it
had before and the paths it was moved from, so the picker can tell an old copy from one the user
changed, and finds an example kept where it used to be. Those are carried forward from the index
already in the repository, which needs no git history to read.

Each example takes the picofx version the index is written at as the lowest firmware it runs on,
unless its opening string has a "Firmware:" line naming another. Only files git tracks are
indexed, so an example still being written is left out until it is committed.

    python3 tools/build_examples_index.py boards/PIMORONI_MIGHTYFX
    python3 tools/build_examples_index.py --check boards/PIMORONI_MIGHTYFX

--check writes nothing and fails if the index is stale. A board whose description names no
"examples_index" has none, and is passed over.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

DESCRIPTION = os.path.join("editor", "fx_board.json")

# The module that holds picofx's version, from the repository's root
VERSION_SOURCE = os.path.join("picofx", "__init__.py")

# A file read as text has Windows line endings taken out before it is hashed, as git stores it
TEXT_FILE = re.compile(r"\.(py|txt|md|json|html|csv)$", re.IGNORECASE)

PICTURE_FILE = re.compile(r"\.(gif|png|jpe?g)$", re.IGNORECASE)
SOUND_FILE = re.compile(r"\.wav$", re.IGNORECASE)

# A file's opening string, the first one written in triple quotes, as the picker reads it
OPENING_STRING = re.compile(r"(\"\"\"|''')([\s\S]*?)\1")

# Lines of an opening string the index reads
DRAWING_LINE = re.compile(r"^\s*Drawing:", re.MULTILINE)
PICTURE_LINE = re.compile(r"^\s*Picture:\s*(.+?)\s*$", re.MULTILINE)
FIRMWARE_LINE = re.compile(r"^\s*Firmware:\s*(.+?)\s*$", re.MULTILINE)

# A path on the drive written out in a source, such as "/examples/pictures/billboards/portrait"
DRIVE_PATH = re.compile(r"[\"'](/examples/[^\"'{}]+?)/?[\"']")


def tracked(repo_dir, folder):
    """The files git tracks under a folder, by path from the repository's root."""
    listed = subprocess.run(["git", "-C", repo_dir, "ls-files", "-z", "--", folder], check=True,
                            capture_output=True).stdout.decode()
    return sorted(name for name in listed.split("\0") if name)


def hash_of(data):
    """The hash git gives bytes stored as a file, as `git hash-object` prints it."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def read_files(repo_dir, base):
    """Every tracked file under the board's examples folder, as {drive path: (hash, size, data)},
    a drive path being one from the top of the FX drive, such as examples/drawings/x.py."""
    files = {}
    for name in tracked(repo_dir, base + "examples/"):
        if name.endswith(".md"):
            continue
        with open(os.path.join(repo_dir, name), "rb") as handle:
            data = handle.read()
        if TEXT_FILE.search(name):
            data = data.replace(b"\r\n", b"\n")
        files[name[len(base):]] = (hash_of(data), len(data), data)
    return files


def opening_string(source):
    found = OPENING_STRING.search(source)
    return found.group(2).strip() if found else ""


def brought(path, source, files):
    """The files a program or drawing brings, its own first, then its thumbnails, then what it
    names. A folder it names brings the files directly inside it."""
    stem = path[:-3]
    beside = stem[:stem.rfind("/") + 1]
    wanted = [path]
    wanted += sorted(name for name in files if name == stem + ".png" or
                     (name.startswith(stem + "-") and name.endswith(".png") and
                      "/" not in name[len(stem):]))
    picture = PICTURE_LINE.search(opening_string(source))
    if picture:
        wanted.append(beside + picture.group(1))
    for named in DRIVE_PATH.findall(source):
        named = named.lstrip("/")
        if named in files:
            wanted.append(named)
        else:
            wanted += sorted(name for name in files if name.startswith(named + "/") and
                             "/" not in name[len(named) + 1:])
    return [name for at, name in enumerate(wanted) if name in files and name not in wanted[:at]]


def sections_of(files, folder):
    """The sections a media folder's sections.txt lists, as [(name, members)], a member being a
    file, a slideshow's folder, or folder/* for each file in that folder on its own."""
    held = files.get(folder + "sections.txt")
    if not held:
        return []
    sections = []
    for line in held[2].decode("utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]
        members = [one.strip() for one in parts[2].split(",")] if len(parts) > 2 else []
        sections.append((parts[0], [one for one in members if one]))
    return sections


def section_of(sections, member):
    for section, members in sections:
        for one in members:
            if one == member or (one.endswith("/*") and member.startswith(one[:-1])):
                return section
    return ""


def code_examples(files, version):
    """The example programs and drawings, as index entries less their files' entries."""
    found = []
    for path in sorted(files):
        top_drawing = path.startswith("examples/drawings/") and path.count("/") == 2
        if not path.endswith(".py") or not (top_drawing or path.startswith("examples/programs/")):
            continue
        source = files[path][2].decode("utf-8")
        said = opening_string(source)
        drawing = bool(DRAWING_LINE.search(said))
        if drawing != top_drawing:
            continue
        firmware = FIRMWARE_LINE.search(said)
        found.append(({"path": path, "kind": "drawing" if drawing else "program",
                       "firmware": firmware.group(1) if firmware else version},
                      brought(path, source, files)))
    return found


def pictures(files, version):
    """The example pictures as the picker's walk finds them: a file at the top of the pictures
    folder, a folder of pictures as one slideshow, and each file of a folder its section splits.
    A folder holding only folders is walked into."""
    folder = "examples/pictures/"
    sections = sections_of(files, folder)
    split = {member[:-2] for _, members in sections for member in members if member.endswith("/*")}
    by_folder = {}
    for name in sorted(files):
        if name.startswith(folder) and PICTURE_FILE.search(name):
            inner = name[len(folder):name.rfind("/")] if name.count("/") > 2 else ""
            by_folder.setdefault(inner, []).append(name)
    found = []
    for inner, held in sorted(by_folder.items()):
        items = [(name[len(folder):], [name], False) for name in held] \
            if not inner or inner in split else [(inner, held, True)]
        for member, names, slideshow in items:
            found.append(({"path": folder + member, "kind": "picture", "firmware": version,
                           "name": member.rsplit("/", 1)[-1],
                           "section": section_of(sections, member), "slideshow": slideshow},
                          names))
    return found


def sounds(files, version):
    """The example sounds, every WAV file under the sounds folder its own, as the picker walks
    into any folder there."""
    folder = "examples/sounds/"
    sections = sections_of(files, folder)
    found = []
    for name in sorted(files):
        if name.startswith(folder) and SOUND_FILE.search(name):
            member = name[len(folder):]
            found.append(({"path": name, "kind": "sound", "firmware": version,
                           "name": member.rsplit("/", 1)[-1],
                           "section": section_of(sections, member)}, [name]))
    return found


def carried(name, hashed, size, before, gone):
    """A file's entry, its earlier versions and earlier paths carried forward from the last
    index: its own where it was there, else one of the same hash that has since gone, a move."""
    was, moved_from = [], []
    previous = before.get(name)
    if previous is None and hashed in gone:
        moved = gone[hashed]
        previous = before[moved]
        moved_from = [moved] + previous.get("moved_from", [])
    elif previous is not None:
        moved_from = previous.get("moved_from", [])
    if previous is not None:
        was = list(previous["was"])
        if previous["hash"] != hashed and not any(one["hash"] == previous["hash"] for one in was):
            was.append({"hash": previous["hash"], "size": previous["size"]})
        was = sorted((one for one in was if one["hash"] != hashed), key=lambda one: one["hash"])
    entry = {"path": name, "size": size, "hash": hashed, "was": was}
    if moved_from:
        entry["moved_from"] = moved_from
    return entry


def build(repo_dir, base, previous):
    """The index, as text, for the examples under base, carrying forward the previous index."""
    with open(os.path.join(repo_dir, VERSION_SOURCE), encoding="utf-8") as handle:
        version = re.search(r'^PICOFX_VERSION = "([^"]+)"', handle.read(), re.MULTILINE).group(1)
    files = read_files(repo_dir, base)
    before = {}
    for example in (previous or {}).get("examples", []):
        for file in example["files"]:
            before[file["path"]] = file
    # A file the last index had that is no longer there, by its hash, to find where it moved
    gone = {}
    for name, file in sorted(before.items()):
        if name not in files:
            gone.setdefault(file["hash"], name)
    examples = []
    for entry, names in code_examples(files, version) + pictures(files, version) + \
            sounds(files, version):
        entry["files"] = [carried(name, files[name][0], files[name][1], before, gone)
                          for name in names]
        examples.append(entry)
    return json.dumps({"format": 1, "examples": examples}, indent=1) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if the index is stale")
    parser.add_argument("--from", dest="seed", metavar="INDEX",
                        help="an index to carry earlier versions forward from, in place of the "
                             "board's own")
    parser.add_argument("board_dir", help="a board directory holding editor/fx_board.json")
    args = parser.parse_args()

    repo_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    with open(os.path.join(args.board_dir, DESCRIPTION), encoding="utf-8") as handle:
        board = json.load(handle)
    if "examples_index" not in board:
        return 0
    index_path = os.path.join(repo_dir, board["examples_index"])
    base = board["examples_index"][:board["examples_index"].rfind("/") + 1]
    previous = None
    seed = args.seed or index_path
    if os.path.exists(seed):
        with open(seed, encoding="utf-8") as handle:
            previous = json.load(handle)
    text = build(repo_dir, base, previous)
    if args.check:
        with open(index_path, encoding="utf-8") as handle:
            if handle.read().replace("\r\n", "\n") != text:
                sys.exit("{} is stale: run tools/build_examples_index.py {}".format(
                    board["examples_index"], args.board_dir))
        print("examples index is up to date")
        return 0
    with open(index_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("{} examples, {} bytes: {}".format(len(json.loads(text)["examples"]), len(text),
                                              board["examples_index"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
