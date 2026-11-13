import base64
import os
import re

import pytest
from conftest import REPO, picker_path

EXAMPLES = {"PIMORONI_MIGHTYFX": "mighty_fx", "PIMORONI_TINYFX": "tiny_fx",
            "PIMORONI_PLASMA2350": "plasma"}

GITHUB = re.compile(r"^https://raw\.githubusercontent\.com/pimoroni/picofx/refs/heads/.+?/(examples/.*)$")

OWN_PROGRAM = '''"""
Program: My blinker
Blinks the first output.
"""
from mighty import MightyFX
mighty = MightyFX()
mighty.outputs[0].on()
'''

ARGV_PROGRAM = '''"""
Takes what it is given.
"""
import sys
print(sys.argv)
'''

FAKE_DRIVE = """
files => {
  function bytesOf(text) {
    var raw = atob(text);
    var bytes = new Uint8Array(raw.length);
    for (var at = 0; at < raw.length; at++) bytes[at] = raw.charCodeAt(at);
    return bytes;
  }
  function missing(name) { return new DOMException(name + " is not here", "NotFoundError"); }
  class FakeFile {
    constructor(name, bytes) {
      this.kind = "file";
      this.name = name;
      this.bytes = bytes || new Uint8Array(0);
      this.modified = 1;
    }
    async getFile() { return new File([this.bytes], this.name, {lastModified: this.modified}); }
    async createWritable() {
      var file = this;
      var parts = [];
      return {
        async write(data) {
          if (typeof data === "string") data = new TextEncoder().encode(data);
          else if (data instanceof Blob) data = new Uint8Array(await data.arrayBuffer());
          parts.push(data);
        },
        async close() {
          file.bytes = new Uint8Array(await new Blob(parts).arrayBuffer());
          file.modified++;
        }
      };
    }
  }
  class FakeFolder {
    constructor(name) {
      this.kind = "directory";
      this.name = name;
      this.children = new Map();
    }
    async *entries() { for (var pair of Array.from(this.children)) yield pair; }
    async *keys() { for (var name of Array.from(this.children.keys())) yield name; }
    async *values() { for (var one of Array.from(this.children.values())) yield one; }
    async getFileHandle(name, options) {
      var found = this.children.get(name);
      if (!found && options && options.create) this.children.set(name, found = new FakeFile(name));
      if (!found || found.kind !== "file") throw missing(name);
      return found;
    }
    async getDirectoryHandle(name, options) {
      var found = this.children.get(name);
      if (!found && options && options.create) this.children.set(name, found = new FakeFolder(name));
      if (!found || found.kind !== "directory") throw missing(name);
      return found;
    }
    async removeEntry(name) {
      if (!this.children.delete(name)) throw missing(name);
    }
    async queryPermission() { return "granted"; }
    async requestPermission() { return "granted"; }
  }
  var root = new FakeFolder("FX");
  Object.keys(files).forEach(function (path) {
    var parts = path.split("/");
    var name = parts.pop();
    var folder = root;
    parts.forEach(function (part) {
      if (!folder.children.has(part)) folder.children.set(part, new FakeFolder(part));
      folder = folder.children.get(part);
    });
    folder.children.set(name, new FakeFile(name, bytesOf(files[path])));
  });
  window.fakeDrive = root;
  window.showDirectoryPicker = async function () { return root; };
}
"""


def examples_of(board, keep=None):
    base = os.path.join(REPO, "examples", EXAMPLES[board])
    found = {}
    for top, folders, names in os.walk(base):
        folders.sort()
        for name in sorted(names):
            path = os.path.relpath(os.path.join(top, name), base).replace(os.sep, "/")
            if not path.startswith("examples/") or path.endswith("index.json"):
                continue
            if keep and not keep(path):
                continue
            with open(os.path.join(top, name), "rb") as f:
                found[path] = f.read()
    return found


def encoded(files):
    return {path: base64.b64encode(data if isinstance(data, bytes) else data.encode()).decode()
            for path, data in files.items()}


