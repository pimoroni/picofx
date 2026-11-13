import os
import shutil
import sys

import pytest
from conftest import BOARDS, REPO
from playwright.sync_api import expect

sys.path.insert(0, os.path.join(REPO, "tools"))
from build_editor import unpacked  # noqa: E402


@pytest.mark.parametrize("board", BOARDS)
def test_the_drive_page_runs(browser, tmp_path, board):
    with open(os.path.join(REPO, "boards", board, "fx_libs", "fx_editor.py"), encoding="utf-8") as f:
        pages, _ = unpacked(f.read())
    (tmp_path / "PICKER.html").write_text(pages["PICKER"], encoding="ascii")
    shutil.copy(os.path.join(REPO, "boards", board, "editor", "catalogue.js"), tmp_path)
    page = browser.new_page(viewport={"width": 1280, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto((tmp_path / "PICKER.html").as_uri())
    expect(page.get_by_role("button", name="Open FX drive")).to_be_visible()
    expect(page.locator("#ledTabs [role=tab]").first).to_be_visible()
    assert errors == []
    page.close()
