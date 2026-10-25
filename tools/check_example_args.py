#!/usr/bin/env python3
"""Checks that each example's Args line agrees with the arguments the example reads.

An example reads an argument as NAME = DEFAULT if not sys.argv[N:] else sys.argv[N], with an
int() or float() round it where it is a number, and the picker offers it as the Nth entry of
the Args line in its opening string, written "Name = default", or "Name = default or other" for a
choice, the default first. The two are kept apart, so this fails where an example reads sys.argv
any other way, where an argument it reads has no entry, and where an entry's default is not the
one the example falls back on.

    python3 tools/check_example_args.py examples
"""

import argparse
import ast
import os
import re
import sys

# One argument read with a fallback, its default and the position it is read from
ARGUMENT_READ = re.compile(r"^\w+ = (.+?) if not sys\.argv\[(\d+):\] else "
                           r"(?:(?:int|float)\()?sys\.argv\[\2\]\)?\s*$")

# The Args line of an opening string
ARGS_LINE = re.compile(r"^\s*Args:\s*(.+?)\s*$", re.M)

# A file's opening string, the first one written in triple quotes, as the picker reads it
OPENING_STRING = re.compile(r"(\"\"\"|''')([\s\S]*?)\1")


def args_entries(source):
    """The Args line's entries as [name, default or None], or None where it has no Args line."""
    opening = OPENING_STRING.search(source)
    found = ARGS_LINE.search(opening.group(2)) if opening else None
    if not found:
        return None

    entries = []
    for entry in found.group(1).split(","):
        name, split, default = entry.partition("=")
        # Of a choice, the default is the first
        entries.append([name.strip(), re.split(r"\s+or\s+", default.strip())[0] if split else None])
    return entries


def problems_in(source):
    """What is wrong with one example's arguments, as a list of messages, empty where nothing is."""
    reads = []
    problems = []
    for number, line in enumerate(source.splitlines(), 1):
        if "sys.argv" not in line:
            continue
        read = ARGUMENT_READ.match(line)
        if not read:
            problems.append(f"line {number} reads sys.argv other than as NAME = DEFAULT if not "
                            f"sys.argv[N:] else sys.argv[N]")
            continue
        reads.append((number, int(read.group(2)), str(ast.literal_eval(read.group(1)))))

    if not reads:
        return problems

    entries = args_entries(source)
    if entries is None:
        return problems + ["it reads sys.argv but its opening string has no Args line"]

    for number, position, default in reads:
        if position > len(entries):
            problems.append(f"line {number} reads argument {position}, which Args does not name")
        elif entries[position - 1][1] != default:
            name, given = entries[position - 1]
            problems.append(f"line {number} falls back on {default}, which Args gives {name} as "
                            f"{given if given is not None else 'no default'}")
    return problems


def example_files(paths):
    """Every Python file under the paths given, in name order."""
    for path in paths:
        if os.path.isfile(path):
            yield path
            continue
        for folder, folders, names in os.walk(path):
            folders.sort()
            for name in sorted(names):
                if name.endswith(".py"):
                    yield os.path.join(folder, name)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", help="example files, or folders to search for them")
    arguments = parser.parse_args()

    failed = 0
    for path in example_files(arguments.paths):
        with open(path, encoding="utf-8") as file:
            problems = problems_in(file.read())
        for problem in problems:
            print(f"{path}: {problem}")
        failed += bool(problems)

    if failed:
        print(f"{failed} example(s) disagree with their Args line", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