def serve_github(page, board):
    base = os.path.join(REPO, "examples", EXAMPLES[board])

    def answer(route):
        found = GITHUB.match(route.request.url)
        path = os.path.join(base, found.group(1)[len("examples/" + EXAMPLES[board]) + 1:]) if found else None
        if not path or not os.path.isfile(path):
            route.fulfill(status=404, body="")
            return
        with open(path, "rb") as f:
            route.fulfill(status=200, body=f.read())

    page.route(GITHUB, answer)


def open_drive(browser, board, files, online=True):
    page = browser.new_page(viewport={"width": 1280, "height": 1000})
    page.errors = []
    page.on("pageerror", lambda error: page.errors.append(str(error)))
    page.on("console", lambda message: message.type == "error" and page.errors.append(message.text))
    if online:
        serve_github(page, board)
    else:
        page.route(GITHUB, lambda route: route.abort())
    page.goto("file://" + picker_path(board))
    page.wait_for_function("typeof currentText === 'function'")
    if files is not None:
        drive = {"effects.txt": "board:\n"}
        drive.update(files)
        page.evaluate(FAKE_DRIVE, encoded(drive))
        page.get_by_role("button", name="Open FX drive").click()
        page.wait_for_function("programsKnown && !programsReading")
    return page


@pytest.fixture
def driven(browser):
    pages = []

    def make(board, files, online=True):
        page = open_drive(browser, board, files, online)
        pages.append(page)
        return page

    yield make
    for page in pages:
        page.close()


DISCOVERED = {"PIMORONI_MIGHTYFX": ("examples/programs/showcase/retro_displays/",
                                    ["Lamp matrix", "Nixie tube"]),
              "PIMORONI_TINYFX": ("examples/programs/audio/", ["Fair use encounters", "Race start"])}

CHANGED = {"PIMORONI_MIGHTYFX": "examples/programs/showcase/transport_signs/departure_board.py",
           "PIMORONI_TINYFX": "examples/programs/showcase/rescue_vehicle.py"}

DISCOVERING = tuple(DISCOVERED)


def own_programs():
    return {"my_blinker.py": OWN_PROGRAM, "programs/argv_test.py": ARGV_PROGRAM}


def drive_for(board, changed=False):
    files = own_programs()
    if board in DISCOVERED:
        files.update(examples_of(board, lambda path: not path.startswith(DISCOVERED[board][0])))
        if changed:
            files[CHANGED[board]] = files[CHANGED[board]] + b"\n# Changed on the drive\n"
    return files


def to_programs(page):
    page.get_by_role("navigation", name="Pages").get_by_role("button", name=re.compile("^Programs")).click()
    return page.get_by_role("region", name="Programs")


def card(region, name):
    return region.get_by_role("button", name=name, exact=True)


def board_line(page):
    lines = [line for line in page.evaluate("currentText()").split("\n") if line.startswith("board:")]
    return lines[0] if lines else ""


@pytest.mark.parametrize("board", sorted(EXAMPLES))
def test_programs_before_the_drive_opens(opened, board):
    page = opened(board)
    region = to_programs(page)
    hero = region.get_by_role("article", name="Chosen program")
    assert hero.get_by_role("heading", name="Choose a program").is_visible()
    assert region.get_by_text("Open the FX drive to see the programs on it.").is_visible()
    assert "program=" not in page.evaluate("currentText()")
    page.get_by_role("navigation", name="Pages").get_by_role("button", name="Effects").click()
    assert region.is_hidden()
    assert page.errors == []


@pytest.mark.parametrize("board", sorted(EXAMPLES))
def test_choosing_a_program(driven, board):
    page = driven(board, drive_for(board))
    region = to_programs(page)
    blinker = card(region, "My blinker")
    assert blinker.get_attribute("aria-pressed") == "false"
    blinker.click()
    assert blinker.get_attribute("aria-pressed") == "true"
    hero = region.get_by_role("article", name="Chosen program")
    assert hero.get_by_role("heading", name="My blinker").is_visible()
    assert board_line(page).startswith("board: program=my_blinker.py")
    tab = page.get_by_role("navigation", name="Pages").get_by_role("button", name=re.compile("^Programs"))
    assert "My blinker" in tab.inner_text()
    hero.get_by_role("button", name="Choose none").click()
    assert "program=" not in board_line(page)
    blinker.click()
    blinker.click()
    assert "program=" not in board_line(page)
    blinker.click()
    page.get_by_role("navigation", name="Pages").get_by_role("button", name="Effects").click()
    assert "program=" not in board_line(page)
    assert page.errors == []


