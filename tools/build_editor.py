#!/usr/bin/env python3
"""Turns a board's editor pages into the frozen module the FX drive carries.

Assembles a board's picker from the parts every board shares in boards/editor/picker/, any of
its own in its editor/picker/ and its description in editor/fx_board.json. A part in one of the
feature folders goes in only for a board with that feature. editor/picker.html links the parts as
they are; the drive's copy has them bundled and minified by esbuild, which
npm ci --prefix tools/picker installs. Generates catalogue.js from the live autofx tables
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

Both pages show picofx's version after their heading, followed by "preview" in the committed pages.
A release build passes --release with its tag, which must be that version, and its pages show the
version alone. It refuses a picker whose Discover fetches examples from a branch other than main.

    python3 tools/build_editor.py --release 1.1.3 boards/PIMORONI_MIGHTYFX
"""

import argparse
import ast
import base64
import glob
import hashlib
import json
import os
import re
import subprocess
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
{}</head>
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

# The last line of every page on the drive, the hash of its content. A mount judges a page by its
# length and its two ends, so a change that kept the length and fell in the middle would pass for
# current, as the shell's closing alone is longer than an end. The hash puts every change in the tail
STAMP_HTML = "<!-- content {} -->\n"
STAMP_SCRIPT = "// content {}\n"
STAMP_DIGITS = 16

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
    "sensor": lambda board: bool(board.get("sensor")),
    "discover": lambda board: "examples_index" in board,
}

# The module that holds picofx's version, from the repository's root
VERSION_SOURCE = os.path.join("picofx", "__init__.py")


def shown_version(repo_dir, release):
    """The version the pages show, picofx's own, and "preview" after it unless this is its
    release."""
    with open(os.path.join(repo_dir, VERSION_SOURCE), encoding="utf-8") as f:
        found = re.search(r'^PICOFX_VERSION = "([^"]+)"', f.read(), re.MULTILINE)
    if not found:
        sys.exit("{} has no PICOFX_VERSION".format(VERSION_SOURCE))
    version = found.group(1)
    if release is None:
        return version + " preview"
    if release != version:
        sys.exit("releasing {} but picofx is {}".format(release, version))
    return version


# The branch a picker with Discover fetches examples from. A release ships it on every board for
# good, so a release takes it from main
DISCOVER_BRANCH = re.compile(r'^var DISCOVER_BRANCH = "([^"]*)";$', re.MULTILINE)
RELEASE_BRANCH = "main"


def check_release_branch(repo_dir):
    """Refuse a release whose picker fetches its examples from a branch other than main."""
    source = os.path.join(repo_dir, SHARED_PARTS, "discover", "28_discover.js")
    with open(source, encoding="utf-8") as f:
        found = DISCOVER_BRANCH.search(f.read())
    if not found:
        sys.exit("the DISCOVER_BRANCH line of {} could not be read".format(source))
    if found.group(1) != RELEASE_BRANCH:
        sys.exit("Discover fetches examples from {}, and a release takes them from {}. Set "
                 "DISCOVER_BRANCH in {}".format(found.group(1), RELEASE_BRANCH, source))


def board_parts(picker_folders, board, kind="js"):
    """The board's numbered parts in number order, from the shared parts and any of its own, a
    feature folder's only where it has it. A part of the board's own adds to the shared ones."""
    folders = []

    def take(folder):
        folders.append(folder)
        for name in sorted(os.listdir(folder)):
            if not os.path.isdir(os.path.join(folder, name)):
                continue
            if name not in FEATURE_FOLDERS:
                sys.exit("{} is not a feature folder the build knows".format(
                    os.path.join(folder, name)))
            if FEATURE_FOLDERS[name](board):
                take(os.path.join(folder, name))

    for folder in picker_folders:
        take(folder)
    parts = [part for where in folders for part in glob.glob(os.path.join(where, "[0-9][0-9]_*." + kind))]
    names = [os.path.basename(part) for part in parts]
    twice = sorted({name for name in names if names.count(name) > 1})
    if twice:
        sys.exit("{} is both a shared part and the board's own".format(", ".join(twice)))
    return sorted(parts, key=os.path.basename)


IMPORT = re.compile(r'^import \{([^}]*)\} from "([^"]+)";\n', re.MULTILINE)
EXPORTED = re.compile(r"^export (?:async )?(?:function\*? |var |let |const |class )([A-Za-z_$][\w$]*)",
                      re.MULTILINE)

ESBUILD = os.path.join("tools", "picker", "node_modules", ".bin", "esbuild")


