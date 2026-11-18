#!/usr/bin/env python3
"""Leaves a board's FX drive copy of its examples with only the programs its list names.

The list names each program to keep by its path from examples/programs/, one per line, with lines
starting # as comments. Any other program leaves the drive with its thumbnails, and a folder left
empty goes too. Pictures, drawings and everything outside programs/ are kept.

    python3 tools/drive_programs.py <the drive copy's examples folder> <the board's list>
"""

import os
import sys


def listed(path):
    """The programs a list names, as paths from examples/programs/."""
    with open(path, encoding="utf-8") as handle:
        lines = (line.strip() for line in handle)
        return {line for line in lines if line and not line.startswith("#")}


def main():
    examples, list_path = sys.argv[1:3]
    programs = os.path.join(examples, "programs")
    keep = listed(list_path)
    removed = 0
    for folder, _, names in os.walk(programs):
        for name in names:
            relative = os.path.relpath(os.path.join(folder, name), programs).replace(os.sep, "/")
            if not name.endswith(".py") or relative in keep:
                continue
            stem = name[:-3]
            # The program goes with its thumbnails, its stem's .png and any -suffixed one beside it
            for other in names:
                if other == name or other == stem + ".png" or (
                        other.startswith(stem + "-") and other.endswith(".png")):
                    os.remove(os.path.join(folder, other))
            removed += 1
    # A folder its programs all left is removed too, deepest first
    for folder, _, _ in sorted(os.walk(programs), reverse=True):
        if folder != programs and not os.listdir(folder):
            os.rmdir(folder)
    missing = sorted(path for path in keep if not os.path.exists(os.path.join(programs, path)))
    # Check if the list names a program the examples no longer hold, so a rename is not missed
    if missing:
        sys.exit("the drive list names programs that are not in the examples: " + ", ".join(missing))
    print("{} programs left off the drive, {} kept".format(removed, len(keep)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
