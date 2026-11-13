import re

import pytest
from conftest import BOARDS
from playwright.sync_api import expect


def split_into_scenes(page):
    page.get_by_role("button", name="split into scenes", exact=True).click()


def scene_tabs(page):
    return page.get_by_role("tablist", name="Scenes").get_by_role("tab")


@pytest.mark.parametrize("board", BOARDS)
def test_scenes_are_added_switched_and_removed(opened, board):
    page = opened(board)
    expect(page.get_by_role("tablist", name="Scenes")).to_have_count(0)

    split_into_scenes(page)
    expect(scene_tabs(page)).to_have_count(2)
    expect(page.get_by_role("tab", name="Scene 1")).to_have_attribute("aria-selected", "true")

    page.get_by_role("button", name="another scene").click()
    expect(scene_tabs(page)).to_have_count(3)
    expect(page.get_by_role("tab", name="Scene 2")).to_have_attribute("aria-selected", "true")
    expect(page.locator("#sceneBody")).to_have_attribute("aria-labelledby", "sceneTab1")

    page.get_by_role("tab", name="Always on").click()
    expect(page.get_by_role("tab", name="Always on")).to_have_attribute("aria-selected", "true")
    expect(page.locator("#sceneTabRow")).to_contain_text("Always on plays under every scene")
    expect(page.locator("#sceneTabRow")).to_contain_text("Under 2 scenes")

    page.get_by_role("tab", name="Scene 1").click()
    page.get_by_role("button", name="Remove scene").click()
    expect(scene_tabs(page)).to_have_count(2)
    page.get_by_role("button", name="Remove scene").click()
    expect(page.get_by_role("tablist", name="Scenes")).to_have_count(0)
    expect(page.locator("#sceneTabRow")).to_be_hidden()
    assert not [line for line in page.evaluate("currentText()").split("\n") if line.startswith("[")]
    assert page.errors == []


@pytest.mark.parametrize("board", BOARDS)
def test_arrow_keys_move_between_scene_tabs(opened, board):
    page = opened(board)
    split_into_scenes(page)
    page.get_by_role("button", name="another scene").click()
    page.get_by_role("tab", name="Scene 2").focus()
    page.keyboard.press("ArrowLeft")
    expect(page.get_by_role("tab", name="Scene 1")).to_have_attribute("aria-selected", "true")
    expect(page.get_by_role("tab", name="Scene 1")).to_be_focused()
    page.keyboard.press("Home")
    expect(page.get_by_role("tab", name="Always on")).to_be_focused()
    page.keyboard.press("End")
    expect(page.get_by_role("tab", name="Scene 2")).to_have_attribute("aria-selected", "true")
    expect(page.get_by_role("tab", name="Scene 2")).to_have_attribute("tabindex", "0")
    expect(page.get_by_role("tab", name="Always on")).to_have_attribute("tabindex", "-1")
    assert page.errors == []


def test_dragging_a_scene_tab_reorders_the_scenes(opened):
    page = opened("PIMORONI_MIGHTYFX")
    split_into_scenes(page)
    page.get_by_role("button", name="another scene").click()
    page.get_by_role("tab", name="Scene 2").drag_to(page.get_by_role("tab", name="Scene 1"))
    expect(scene_tabs(page)).to_have_text([re.compile("^Always on"), re.compile("^Scene 2"),
                                          re.compile("^Scene 1")])
    expect(page.get_by_role("tab", name="Scene 2")).to_have_attribute("aria-selected", "true")
    assert page.evaluate("state.scenes.map(function (scene) { return scene.name; })") == ["Scene 2",
                                                                                         "Scene 1"]
    assert page.errors == []


@pytest.mark.parametrize("board", BOARDS)
def test_scene_settings_change_the_file(opened, board):
    page = opened(board)
    split_into_scenes(page)
    page.get_by_role("button", name="another scene").click()
    settings = page.get_by_role("group", name="Scene settings")

    name = settings.get_by_role("textbox", name="Scene name")
    name.fill("Party: time")
    expect(name).to_have_value("Party time")
    expect(page.get_by_role("tab", name="Party time")).to_be_visible()
    expect(page.locator("#preview")).to_contain_text("[Party time")
    name.press("Tab")

    seconds = settings.get_by_role("spinbutton", name="Seconds")
    seconds.fill("25")
    seconds.press("Tab")
    expect(page.locator("#preview")).to_contain_text("[Party time: 25s]")
    expect(page.get_by_role("tab", name="Party time")).to_contain_text("25s")

    settings.get_by_role("combobox", name="Scene after").select_option(label="itself")
    expect(page.locator("#preview")).to_contain_text("[Party time: 25s restart then Party time]")
    expect(settings.get_by_role("button", name="Restart")).to_be_disabled()
    expect(settings.get_by_role("button", name="Restart")).to_have_attribute("aria-pressed", "true")
    settings.get_by_role("combobox", name="Scene after").select_option(label="the next scene")

    settings.get_by_role("button", name="Restart").click()
    expect(page.get_by_role("group", name="Scene settings").get_by_role("button", name="Restart")) \
        .to_have_attribute("aria-pressed", "true")
    expect(page.locator("#preview")).to_contain_text("[Party time: 25s restart]")

    page.get_by_role("group", name="Scene settings").get_by_role("combobox", name="How the scene ends") \
        .select_option("waits")
    expect(page.get_by_role("group", name="Scene settings").get_by_role("spinbutton")).to_have_count(0)
    expect(page.get_by_role("tab", name="Party time")).to_contain_text("waits")

    page.get_by_role("group", name="Scene settings").get_by_role("textbox", name="Scene name") \
        .fill("Scene 1")
    expect(page.get_by_role("group", name="Scene settings").get_by_role("textbox", name="Scene name")) \
        .to_have_attribute("aria-invalid", "true")
    expect(page.locator("#sceneTabRow > p")).to_have_text("Another scene is called Scene 1")
    page.get_by_role("group", name="Scene settings").get_by_role("textbox", name="Scene name").press("Tab")
    expect(page.get_by_role("tab", name="Party time")).to_be_visible()
    assert page.errors == []