@pytest.mark.parametrize("board", sorted(EXAMPLES))
def test_typed_arguments(driven, board):
    page = driven(board, drive_for(board))
    region = to_programs(page)
    card(region, "Argv test").click()
    arguments = region.get_by_role("group", name="Arguments")
    arguments.get_by_role("button", name="+ an argument").click()
    arguments.get_by_role("button", name="+ an argument").click()
    arguments.get_by_role("textbox", name="Argument 1").fill("one")
    arguments.get_by_role("textbox", name="Argument 1").press("Tab")
    arguments.get_by_role("textbox", name="Argument 2").fill("two words")
    arguments.get_by_role("textbox", name="Argument 2").press("Tab")
    assert board_line(page).startswith('board: program=programs/argv_test.py args=one|"two words"')
    arguments.get_by_role("button", name="Remove Argument 1").click()
    assert board_line(page).startswith('board: program=programs/argv_test.py args="two words"')
    assert arguments.get_by_role("textbox").count() == 1
    assert page.errors == []


def test_chosen_arguments(driven):
    page = driven("PIMORONI_MIGHTYFX", drive_for("PIMORONI_MIGHTYFX"))
    region = to_programs(page)
    card(region, "Bus departures").click()
    assert board_line(page).startswith("board: program=examples/programs/showcase/transport_signs/"
                                       "bus_departures.py")
    assert "args=" not in board_line(page)
    arguments = region.get_by_role("group", name="Arguments")
    arguments.get_by_role("combobox", name="Rotation").select_option("90")
    assert "args=2.8|90" in board_line(page)
    arguments.get_by_role("combobox", name="Rotation").select_option("0")
    assert "args=" not in board_line(page)
    assert page.errors == []


def test_filtering_by_what_is_to_hand(driven):
    page = driven("PIMORONI_MIGHTYFX", drive_for("PIMORONI_MIGHTYFX"))
    region = to_programs(page)
    chips = region.get_by_role("group", name="Show programs using")
    screen = chips.get_by_role("button", name="screen", exact=True)
    assert screen.get_attribute("aria-pressed") == "true"
    assert card(region, "Bus departures").is_visible()
    screen.click()
    assert screen.get_attribute("aria-pressed") == "false"
    chips.get_by_role("button", name="2 screens", exact=True).click()
    chips.get_by_role("button", name="hub", exact=True).click()
    assert card(region, "Bus departures").count() == 0
    assert card(region, "My blinker").is_visible()
    chips.get_by_role("button", name="none", exact=True).click()
    assert chips.get_by_role("button", pressed=True).count() == 0
    chips.get_by_role("button", name="all", exact=True).click()
    assert chips.get_by_role("button", pressed=False).count() == 2
    assert card(region, "Bus departures").is_visible()
    assert page.errors == []


@pytest.mark.parametrize("board", sorted(EXAMPLES))
def test_folding_a_group(driven, board):
    page = driven(board, drive_for(board))
    region = to_programs(page)
    fold = region.get_by_role("button", name=re.compile("^On the drive"))
    assert fold.get_attribute("aria-expanded") == "true"
    fold.click()
    assert fold.get_attribute("aria-expanded") == "false"
    assert card(region, "My blinker").count() == 0
    fold.click()
    assert card(region, "My blinker").is_visible()
    assert page.errors == []


@pytest.mark.parametrize("board", sorted(EXAMPLES))
def test_copying_and_deleting_your_own(driven, board):
    page = driven(board, drive_for(board))
    page.on("dialog", lambda dialog: dialog.accept())
    region = to_programs(page)
    card(region, "My blinker").click()
    region.get_by_role("button", name="Duplicate my_blinker.py in the programs folder").click()
    page.wait_for_function("PROGRAMS.some(function (one) { return one.path === 'programs/my_blinker_2.py'; })")
    assert card(region, "My blinker").count() == 2
    assert board_line(page).startswith("board: program=programs/my_blinker_2.py")
    region.get_by_role("button", name="Delete my_blinker_2.py from the FX drive").click()
    page.wait_for_function("!PROGRAMS.some(function (one) { return one.path === 'programs/my_blinker_2.py'; })")
    assert card(region, "My blinker").count() == 1
    assert "program=" not in board_line(page)
    assert page.evaluate("fakeDrive.children.get('programs').children.has('my_blinker_2.py')") is False
    assert page.errors == []


