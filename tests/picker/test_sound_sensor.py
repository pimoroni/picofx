import re

import pytest

BOARDS = ("PIMORONI_MIGHTYFX", "PIMORONI_TINYFX")

DRIVE = """
(function () {
  state.fileHandle = {};
  state.dirHandle = {};
  state.scanned = true;
  state.sounds = ["ambience.wav", "chimes.wav"];
  state.sounds.forEach(function (name, at) {
    var bars = [];
    for (var i = 0; i < 96; i++) bars.push((i % 7) / 7);
    state.soundInfo[name] = {seconds: 3 + at, bars: bars};
  });
  draw();
})()
"""


def open_tab(opened, board, panel, *steps):
    page = opened(board)
    page.click("#ledTabs [data-panel=%s]" % panel)
    for step in steps:
        page.evaluate(step)
    return page


def text(page):
    return page.evaluate("currentText()")


def sound_tab(page):
    return page.get_by_role("region", name="Sound")


def sensor_tab(page):
    return page.get_by_role("region", name="Sensor")


@pytest.mark.parametrize("board", BOARDS)
def test_choose_loop_and_quieten_a_sound(opened, board):
    page = open_tab(opened, board, "soundPanel", DRIVE)
    tab = sound_tab(page)
    loop = tab.get_by_role("button", name="Loop")
    assert loop.is_disabled()

    tile = tab.get_by_role("button", name=re.compile(r"^chimes\.wav"))
    tile.click()
    assert tile.get_attribute("aria-pressed") == "true"
    assert "audio: wav file=chimes.wav" in text(page)

    loop.click()
    assert loop.get_attribute("aria-pressed") == "true"
    assert "audio: wav file=chimes.wav loop=true" in text(page)
    assert "4s, on repeat" in tile.inner_text()

    tab.get_by_role("slider").fill("70")
    assert tab.locator("output").inner_text() == "70%"
    assert "audio: wav file=chimes.wav loop=true volume=70%" in text(page)

    nothing = tab.get_by_role("button", name="Nothing")
    nothing.click()
    assert nothing.get_attribute("aria-pressed") == "true"
    assert "audio:" not in text(page)
    assert page.errors == []


@pytest.mark.parametrize("board", BOARDS)
def test_hear_a_sound_on_the_drive(opened, board):
    page = open_tab(opened, board, "soundPanel", DRIVE)
    tab = sound_tab(page)
    assert tab.get_by_role("button", name="Hear chimes.wav").count() == 0
    page.evaluate("soundHandles['chimes.wav'] = {getFile: async function () { return new Blob([]); }}; draw()")
    hear = tab.get_by_role("button", name="Hear chimes.wav")
    assert hear.get_attribute("aria-pressed") == "false"
    assert hear.get_attribute("title") == "Play chimes.wav here"


@pytest.mark.parametrize("board", BOARDS)
def test_fold_own_sounds(opened, board):
    page = open_tab(opened, board, "soundPanel", DRIVE)
    tab = sound_tab(page)
    heading = tab.get_by_role("button", name=re.compile("your own sounds"))
    assert heading.get_attribute("aria-expanded") == "true"
    heading.click()
    assert heading.get_attribute("aria-expanded") == "false"
    assert tab.get_by_role("button", name=re.compile(r"^chimes\.wav")).count() == 0
    heading.click()
    assert tab.get_by_role("button", name=re.compile(r"^chimes\.wav")).count() == 1


@pytest.mark.parametrize("board", BOARDS)
def test_scene_plays_always_on_sound_or_silence(opened, board):
    page = open_tab(opened, board, "soundPanel", DRIVE,
                    "addScene(); addScene(); switchTo(-1); state.sound = 'ambience.wav'; switchTo(1)")
    tab = sound_tab(page)
    assert "plays on through this scene" in tab.locator("p").first.inner_text()
    assert tab.get_by_role("group", name="How it plays").get_attribute("disabled") == ""
    assert tab.get_by_role("slider").is_disabled()
    under = tab.locator("li", has=page.get_by_role("button", name=re.compile(r"^ambience\.wav")))
    assert under.get_attribute("data-under") == ""

    silence = tab.get_by_role("button", name="Silence")
    silence.click()
    assert silence.get_attribute("aria-pressed") == "true"
    assert "this scene is silent" in tab.locator("p").first.inner_text()
    assert re.search(r"\[Scene 2: 10s\]\naudio: none\n", text(page))
    assert page.errors == []


@pytest.mark.parametrize("board", BOARDS)
def test_silence_waits_for_always_on_sound(opened, board):
    page = open_tab(opened, board, "soundPanel", DRIVE, "addScene()")
    assert not sound_tab(page).get_by_role("button", name="Silence").is_visible()


@pytest.mark.parametrize("board", BOARDS)
def test_fit_a_remote_and_choose_what_a_button_does(opened, board):
    page = open_tab(opened, board, "sensorPanel")
    tab = sensor_tab(page)
    page.get_by_role("button", name="Edit board").click()
    tab.get_by_role("combobox", name="Sensor").select_option("ir")
    page.get_by_role("button", name="Done").click()
    assert "sensor=ir" in text(page)

    record = tab.get_by_role("combobox", name="Record", exact=True)
    record.select_option(label="Restart the effects")
    assert "remote: record=restart" in text(page)
    assert tab.get_by_role("combobox", name="OK / Stop").count() == 0
    assert "Standby" in tab.locator("li[data-from=fixed]").first.inner_text()

    page.locator("circle[data-button=LEFT]").click()
    assert page.evaluate("document.activeElement.closest('li').dataset.button") == "LEFT"

    tab.get_by_role("listitem").filter(has_text="Anticlockwise").hover()
    assert page.locator("path[data-button=ANTICLOCK]").get_attribute("data-hot") == ""

    tab.get_by_role("button", name="split into scenes").click()
    assert page.evaluate("state.scenes.length") == 1
    assert "Scene: Scene 1" in tab.get_by_role("combobox", name="1 Red").inner_text()
    assert page.errors == []


@pytest.mark.parametrize("board", BOARDS)
def test_scene_changes_a_remote_button(opened, board):
    page = open_tab(opened, board, "sensorPanel",
                    "absorbFile('board: sensor=ir\\n\\n[One]\\nout1: pulse\\n\\n[Two]\\nout1: flash\\n')",
                    "switchTo(1)")
    tab = sensor_tab(page)
    left = tab.get_by_role("listitem").filter(has=page.get_by_role("combobox", name="Left", exact=True))
    assert left.get_attribute("data-from") == "always"
    tab.get_by_role("combobox", name="Left", exact=True).select_option(label="First scene")
    assert left.get_attribute("data-from") is None
    assert re.search(r"\[Two\]\nremote: left=first\nout1: flash", text(page))
    assert page.errors == []


@pytest.mark.parametrize("board", BOARDS)
def test_pir_trigger_waits_and_cancels(opened, board):
    page = open_tab(opened, board, "sensorPanel", "state.sensorKind = 'pir'; draw()")
    starts = sensor_tab(page).get_by_role("group", name="Motion starts")
    starts.get_by_role("combobox", name="Trigger").select_option(label="Restart the effects")
    assert "motion: starts=restart" in text(page)

    cancels = starts.get_by_role("combobox", name="If motion stops first?")
    assert cancels.is_disabled()
    starts.get_by_role("spinbutton", name="after").fill("2")
    starts.get_by_role("spinbutton", name="after").dispatch_event("change")
    assert "motion: starts=restart after=2s" in text(page)

    cancels.select_option(label="finish this first")
    assert "motion: starts=restart after=2s cancel=no" in text(page)
    assert page.errors == []
