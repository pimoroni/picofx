import functools
import http.server
import os
import threading

import pytest

playwright = pytest.importorskip("playwright.sync_api")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BOARDS = ("PIMORONI_MIGHTYFX", "PIMORONI_TINYFX", "PIMORONI_PLASMA2350")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@functools.cache
def server_root():
    handler = functools.partial(QuietHandler, directory=REPO)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return "http://127.0.0.1:{}/".format(server.server_address[1])


def picker_url(board):
    return server_root() + "boards/{}/editor/picker.html".format(board)


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
        page.goto(picker_url(board))
        page.wait_for_function("typeof currentText === 'function'")
        pages.append(page)
        return page

    yield open_board
    for page in pages:
        page.close()