def script_order(parts):
    """The board's script parts in the order they load: by number, except that a part always
    comes after every part it imports. Refuses an import of a part the board does not take, and
    two parts exporting one name."""
    imports = {}
    owners = {}
    for part in parts:
        with open(part, encoding="utf-8") as f:
            text = f.read()
        imports[part] = []
        for names, source in IMPORT.findall(text):
            source = os.path.normpath(os.path.join(os.path.dirname(part), source))
            if source not in parts:
                sys.exit("{} imports {}, which this board does not take".format(part, source))
            imports[part].append(source)
        for name in EXPORTED.findall(text):
            if name in owners:
                sys.exit("{} and {} both export {}".format(owners[name], part, name))
            owners[name] = part
    order = []
    while len(order) < len(parts):
        ready = [part for part in parts if part not in order and
                 all(source in order for source in imports[part])]
        if not ready:
            sys.exit("the picker's parts import each other in a circle: " +
                     ", ".join(part for part in parts if part not in order))
        order.append(ready[0])
    return order


def esbuild(repo_dir, text, *options):
    """text run through the picker's pinned esbuild."""
    tool = os.path.join(repo_dir, ESBUILD)
    if not os.path.exists(tool):
        sys.exit("esbuild is missing: npm ci --prefix tools/picker")
    done = subprocess.run([tool, "--log-level=warning", "--charset=ascii"] + list(options),
                          input=text.encode("utf-8"), capture_output=True, cwd=repo_dir)
    if done.returncode:
        sys.exit(done.stderr.decode("utf-8", "replace"))
    return done.stdout.decode("ascii")


def picker_pages(board_dir, repo_dir, version):
    """The board's picker twice from page.html and the parts: the page the repository keeps,
    which loads the parts as they are, and the page the drive carries, every part minified into
    it."""
    with open(os.path.join(board_dir, "editor", DESCRIPTION_NAME), encoding="utf-8") as f:
        board = json.load(f)
    check_board(board_dir, board)
    shared = os.path.join(repo_dir, SHARED_PARTS)
    own = os.path.join(board_dir, "editor", "picker")
    editor_dir = os.path.join(board_dir, "editor")
    with open(os.path.join(shared, "page.html"), encoding="utf-8") as f:
        page = f.read()
    folders = [shared] + ([own] if os.path.isdir(own) else [])
    page = page.replace("__BOARD_NAME__", board["name"]).replace("__VERSION__", version)
    page = page.replace("__BUILD__", json.dumps({"board": board, "version": version}, indent=1))
    styles = [os.path.normpath(part) for part in board_parts(folders, board, "css")]
    scripts = script_order([os.path.normpath(part) for part in board_parts(folders, board)])

    def href(part):
        return os.path.relpath(part, editor_dir).replace(os.sep, "/")

    links = "".join('<link rel="stylesheet" href="{}">\n'.format(href(part)) for part in styles)
    loads = "".join('import * as part{} from "{}";\n'.format(at, href(part))
                    for at, part in enumerate(scripts))
    exposed = ("for (const part of [{}]) {{\n"
               "  for (const name of Object.keys(part)) {{\n"
               "    if ([window, Window.prototype, EventTarget.prototype].some(holder => Object.hasOwn(holder, name))) continue;\n"
               "    Object.defineProperty(window, name, {{get: () => part[name]}});\n"
               "  }}\n"
               "}}\n").format(", ".join("part{}".format(at) for at in range(len(scripts))))
    kept = (page.replace("__STYLES__\n", links) +
            '<script type="module">\n' + loads + exposed + "</script>\n</body>\n</html>\n")

    css = ""
    for part in styles:
        with open(part, encoding="utf-8") as f:
            css += f.read()
    entry = "".join('import "./{}";\n'.format(os.path.relpath(part, repo_dir).replace(os.sep, "/"))
                    for part in scripts)
    script = esbuild(repo_dir, entry, "--bundle", "--format=iife", "--minify",
                     "--sourcefile=picker.js")
    style = esbuild(repo_dir, css, "--loader=css", "--minify")
    shipped = (page.replace("__STYLES__\n", "<style>" + style.strip() + "</style>\n") +
               "<script>" + script.strip() + "</script>\n</body>\n</html>\n")

    for text in (kept, shipped):
        left = sorted(set(re.findall(r"__[A-Z_]+__", text)))
        if left:
            sys.exit("picker.html has {} unfilled".format(", ".join(left)))
    return kept, shipped


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
    # A board with no sensor connector has nothing to say sensor= about, and no triggers
    sensor = bool(board.get("sensor"))
    if not sensor:
        board_settings.pop("sensor", None)
    vocabulary = autofx.vocabulary

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
        "triggers": {name: list(triggers) for name, triggers in vocabulary.TRIGGERS.items()}
                    if sensor else {},
        "triggers_fixed": list(vocabulary.TRIGGERS_FIXED),
        "trigger_steps": list(vocabulary.TRIGGER_STEPS),
        "trigger_timing": list(vocabulary.TRIGGER_TIMING),
        "board": own,
    }
    return ("// Generated from the autofx tables. Do not edit.\n"
            "var CATALOGUE = " + json.dumps(tables, indent=1) + ";\n")


