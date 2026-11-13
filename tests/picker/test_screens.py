import re

import pytest

MEDIA = """
(function () {
  function art(w, h) {
    var canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    canvas.getContext('2d').fillRect(0, 0, w, h);
    return {url: canvas.toDataURL(), w: w, h: h, ratio: w / h};
  }
  state.fileHandle = {};
  state.scanned = true;
  state.media = [{name: 'cat.gif', kind: 'gif'}, {name: 'sunset.png', kind: 'image'}];
  state.art['cat.gif'] = art(240, 240);
  state.art['sunset.png'] = art(320, 240);
  draw();
})()
"""


def screens_tab(opened, board):
    page = opened(board)
    page.evaluate(MEDIA)
    page.get_by_role("tab", name=re.compile("^Screens")).click()
    return page


def written(page):
    return page.evaluate("currentText()")


def test_picture_goes_to_a_screen(opened):
    page = screens_tab(opened, "PIMORONI_MIGHTYFX")
    show = page.get_by_role("group", name="Show cat.gif").get_by_role("button", name="A")
    show.click()
    assert show.get_attribute("aria-pressed") == "true"
    screen = page.get_by_role("region", name="Screen A")
    assert "showing cat.gif" in screen.locator(":scope > output").inner_text()
    assert re.search(r"^screenA: gif file=cat.gif$", written(page), re.MULTILINE)
    show.click()
    assert show.get_attribute("aria-pressed") == "false"
    assert "screenA:" not in written(page)
    assert page.errors == []


def test_screen_settings(opened):
    page = screens_tab(opened, "PIMORONI_MIGHTYFX")
    page.get_by_role("group", name="Show sunset.png").get_by_role("button", name="B").click()
    screen = page.get_by_role("region", name="Screen B")
    screen.get_by_role("group", name="Rotation").get_by_role("button", name="90\u00b0").click()
    assert "rotation=90" in written(page)
    screen.get_by_role("button", name="Mirror").click()
    assert "mirror=true" in written(page)
    screen.get_by_text("Placement").click()
    screen.get_by_role("group", name="Position").get_by_role("button", name="top left").click()
    assert "offset=0|0" in written(page)
    screen.get_by_text("Background").click()
    screen.get_by_role("radiogroup", name="Background colour").get_by_role("radio", name="red").click()
    assert "bg=red" in written(page)
    screen.get_by_role("radiogroup", name="Background colour").get_by_role("radio", name="custom").click()
    hex = screen.get_by_label("Hex")
    hex.fill("#123456")
    hex.dispatch_event("change")
    assert "bg=123456" in written(page)
    light = screen.locator(".backlight input")
    light.fill("50")
    light.dispatch_event("change")
    assert "backlight=50%" in written(page)
    assert page.errors == []


def test_paired_screens(opened):
    page = screens_tab(opened, "PIMORONI_MIGHTYFX")
    page.get_by_role("group", name="Show cat.gif").get_by_role("button", name="A").click()
    paired = page.get_by_role("region", name="Screen A").get_by_role("button", name="Paired")
    paired.click()
    assert paired.get_attribute("aria-pressed") == "true"
    assert "screenA,B" in written(page)
    other = page.get_by_role("group", name="Show cat.gif").get_by_role("button", name="B")
    assert other.get_attribute("aria-pressed") == "true"
    assert page.errors == []


def test_screen_off_in_a_scene(opened):
    page = screens_tab(opened, "PIMORONI_MIGHTYFX")
    off = page.get_by_role("group", name="Off")
    assert off.count() == 0
    page.evaluate("addScene(); draw()")
    page.get_by_role("group", name="Off").get_by_role("button", name="B").click()
    assert "off in this scene" in page.get_by_role("region", name="Screen B").locator(":scope > output").inner_text()
    assert re.search(r"^screenB: none$", written(page), re.MULTILINE)
    assert page.errors == []


def test_always_on_picture_freezes_a_scene_s_settings(opened):
    page = screens_tab(opened, "PIMORONI_MIGHTYFX")
    page.evaluate("addScene(); state.always.body.screens.A.shows = 'cat.gif'; draw()")
    screen = page.get_by_role("region", name="Screen A")
    assert "from Always on" in screen.locator(":scope > output").inner_text()
    assert screen.get_by_role("group", name="Rotation").get_by_role("button", name="90\u00b0").is_disabled()
    assert page.errors == []


def test_screen_removed_and_added_in_setup(opened):
    page = screens_tab(opened, "PIMORONI_MIGHTYFX")
    assert page.get_by_role("button", name="Remove Screen B").count() == 0
    page.evaluate("setSetup(true); draw()")
    page.get_by_role("button", name="Remove Screen B").click()
    add = page.get_by_role("region", name="Screen B").get_by_role("button", name="add this screen")
    assert add.is_enabled()
    show = page.get_by_role("group", name="Show cat.gif").get_by_role("button", name="B")
    assert show.is_disabled()
    add.click()
    assert page.get_by_role("button", name="Remove Screen B").is_enabled()
    assert page.errors == []


def test_screen_hub_positions_and_groups(opened):
    page = screens_tab(opened, "PIMORONI_MIGHTYFX")
    hub = page.get_by_role("button", name="A Screen Hub across both")
    assert hub.is_disabled()
    page.evaluate("setSetup(true); draw()")
    page.get_by_role("button", name="A Screen Hub across both").click()
    page.evaluate("setSetup(false); draw()")
    assert page.get_by_role("region", name="Screen Hub").is_visible()
    page.get_by_role("group", name="Show cat.gif").get_by_role("button", name="all").click()
    assert "hubA-F" in written(page)
    page.get_by_role("group", name="Position A group").get_by_role("button", name="1").click()
    page.get_by_role("group", name="Position B group").get_by_role("button", name="1").click()
    page.get_by_role("button", name="Position C").click()
    tiles = page.get_by_role("region", name="Screen Hub").get_by_role("listitem")
    assert tiles.nth(2).get_attribute("aria-current") == "true"
    page.get_by_role("region", name="Screen Hub").get_by_role("group", name="Rotation") \
        .get_by_role("button", name="90\u00b0").click()
    assert re.search(r"^hubC rotation=90: gif", written(page), re.MULTILINE)
    page.get_by_role("group", name="Show sunset.png").get_by_role("button", name="1").click()
    assert re.search(r"^hubA-B: image", written(page), re.MULTILINE)
    assert page.errors == []


@pytest.mark.parametrize("board", ["PIMORONI_PLASMA2350"])
def test_one_screen(opened, board):
    page = screens_tab(opened, board)
    show = page.get_by_role("group", name="Show cat.gif").get_by_role("button", name="Show")
    show.click()
    assert show.get_attribute("aria-pressed") == "true"
    assert "showing cat.gif" in page.get_by_role("region", name="Screen").locator(":scope > output").inner_text()
    assert re.search(r"^screen: gif", written(page), re.MULTILINE)
    assert page.errors == []
