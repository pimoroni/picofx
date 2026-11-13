import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BOARDS = ("PIMORONI_MIGHTYFX", "PIMORONI_TINYFX", "PIMORONI_PLASMA2350")


def picker_path(board):
    return os.path.join(REPO, "boards", board, "editor", "picker.html")


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
