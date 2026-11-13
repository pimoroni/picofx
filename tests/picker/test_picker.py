import glob
import os

import pytest
from conftest import BOARDS, HERE

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
