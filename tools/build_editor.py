#!/usr/bin/env python3
"""Turns a board's editor pages into the frozen module the FX drive carries.

Assembles a board's editor/picker.html from the parts every board shares in
boards/editor/picker/, any of its own in its editor/picker/ and its description in
editor/fx_board.json. A part in one of the feature folders
goes in only for a board with that feature. Generates catalogue.js from the live autofx tables
so a page always offers what the firmware it ships with provides, its strips and screen ports
from the board's class or, where the class is not in this repository, from its description. It
writes the picker, the text editor every board shares in boards/editor/editor.html and the
catalogue compressed into a frozen module for fx_drive to heal onto the drive. A board with no fx_libs/ carries no FX drive, and gets its picker.html and
catalogue.js alone. The parts and pages are
committed and the module is generated, so run this after editing a part, a page, the
description or anything the catalogue reads.

    python3 tools/build_editor.py boards/PIMORONI_MIGHTYFX
    python3 tools/build_editor.py --check boards/PIMORONI_MIGHTYFX

--check writes nothing and fails if a generated file is stale. It compares the module's
pages once inflated, since two zlib builds need not compress the same text to the same bytes.
"""

import argparse
import ast
import base64
import glob
import json
import os
import re
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

# Added to the header of a module carrying shells
SHELL_HEADER = """# A shelled page also carries the opening and closing of a page that inflates itself in the
# browser, its length and ends being that page's as the drive holds it.

"""

