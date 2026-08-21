#!/usr/bin/env python3
"""Turns a board's editor pages into the frozen module the FX drive carries.

Reads editor/picker.html, generates catalogue.js from the live autofx tables so a
page always offers what the firmware it ships with provides, and writes both as a
frozen module for fx_drive to heal onto the drive. The pages are committed and the
module is generated, so run this after editing a page or anything the catalogue
reads.

    python3 tools/build_editor.py boards/PIMORONI_MIGHTYFX
"""

import argparse
import json
import os
import sys
import types

MODULE_NAME = "fx_editor.py"

MODULE_HEADER = """# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# Generated from editor/*.html and the autofx tables by tools/build_editor.py.
# Edit those and rebuild; edits here are lost.

"""

PAGES = (("PICKER", "picker.html"),)


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
        "settings": autofx.SETTINGS,
        "colours": sorted(autofx.COLOURS),
        "channel_kinds": autofx.CHANNEL_KINDS,
        "screen_ports": sorted(autofx.SCREEN_PORTS),
        "strips": list(autofx.STRIPS),
        "board_settings": {key: (list(value) if isinstance(value, tuple) else value)
                           for key, value in autofx.BOARD_SETTINGS.items()},
    }
    return ("// Generated from the autofx tables. Do not edit.\n"
            "var CATALOGUE = " + json.dumps(tables, indent=1) + ";\n")


def embed(name, text):
    """One page as a triple-quoted assignment, line structure kept for diffs."""
    if not text.isascii():
        stray = sorted({c for c in text if not c.isascii()})
        sys.exit("{} contains {}, and it has to be ASCII to reach the drive a "
                 "piece at a time".format(name, ", ".join(repr(c) for c in stray)))
    escaped = text.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return '{} = """\\\n{}"""\n'.format(name, escaped)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board_dir", help="a board directory holding editor/")
    args = parser.parse_args()

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    sources = {"CATALOGUE": catalogue(repo_dir)}
    for name, page in PAGES:
        path = os.path.join(args.board_dir, "editor", page)
        with open(path, encoding="utf-8", newline="") as f:
            sources[name] = f.read()

    parts = [MODULE_HEADER]
    for name in ("PICKER", "CATALOGUE"):
        parts.append(embed(name, sources[name]))
    module_text = "\n".join(parts)

    # The escaping has to invert exactly: parse the module back and compare
    namespace = {}
    exec(compile(module_text, MODULE_NAME, "exec"), namespace)
    for name, text in sources.items():
        if namespace[name] != text:
            sys.exit("{} does not survive the module round trip".format(name))

    module = os.path.join(args.board_dir, "frozen_libs", MODULE_NAME)
    with open(module, "w", encoding="utf-8", newline="\n") as f:
        f.write(module_text)

    print("{} bytes of pages and catalogue: {}".format(
        sum(len(text) for text in sources.values()), module))


if __name__ == "__main__":
    main()
