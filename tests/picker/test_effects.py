import re

import pytest

MIGHTY = "PIMORONI_MIGHTYFX"


def saved(page):
    return page.evaluate("currentText()")


def cut_between(page, first, second):
    page.get_by_role("button", name="cut between {} and {}".format(first, second)).click()


def stretch(page, name):
    return page.get_by_role("button", name=name, exact=True)


def pick(page, name):
    stretch(page, name).locator("strong").click()


@pytest.fixture
def mighty(opened):
    page = opened(MIGHTY)
    yield page
    assert page.errors == []


def test_opens_on_the_stretch_settings(mighty):
    assert mighty.get_by_role("heading", name=re.compile("^Rainbow on outputs 1 to 7")).is_visible()
    assert not mighty.locator("#looks").is_visible()


def test_cutting_keeps_the_look_on_both_sides(mighty):
    cut_between(mighty, 4, 5)
    assert stretch(mighty, "Rainbow on outputs 1 to 4").is_visible()
    assert stretch(mighty, "Rainbow on outputs 5 to 7").is_visible()
    assert "out1-4:" in saved(mighty) and "out5-7:" in saved(mighty)


def test_change_look_then_choose_a_card(mighty):
    cut_between(mighty, 4, 5)
    pick(mighty, "Rainbow on outputs 5 to 7")
    mighty.get_by_role("button", name="Change look").click()
    assert mighty.get_by_role("heading", name=re.compile("^Choose a look for outputs 5 to 7")).is_visible()
    mighty.get_by_role("button", name=re.compile("^Solid")).click()
    assert mighty.get_by_role("heading", name=re.compile("^Solid on outputs 5 to 7")).is_visible()
    assert "out5-7 colour=yellow: static" in saved(mighty)


def test_keep_leaves_the_look(mighty):
    before = saved(mighty)
    mighty.get_by_role("button", name="Change look").click()
    mighty.get_by_role("button", name="Keep Rainbow").click()
    assert mighty.get_by_role("heading", name=re.compile("^Rainbow on")).is_visible()
    assert saved(mighty) == before


def test_nothing_opens_the_gallery_straight_away(mighty):
    cut_between(mighty, 4, 5)
    pick(mighty, "Rainbow on outputs 5 to 7")
    mighty.get_by_role("button", name="Change look").click()
    mighty.get_by_role("button", name="Nothing", exact=True).click()
    pick(mighty, "Rainbow on outputs 1 to 4")
    pick(mighty, "Nothing on outputs 5 to 7")
    assert mighty.get_by_role("heading", name=re.compile("^Choose a look for outputs 5 to 7")).is_visible()
    assert "out5-7" not in saved(mighty)


def test_swatch_sets_the_colour(mighty):
    mighty.get_by_role("button", name="Change look").click()
    mighty.get_by_role("button", name=re.compile("^Solid")).click()
    mighty.get_by_role("radio", name="red").click()
    assert mighty.get_by_role("radio", name="red").get_attribute("aria-checked") == "true"
    assert "out1-7 colour=red: static" in saved(mighty)


def test_reverse_is_a_toggle(mighty):
    reverse = mighty.get_by_role("button", name="Reverse")
    assert reverse.get_attribute("aria-pressed") == "false"
    before = saved(mighty)
    reverse.click()
    assert mighty.get_by_role("button", name="Reverse").get_attribute("aria-pressed") == "true"
    assert saved(mighty) != before


def test_brightness_figure_is_typed(mighty):
    mighty.get_by_role("button", name="show values").click()
    box = mighty.get_by_role("group", name="Settings").get_by_role("textbox").first
    box.fill("40")
    box.press("Enter")
    assert "level=40%" in saved(mighty)


def test_blink_takes_another_colour(mighty):
    mighty.get_by_role("button", name="Change look").click()
    mighty.get_by_role("button", name=re.compile("^Blink")).click()
    mighty.get_by_role("button", name="+ another colour").click()
    mighty.get_by_role("radio", name="blue").click()
    assert "rgb_blink" in saved(mighty)


def test_undo_takes_back_a_cut(mighty):
    before = saved(mighty)
    cut_between(mighty, 2, 3)
    mighty.get_by_role("button", name="Undo").click()
    assert saved(mighty) == before


def test_strip_shows_its_leds_in_the_bar(opened):
    page = opened("PIMORONI_PLASMA2350")
    name = page.evaluate("(function () { var strip = runs.filter(function (run) { return run.strip; })[0];"
                         " cutAt(strip, 32); return strip.name; })()")
    bar = page.locator("[data-stretches={}] ol".format(name))
    assert bar.locator("> li").count() == 2
    assert bar.locator("li > button > span i").count() == 66
    assert page.errors == []