# A page that inflates itself in the browser, for a board whose drive is short of room: its
# zlib stream in base64 between these two, which fx_drive writes around the frozen stream
# itself. A browser without DecompressionStream says so instead.
SHELL_OPENING = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{}</title>
</head>
<body>
<p id="opening">Opening the page...</p>
<script id="packed" type="application/octet-stream">"""

SHELL_CLOSING = """</script>
<script>
(function () {
  var said = document.getElementById("opening");
  if (typeof DecompressionStream === "undefined") {
    said.textContent = "This browser is too old to open this page. A current Chrome or Edge opens it.";
    return;
  }
  var text = atob(document.getElementById("packed").textContent);
  var bytes = new Uint8Array(text.length);
  for (var i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i);
  var page = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate"));
  new Response(page).text().then(function (html) {
    document.open();
    document.write(html);
    document.close();
  }, function (e) { said.textContent = "This page could not be opened: " + e; });
})();
</script>
</body>
</html>
"""

# The pages a board whose description sets "shell" writes as shells; the catalogue is script,
# read as it is
SHELLED = ("PICKER", "EDITOR")

# How many characters of each end of a page a mount compares
EDGE = 512

# How many bytes of a zlib stream go on one line of the module
BYTES_PER_LINE = 64

# The board's description: its name, outputs, strips, screens, sound, the examples it offers, and
# the folder of examples its filesystem carries, as its uf2-copyfiles.sh copies them, the name
# those examples give the board, and with "shell" set, that its drive carries the pages as shells
DESCRIPTION_NAME = "fx_board.json"

# The picker's page and the parts every board shares, from the repository's root
SHARED_PARTS = os.path.join("boards", "editor", "picker")

# The text editor every board shares, which takes the board's own parts from the catalogue
SHARED_EDITOR = os.path.join("boards", "editor", "editor.html")

# The folders of picker parts a board takes only where its description has the feature
FEATURE_FOLDERS = {
    "screens": lambda board: bool(board["screens"]),
    "hub": lambda board: bool(board["screens"] and board["screens"]["hub"]),
    "sound": lambda board: bool(board["sound"]),
}

# The picker's parts are its script, so the page closes after the last of them
PICKER_END = "</script>\n</body>\n</html>\n"


def board_parts(picker_folders, board):
    """The board's numbered parts in number order, from the shared parts and any of its own, a
    feature folder's only where it has it. A part of the board's own adds to the shared ones."""
    folders = []
    for folder in picker_folders:
        folders.append(folder)
        for name in sorted(os.listdir(folder)):
            if not os.path.isdir(os.path.join(folder, name)):
                continue
            if name not in FEATURE_FOLDERS:
                sys.exit("{} is not a feature folder the build knows".format(
                    os.path.join(folder, name)))
            if FEATURE_FOLDERS[name](board):
                folders.append(os.path.join(folder, name))
    parts = [part for where in folders for part in glob.glob(os.path.join(where, "[0-9][0-9]_*.js"))]
    names = [os.path.basename(part) for part in parts]
    twice = sorted({name for name in names if names.count(name) > 1})
    if twice:
        sys.exit("{} is both a shared part and the board's own".format(", ".join(twice)))
    return sorted(parts, key=os.path.basename)


def picker(board_dir, repo_dir):
    """picker.html, from page.html and the numbered parts after it, with the board filled in."""
    with open(os.path.join(board_dir, "editor", DESCRIPTION_NAME), encoding="utf-8") as f:
        board = json.load(f)
    check_board(board_dir, board)
    shared =os.path.join(repo_dir, SHARED_PARTS)
    own = os.path.join(board_dir, "editor", "picker")
    with open(os.path.join(shared, "page.html"), encoding="utf-8") as f:
        text = f.read()
    for part in board_parts([shared] + ([own] if os.path.isdir(own) else []), board):
        with open(part, encoding="utf-8") as f:
            text += f.read()
    text = text.replace("__BOARD_NAME__", board["name"])
    text = text.replace("__BOARD__", json.dumps(board, indent=1))
    text += PICKER_END
    left = sorted(set(re.findall(r"__[A-Z_]+__", text)))
    if left:
        sys.exit("picker.html has {} unfilled".format(", ".join(left)))
    return text


# The tables a board's class declares its connectors in, each a tuple
BOARD_TABLES = ("STRIPS", "SCREENS", "STRIP_BRIGHTNESS", "STRIP_TAKES")

# What the module carries, in order. The catalogue without screen ports is only for a board
# that detects at run time whether it has them
MODULE_PAGES = ("PICKER", "EDITOR", "CATALOGUE", "CATALOGUE_WITHOUT_SCREENS")


def board_declares(board_dir):
    """
    What a board's class declares, read from its source in visible_libs/ so no board need be
    imported: its STRIPS, SCREENS, STRIP_BRIGHTNESS and STRIP_TAKES as lists, each empty where
    it declares none, whether it hands back a Screen Hub, and whether it detects at run time
    which of its parts it has. None where the board carries no class here.
    """
    sources = sorted(glob.glob(os.path.join(board_dir, "visible_libs", "*.py")))
    if not sources:
        return None
    declared = {table: [] for table in BOARD_TABLES}
    declared["hub"] = False
    declared["detect"] = False
    for path in sources:
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            found = {}
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if getattr(target, "id", "") in BOARD_TABLES:
                            found[target.id] = list(ast.literal_eval(item.value))
                elif isinstance(item, ast.FunctionDef) and item.name in ("hub", "detect"):
                    found[item.name] = True
            if "STRIPS" in found or "SCREENS" in found:
                declared.update(found)
                return declared
    return declared


def board_hub(declared):
    """Whether a board can carry a Screen Hub, which takes both of its screen ports."""
    return declared["hub"] and len(declared["SCREENS"]) > 1


def check_board(board_dir, board):
    """
    Fail where the description names a strip, screen port or hub the board's class lacks, or
    gives a strip a brightness or other strips' terminals the class does not.
    """
    declared = board_declares(board_dir)
    if declared is None:
        return
    strips = [name.lower() for name, _prop in declared["STRIPS"]]
    missing = [strip["name"] for strip in board["strips"] if strip["name"] not in strips]
    if missing:
        sys.exit("{} names {}, which the board's class does not declare in STRIPS".format(
            DESCRIPTION_NAME, ", ".join(missing)))
    bright = [name.lower() for name in declared["STRIP_BRIGHTNESS"]]
    takes = {name.lower(): sorted(other.lower() for other in others)
             for name, others in declared["STRIP_TAKES"]}
    for strip in board["strips"]:
        if ("brightness" in strip) != (strip["name"] in bright):
            sys.exit("{} and the board's class's STRIP_BRIGHTNESS disagree on whether {} takes a "
                     "brightness".format(DESCRIPTION_NAME, strip["name"]))
        if sorted(strip.get("takes", [])) != takes.get(strip["name"], []):
            sys.exit("{} and the board's class's STRIP_TAKES disagree on the terminals {} "
                     "takes".format(DESCRIPTION_NAME, strip["name"]))
    screens = [name.lower() for name, _prop in declared["SCREENS"]]
    described = board["screens"] or {"ports": [], "hub": False}
    missing = [port["id"] for port in described["ports"] if port["id"] not in screens]
    if missing:
        sys.exit("{} names {}, which the board's class does not declare in SCREENS".format(
            DESCRIPTION_NAME, ", ".join(missing)))
    if described["hub"] and not board_hub(declared):
        sys.exit("{} offers a Screen Hub, which the board's class cannot carry".format(
            DESCRIPTION_NAME))


def described(board):
    """What a board's description says its class would declare, for a board whose class is not
    in this repository."""
    screens = board["screens"] or {"ports": [], "hub": False}
    return {"STRIPS": [(strip["name"], None) for strip in board["strips"]],
            "SCREENS": [(port["id"], None) for port in screens["ports"]],
            "STRIP_BRIGHTNESS": [strip["name"] for strip in board["strips"] if "brightness" in strip],
            "STRIP_TAKES": [(strip["name"], strip["takes"]) for strip in board["strips"]
                            if "takes" in strip],
            "hub": screens["hub"], "detect": False}


def catalogue(repo_dir, board_dir, board, offer_screens=True):
    """catalogue.js, from the same tables autofx reads on the board, with the strips and screen
    ports its class declares, or its description where its class is not here, and the board's
    outputs and connectors from its description. Without offer_screens it offers no screen
    ports, for a board that detects it has none."""
    fake = types.ModuleType("machine")
    for name in ("PWM", "Pin", "Timer", "SPI"):
        setattr(fake, name, type(name, (), {}))
    sys.modules["machine"] = fake
    for name in ("rp2", "vfs"):
        sys.modules.setdefault(name, types.ModuleType(name))

    sys.path.insert(0, repo_dir)
    sys.path.insert(0, os.path.join(repo_dir, "boards", "visible_libs"))
    import autofx

    declared = board_declares(board_dir) or described(board)
    if not offer_screens:
        declared = dict(declared, SCREENS=[])
    strips = [name.lower() for name, _prop in declared["STRIPS"]]
    screens = [name.lower() for name, _prop in declared["SCREENS"]]
    sizes = autofx.SCREEN_SIZES + ((autofx.HUB,) if board_hub(declared) else ())
    board_settings = dict(autofx.BOARD_SETTINGS, **dict.fromkeys(screens, sizes),
                          **dict.fromkeys(strips))

    # The board's own parts for the text editor's targets and hints: its outputs with their kind,
    # and each strip and screen port as a file writes it, with the connector its description names
    connectors = {part.get("name", part.get("id")): part.get("connector")
                  for part in board["strips"] + (board["screens"] or {"ports": []})["ports"]}
    own = {
        "outputs": [[output["name"], output["kind"]] for output in board["outputs"]],
        "colour": board["output_words"]["colour"],
        "strips": [[name, connectors.get(name.lower())] for name, _prop in declared["STRIPS"]],
        "screens": [[name, connectors.get(name.lower())]
                    for name, _prop in declared["SCREENS"]],
        "hub": board_hub(declared),
        "sound": bool(board["sound"]),
    }
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
        "screen_ports": screens,
        "strips": strips,
        "output_settings": list(autofx.OUTPUT_SETTINGS),
        "screen_settings": list(autofx.SCREEN_SETTINGS),
        "tiling": list(autofx.TILING),
        "board_settings": {key: (list(value) if isinstance(value, tuple) else value)
                           for key, value in board_settings.items()},
        "board": own,
    }
    return ("// Generated from the autofx tables. Do not edit.\n"
            "var CATALOGUE = " + json.dumps(tables, indent=1) + ";\n")


def embed(name, text, shell=False):
    """One page as a tuple of its length, its two ends and its zlib stream.

    A shelled page adds its shell's opening and closing, and its length and ends are those of
    the shell as the drive will hold it.
    """
    if not text.isascii():
        stray = sorted({c for c in text if not c.isascii()})
        sys.exit("{} contains {}, and it has to be ASCII to reach the drive a "
                 "piece at a time".format(name, ", ".join(repr(c) for c in stray)))
    packed = zlib.compress(text.encode("ascii"), 9)
    lines = ["    {!r}".format(packed[at:at + BYTES_PER_LINE])
             for at in range(0, len(packed), BYTES_PER_LINE)]
    if not shell:
        return "{} = ({}, {!r}, {!r}, (\n{}\n))\n".format(
            name, len(text), text[:EDGE], text[-EDGE:], "\n".join(lines))
    opening, closing = shell_ends(text)
    drive = opening + base64.b64encode(packed).decode("ascii") + closing
    return "{} = ({}, {!r}, {!r}, (\n{}\n), {!r}, {!r})\n".format(
        name, len(drive), drive[:EDGE], drive[-EDGE:], "\n".join(lines),
        opening.encode("ascii"), closing.encode("ascii"))


def shell_ends(text):
    """The opening and closing of a page's shell, titled as the page is."""
    title = re.search(r"<title>(.*?)</title>", text)
    return SHELL_OPENING.format(title.group(1) if title else ""), SHELL_CLOSING