def test_no_discover_without_examples(driven):
    page = driven("PIMORONI_PLASMA2350", drive_for("PIMORONI_PLASMA2350"))
    region = to_programs(page)
    assert card(region, "My blinker").is_visible()
    assert region.get_by_role("button", name=re.compile("^Discover")).count() == 0
    assert page.errors == []


@pytest.mark.parametrize("board", DISCOVERING)
def test_discovering_programs(driven, board):
    page = driven(board, drive_for(board))
    region = to_programs(page)
    examples = region.get_by_role("region", name="Examples")
    examples.get_by_role("button", name=re.compile("^Discover more example programs")).click()
    sheet = page.get_by_role("dialog", name="More example programs")
    first, second = DISCOVERED[board][1]
    sheet.get_by_role("checkbox", name="Choose " + first).click()
    sheet.get_by_role("checkbox", name="Choose " + second).click()
    assert sheet.get_by_text("2 examples chosen").is_visible()
    sheet.get_by_role("button", name="Download 2").click()
    page.wait_for_function("!discover.busy || !Object.keys(discover.busy).length")
    sheet.get_by_text("Downloaded 2 examples.").wait_for()
    assert sheet.get_by_role("checkbox", name="Choose " + first).count() == 0
    sheet.get_by_role("button", name="\u2039 Back").click()
    assert sheet.is_hidden()
    assert card(region, first).is_visible()
    assert card(region, second).is_visible()
    assert "program=" not in board_line(page)
    assert page.errors == []


@pytest.mark.parametrize("board", DISCOVERING)
def test_downloading_one_chooses_it(driven, board):
    page = driven(board, drive_for(board))
    region = to_programs(page)
    region.get_by_role("button", name=re.compile("^Discover more example programs")).click()
    sheet = page.get_by_role("dialog", name="More example programs")
    name = DISCOVERED[board][1][0]
    offer = sheet.get_by_role("listitem").filter(has=page.get_by_role("checkbox", name="Choose " + name))
    offer.get_by_role("button").first.click()
    assert offer.get_by_role("button").first.get_attribute("aria-pressed") == "true"
    sheet.get_by_role("button", name="Download", exact=True).click()
    sheet.get_by_text(re.compile("^Downloaded ")).wait_for()
    page.keyboard.press("Escape")
    assert sheet.is_hidden()
    assert card(region, name).get_attribute("aria-pressed") == "true"
    assert "program=" + DISCOVERED[board][0] in board_line(page)
    assert page.errors == []


@pytest.mark.parametrize("board", DISCOVERING)
def test_updating_a_changed_example(driven, board):
    page = driven(board, drive_for(board, changed=True))
    region = to_programs(page)
    examples = region.get_by_role("region", name="Examples")
    examples.get_by_role("button", name="Check for updates").click()
    update = examples.get_by_role("button", name="Update all")
    page.wait_for_function("discover.program.status === 'done'")
    assert update.is_enabled()
    update.click()
    kept = "programs/" + CHANGED[board].split("/")[-1]
    examples.get_by_text(re.compile("Your changed copy is kept as " + re.escape(kept))).wait_for()
    assert page.evaluate("fakeDrive.children.get('programs').children.has('%s')" % kept.split("/")[1])
    assert page.errors == []


@pytest.mark.parametrize("board", DISCOVERING)
def test_discover_offline(driven, board):
    page = driven(board, drive_for(board), online=False)
    region = to_programs(page)
    region.get_by_role("button", name=re.compile("^Discover more example programs")).click()
    sheet = page.get_by_role("dialog", name="More example programs")
    sheet.get_by_role("status").get_by_text("Could not connect. Check this computer is online.").wait_for()
    sheet.get_by_role("button", name="\u2039 Back").click()
    assert sheet.is_hidden()
    assert region.get_by_text("Could not connect. Check this computer is online.").is_visible()