@pytest.mark.parametrize("board", BOARDS)
def test_page_tabs_switch_between_effects_and_programs(opened, board):
    page = opened(board)
    page.get_by_role("button", name="Programs", exact=True).click()
    expect(page.locator("#sceneBody")).to_be_hidden()
    expect(page.locator("#floatBar > p + p")).to_have_text("Programs")
    page.get_by_role("button", name=re.compile("^Effects")).click()
    expect(page.locator("#sceneBody")).to_be_visible()
    expect(page.locator("#floatBar > p + p")).to_have_text("Effects")
    assert page.errors == []


@pytest.mark.parametrize("board", BOARDS)
def test_preview_shows_the_file(opened, board):
    page = opened(board)
    page.get_by_text("The file to be saved").click()
    preview = page.locator("#preview")
    expect(preview).to_be_visible()
    assert preview.inner_text() == page.evaluate("currentText()")
    split_into_scenes(page)
    assert preview.inner_text() == page.evaluate("currentText()")
    assert page.errors == []


def test_preview_marks_lines_the_board_reported(opened):
    page = opened("PIMORONI_MIGHTYFX")
    page.get_by_text("The file to be saved").click()
    text = page.evaluate("currentText()")
    line = next(at for at, one in enumerate(text.split("\n")) if one and not one.startswith("#")) + 1
    page.evaluate("([said, about]) => takeAnswer(said, about)",
                  ["line %d: unknown effect" % line, text])
    expect(page.locator("#preview mark")).to_have_count(1)
    expect(page.locator("#preview em")).to_have_text("unknown effect")
    expect(page.locator("#previewNote")).to_be_hidden()
    read = text.split("\n")
    read[line - 1] += " colour=red"
    page.evaluate("([said, about]) => takeAnswer(said, about)",
                  ["line %d: unknown effect" % line, "\n".join(read)])
    expect(page.locator("#previewNote")).to_have_text("One reported line has since changed.")
    expect(page.locator("#preview mark")).to_have_count(0)
    assert page.errors == []


def test_banner_says_what_the_page_says(opened):
    page = opened("PIMORONI_MIGHTYFX")
    status = page.get_by_role("status")
    page.evaluate("banner('The board reported problems:', true, 'line 3: nope')")
    expect(status).to_have_attribute("data-tone", "warn")
    expect(status.locator("p")).to_have_text("The board reported problems:")
    expect(status.locator("pre")).to_have_text("line 3: nope")
    expect(page.locator("#floatBar > p > button")).to_have_text("The board reported problems:")
    page.evaluate("banner('')")
    expect(status).to_be_hidden()
    expect(page.locator("#floatBar > p > button")).to_be_hidden()
    assert page.errors == []


@pytest.mark.parametrize("board", BOARDS)
def test_save_menu_opens_and_closes(opened, board):
    page = opened(board)
    arrow = page.get_by_role("button", name="Save settings")
    menu = page.get_by_role("group", name="Save settings")
    expect(menu).to_be_hidden()
    arrow.click()
    expect(arrow).to_have_attribute("aria-expanded", "true")
    expect(menu.get_by_role("checkbox")).to_have_count(2)
    reload = menu.get_by_role("checkbox", name=re.compile("Play saves without an eject"))
    was = reload.is_checked()
    reload.click()
    expect(menu).to_be_visible()
    expect(menu.get_by_role("checkbox", name=re.compile("Play saves without an eject"))) \
        .to_be_checked(checked=not was)
    page.keyboard.press("Escape")
    expect(menu).to_be_hidden()
    expect(arrow).to_have_attribute("aria-expanded", "false")
    expect(arrow).to_be_focused()
    arrow.click()
    page.locator("main").click(position={"x": 5, "y": 5})
    expect(menu).to_be_hidden()
    assert page.errors == []


@pytest.mark.parametrize("board", BOARDS)
def test_float_bar_takes_the_drive_buttons_on_scroll(opened, board):
    page = opened(board)
    split_into_scenes(page)
    page.set_viewport_size({"width": 1280, "height": 480})
    bar = page.locator("#floatBar")
    expect(bar).to_have_attribute("aria-hidden", "true")
    page.mouse.wheel(0, 2000)
    expect(bar).to_have_attribute("data-shown", "")
    expect(bar.get_by_role("button", name="Open FX drive")).to_be_visible()
    expect(page.locator("#floatBar > p + p")).to_have_text("EffectsScene 1")
    expect(page.locator("header [data-standin]")).to_have_count(1)
    page.evaluate("window.scrollTo(0, 0)")
    expect(bar).to_have_attribute("aria-hidden", "true")
    expect(page.locator("header").get_by_role("button", name="Open FX drive")).to_be_visible()
    expect(page.locator("[data-standin]")).to_have_count(0)
    assert page.errors == []