def unpacked(module_text):
    """
    Each page of a module's text, inflated, after checking its length and ends agree, and the
    names of the pages it carries as shells.
    """
    namespace = {}
    exec(compile(module_text, MODULE_NAME, "exec"), namespace)
    pages = {}
    shelled = set()
    for name in MODULE_PAGES:
        if name not in namespace:
            continue
        size, head, tail, packed = namespace[name][:4]
        text = zlib.decompress(packed).decode("ascii")
        drive = text
        # Check if the page is shelled, which the drive holds as its shell
        if len(namespace[name]) == 6:
            opening, closing = namespace[name][4:]
            drive = (opening.decode("ascii") + base64.b64encode(packed).decode("ascii") +
                     closing.decode("ascii"))
            shelled.add(name)
        if (size, head, tail) != (len(drive), drive[:EDGE], drive[-EDGE:]):
            sys.exit("{} carries a length or ends that are not its page's".format(name))
        pages[name] = text
    return pages, shelled


def stale_files(generated):
    """The generated files whose text on disk is not what they should hold."""
    stale = []
    for path, text in generated.items():
        with open(path, encoding="utf-8", newline="") as f:
            if f.read() != text:
                stale.append(path)
    return stale


def build_page_only(generated, check):
    """Write the generated pages, or with check fail where any is stale."""
    if check:
        stale = stale_files(generated)
        if stale:
            sys.exit("stale, rebuild with tools/build_editor.py: " + ", ".join(stale))
        print("editor pages are up to date")
        return
    for path, text in generated.items():
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print("{} bytes of pages: {}".format(sum(len(text) for text in generated.values()),
                                         ", ".join(generated)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="write nothing, and fail if a generated file is stale")
    parser.add_argument("board_dir", help="a board directory holding editor/")
    args = parser.parse_args()

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    editor_dir = os.path.join(args.board_dir, "editor")
    module = os.path.join(args.board_dir, "fx_libs", MODULE_NAME)

    # What the generated files should hold, the picker and catalogue being generated as well as
    # embedded. The catalogue is the autofx tables the board's firmware carries
    with open(os.path.join(editor_dir, DESCRIPTION_NAME), encoding="utf-8") as f:
        board = json.load(f)
    catalogue_path = os.path.join(editor_dir, "catalogue.js")
    generated = {os.path.join(editor_dir, "picker.html"): picker(args.board_dir, repo_dir),
                 catalogue_path: catalogue(repo_dir, args.board_dir, board)}

    # A board with no FX drive modules carries no FX drive, so it takes the pages alone
    if not os.path.isdir(os.path.dirname(module)):
        build_page_only(generated, args.check)
        return

    sources = {"CATALOGUE": generated[catalogue_path],
               "PICKER": generated[os.path.join(editor_dir, "picker.html")]}
    with open(os.path.join(repo_dir, SHARED_EDITOR), encoding="utf-8", newline="") as f:
        sources["EDITOR"] = f.read()
    declared = board_declares(args.board_dir)
    if declared and declared["detect"]:
        sources["CATALOGUE_WITHOUT_SCREENS"] = catalogue(repo_dir, args.board_dir, board,
                                                         offer_screens=False)

    shelled = set(SHELLED) if board.get("shell", False) else set()
    if args.check:
        stale = stale_files(generated)
        with open(module, encoding="utf-8") as f:
            if unpacked(f.read()) != (sources, shelled):
                stale.append(module)
        if stale:
            sys.exit("stale, rebuild with tools/build_editor.py: " + ", ".join(stale))
        print("editor pages and module are up to date")
        return

    parts = [MODULE_HEADER + (SHELL_HEADER if shelled else "")]
    for name in MODULE_PAGES:
        if name in sources:
            parts.append(embed(name, sources[name], name in shelled))
    module_text = "\n".join(parts)

    # The packing has to invert exactly: parse the module back and compare
    if unpacked(module_text) != (sources, shelled):
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
