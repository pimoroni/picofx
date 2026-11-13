import glob
import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BOARDS = ("PIMORONI_MIGHTYFX", "PIMORONI_TINYFX", "PIMORONI_PLASMA2350")
UPDATING = os.environ.get("PICKER_GOLDEN") == "update"

SCENARIOS = {
    "default": [],
    "cut_and_solid": [
        "cutAt(runs[0], Math.floor(runs[0].lamps.length / 2) - 1)",
        "landLook(runs[0], runs[0].sections.length - 1, 'Solid')",
    ],
    "nothing": [
        "landLook(runs[0], 0, null)",
    ],
    "undo_cut": [
        "cutAt(runs[0], 0)",
        "stepBack(runs[0])",
    ],
    "scene": [
        "addScene()",
        "landLook(runs[0], 0, 'Sparkle')",
    ],
    "fitted_strip": [
        "(function () {"
        " var strip = runs.filter(function (run) { return run.strip; })[0];"
        " if (!strip) return;"
        " stripSet(strip, {there: true, leds: 20}); settle(); draw();"
        " cutAt(strip, 9); landLook(strip, 1, 'Scanner');"
        "})()",
    ],
    "broken_out": [
        "(function () {"
        " var out = BOARD.outputs.findIndex(function (one) {"
        "   return one.kind === 'colour' && one.breaks_out; });"
        " if (out < 0) return;"
        " breakOut(out);"
        " landLook(mono, 0, 'Sparkle');"
        "})()",
    ],
}


def picker_path(board):
    return os.path.join(REPO, "boards", board, "editor", "picker.html")


def corpus(board):
    return sorted(glob.glob(os.path.join(HERE, "corpus", board, "*.txt")))


def golden_path(board, name):
    return os.path.join(HERE, "golden", board, name + ".txt")


def check_golden(board, name, text):
    path = golden_path(board, name)
    if UPDATING:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return
    with open(path, encoding="utf-8") as f:
        assert text == f.read()


@pytest.fixture(scope="session")
def browser():
    with playwright.sync_playwright() as driver:
        channel = os.environ.get("PICKER_BROWSER_CHANNEL") or None
        launched = driver.chromium.launch(channel=channel)
        yield launched
        launched.close()


@pytest.fixture
def opened(browser):
    pages = []

    def open_board(board):
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.errors = []
        page.on("pageerror", lambda error: page.errors.append(str(error)))
        page.on("console", lambda message: message.type == "error" and page.errors.append(message.text))
        page.goto("file://" + picker_path(board))
        page.wait_for_function("typeof currentText === 'function'")
        pages.append(page)
        return page

    yield open_board
    for page in pages:
        page.close()


@pytest.mark.parametrize("board", BOARDS)
@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_scenario(opened, board, scenario):
    page = opened(board)
    for step in SCENARIOS[scenario]:
        page.evaluate(step)
    check_golden(board, "scenario_" + scenario, page.evaluate("currentText()"))
    assert page.errors == []


@pytest.mark.parametrize("board, path", [(board, path) for board in BOARDS for path in corpus(board)],
                         ids=lambda value: os.path.basename(value))
def test_round_trip(opened, board, path):
    page = opened(board)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    page.evaluate("text => absorbFile(text)", text)
    name = "read_" + os.path.splitext(os.path.basename(path))[0]
    check_golden(board, name, page.evaluate("currentText()"))
    assert page.errors == []
