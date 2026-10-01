#!/usr/bin/env python3
"""Turns a board's editor pages into the frozen module the FX drive carries.

Reads editor/picker.html, generates catalogue.js from the live autofx tables so a
page always offers what the firmware it ships with provides, and writes the pages and
catalogue compressed into a frozen module for fx_drive to heal onto the drive. The
pages are committed and the module is generated, so run this after editing a page or
anything the catalogue reads.

    python3 tools/build_editor.py boards/PIMORONI_MIGHTYFX
    python3 tools/build_editor.py --check boards/PIMORONI_MIGHTYFX

--check writes nothing and fails if a generated file is stale. It compares the module's
pages once inflated, since two zlib builds need not compress the same text to the same bytes.
"""

import argparse
import json
import os
import sys
import types
import zlib

MODULE_NAME = "fx_editor.py"

MODULE_HEADER = """# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# Generated from editor/*.html and the autofx tables by tools/build_editor.py.
# Edit those and rebuild; edits here are lost.
#
# Each page is its length, its first and last characters, and the whole page as a zlib
# stream. The ends let a mount see the drive already holds a page without inflating it.

"""

PAGES = (("PICKER", "picker.html"), ("EDITOR", "editor.html"))

# How many characters of each end of a page a mount compares
EDGE = 512

# How many bytes of a zlib stream go on one line of the module
BYTES_PER_LINE = 64

def catalogue(repo_dir):
    """catalogue.js, from the same tables autofx reads on the board."""
    fake = types.ModuleType("machine")
    for name in ("PWM", "Pin", "Timer", "SPI"):
        setattr(fake, name, type(name, (), {}))
    sys.modules["machine"] = fake
    for name in ("rp2", "vfs"):
        sys.modules.setdefault(name, types.ModuleType(name))

    sys.path.insert(0, repo_dir)
    sys.path.insert(0, os.path.join(repo_dir, "boards", "visible_libs"))
    import autofx

    tables = {
        "effects": {name: {"kind": kind, "takes": list(takes)}
                    for name, (_cls, kind, _called, takes)
                    in sorted(autofx.EFFECTS.items())},
        "screen_effects": {name: list(takes)
                           for name, takes in autofx.SCREEN_EFFECTS.items()},
        "audio": autofx.AUDIO,
        "audio_effects": {name: list(takes)
                          for name, takes in autofx.AUDIO_EFFECTS.items()},
        "settings": autofx.SETTINGS,
        "colours": sorted(autofx.COLOURS),
        "channel_kinds": autofx.CHANNEL_KINDS,
        "screen_ports": sorted(autofx.SCREEN_PORTS),
        "strips": list(autofx.STRIPS),
        "output_settings": list(autofx.OUTPUT_SETTINGS),
        "screen_settings": list(autofx.SCREEN_SETTINGS),
        "tiling": list(autofx.TILING),
        "board_settings": {key: (list(value) if isinstance(value, tuple) else value)
                           for key, value in autofx.BOARD_SETTINGS.items()},
    }
    return ("// Generated from the autofx tables. Do not edit.\n"
            "var CATALOGUE = " + json.dumps(tables, indent=1) + ";\n")


def embed(name, text):
    """One page as a tuple of its length, its two ends and its zlib stream."""
    if not text.isascii():
        stray = sorted({c for c in text if not c.isascii()})
        sys.exit("{} contains {}, and it has to be ASCII to reach the drive a "
                 "piece at a time".format(name, ", ".join(repr(c) for c in stray)))
    packed = zlib.compress(text.encode("ascii"), 9)
    lines = ["    {!r}".format(packed[at:at + BYTES_PER_LINE])
             for at in range(0, len(packed), BYTES_PER_LINE)]
    return "{} = ({}, {!r}, {!r}, (\n{}\n))\n".format(
        name, len(text), text[:EDGE], text[-EDGE:], "\n".join(lines))


def unpacked(module_text):
    """Each page of a module's text, inflated, after checking its length and ends agree."""
    namespace = {}
    exec(compile(module_text, MODULE_NAME, "exec"), namespace)
    pages = {}
    for name in ("PICKER", "EDITOR", "CATALOGUE"):
        size, head, tail, packed = namespace[name]
        text = zlib.decompress(packed).decode("ascii")
        if (size, head, tail) != (len(text), text[:EDGE], text[-EDGE:]):
            sys.exit("{} carries a length or ends that are not its page's".format(name))
        pages[name] = text
    return pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="write nothing, and fail if a generated file is stale")
    parser.add_argument("board_dir", help="a board directory holding editor/")
    args = parser.parse_args()

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    editor_dir = os.path.join(args.board_dir, "editor")
    module = os.path.join(args.board_dir, "frozen_libs", MODULE_NAME)

    # What the generated files should hold
    sources = {"CATALOGUE": catalogue(repo_dir)}
    generated = {os.path.join(editor_dir, "catalogue.js"): sources["CATALOGUE"]}
    for name, page in PAGES:
        with open(os.path.join(editor_dir, page), encoding="utf-8", newline="") as f:
            sources[name] = f.read()

    if args.check:
        stale = []
        for path, text in generated.items():
            with open(path, encoding="utf-8", newline="") as f:
                if f.read() != text:
                    stale.append(path)
        with open(module, encoding="utf-8") as f:
            if unpacked(f.read()) != sources:
                stale.append(module)
        if stale:
            sys.exit("stale, rebuild with tools/build_editor.py: " + ", ".join(stale))
        print("editor pages and module are up to date")
        return

    parts = [MODULE_HEADER]
    for name in ("PICKER", "EDITOR", "CATALOGUE"):
        parts.append(embed(name, sources[name]))
    module_text = "\n".join(parts)

    # The packing has to invert exactly: parse the module back and compare
    if unpacked(module_text) != sources:
        sys.exit("the pages do not survive the module round trip")

    generated[module] = module_text
    for path, text in generated.items():
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    print("{} bytes of pages and catalogue, packed to {}: {}".format(
        sum(len(text) for text in sources.values()),
        sum(len(zlib.compress(text.encode("ascii"), 9)) for text in sources.values()), module))


if __name__ == "__main__":
    main()