def stamp_style(name):
    """The comment a page's stamp is written as, a script's or a page's."""
    return STAMP_SCRIPT if name.startswith("CATALOGUE") else STAMP_HTML


def stamp(name, text):
    """The last line a page ends with on the drive, the hash of its content."""
    return stamp_style(name).format(hashlib.sha256(text.encode("ascii")).hexdigest()[:STAMP_DIGITS])


def embed(name, text, shell=False):
    """One page as a tuple of its length, its two ends and its zlib stream.

    A shelled page adds its shell's opening and closing, and its length and ends are those of
    the shell as the drive will hold it. Either way the page ends with stamp(), inside the
    stream for a plain page and after the closing for a shelled one.
    """
    if not text.isascii():
        stray = sorted({c for c in text if not c.isascii()})
        sys.exit("{} contains {}, and it has to be ASCII to reach the drive a "
                 "piece at a time".format(name, ", ".join(repr(c) for c in stray)))
    if not shell:
        drive = text + stamp(name, text)
        packed = zlib.compress(drive.encode("ascii"), 9)
        lines = ["    {!r}".format(packed[at:at + BYTES_PER_LINE])
                 for at in range(0, len(packed), BYTES_PER_LINE)]
        return "{} = ({}, {!r}, {!r}, (\n{}\n))\n".format(
            name, len(drive), drive[:EDGE], drive[-EDGE:], "\n".join(lines))
    packed = zlib.compress(text.encode("ascii"), 9)
    lines = ["    {!r}".format(packed[at:at + BYTES_PER_LINE])
             for at in range(0, len(packed), BYTES_PER_LINE)]
    opening, closing = shell_ends(text)
    closing += stamp(name, text)
    drive = opening + base64.b64encode(packed).decode("ascii") + closing
    return "{} = ({}, {!r}, {!r}, (\n{}\n), {!r}, {!r})\n".format(
        name, len(drive), drive[:EDGE], drive[-EDGE:], "\n".join(lines),
        opening.encode("ascii"), closing.encode("ascii"))


def shell_ends(text):
    """The opening and closing of a page's shell, with the page's title and icon."""
    title = re.search(r"<title>(.*?)</title>", text)
    icon = re.search(r'<link rel="icon"[^>]*>\n', text)
    return (SHELL_OPENING.format(title.group(1) if title else "", icon.group(0) if icon else ""),
            SHELL_CLOSING)


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
        # A plain page carries its stamp in the stream, which the page itself goes without
        if name not in shelled:
            text = text[:text.rfind(stamp_style(name).split("{}")[0])]
        if not drive.endswith(stamp(name, text)):
            sys.exit("{} does not end with the hash of its content".format(name))
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
    parser.add_argument("--release", metavar="VERSION",
                        help="the release being built, which must be picofx's version")
    parser.add_argument("board_dir", help="a board directory holding editor/")
    args = parser.parse_args()

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    version = shown_version(repo_dir, args.release)
    editor_dir = os.path.join(args.board_dir, "editor")
    module = os.path.join(args.board_dir, "fx_libs", MODULE_NAME)

    # What the generated files should hold, the picker and catalogue being generated as well as
    # embedded. The catalogue is the autofx tables the board's firmware carries
    with open(os.path.join(editor_dir, DESCRIPTION_NAME), encoding="utf-8") as f:
        board = json.load(f)
    catalogue_path = os.path.join(editor_dir, "catalogue.js")
    kept, shipped = picker_pages(args.board_dir, repo_dir, version)
    generated = {os.path.join(editor_dir, "picker.html"): kept,
                 catalogue_path: catalogue(repo_dir, args.board_dir, board)}
    if args.release:
        check_release_branch(repo_dir)

    # A board with no FX drive modules carries no FX drive, so it takes the pages alone
    if not os.path.isdir(os.path.dirname(module)):
        build_page_only(generated, args.check)
        return

    sources = {"CATALOGUE": generated[catalogue_path],
               "PICKER": shipped}
    with open(os.path.join(repo_dir, SHARED_EDITOR), encoding="utf-8", newline="") as f:
        sources["EDITOR"] = f.read().replace("__BOARD_NAME__", board["name"]).replace(
            "__VERSION__", version)
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
