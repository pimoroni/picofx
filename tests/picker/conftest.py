import functools
import http.server
import json
import os
import sys
import threading

import pytest

playwright = pytest.importorskip("playwright.sync_api")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BOARDS = ("PIMORONI_MIGHTYFX", "PIMORONI_TINYFX", "PIMORONI_PLASMA2350")

sys.path.insert(0, os.path.join(REPO, "tools"))
import build_editor  # noqa: E402

EXPOSE = """async (urls) => {
  for (const url of urls) {
    const part = await import(url);
    for (const name of Object.keys(part)) {
      if ([window, Window.prototype, EventTarget.prototype].some(holder => Object.hasOwn(holder, name))) continue;
      Object.defineProperty(window, name, {get: () => part[name]});
    }
  }
}"""


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


@functools.cache
def part_urls(board):
    with open(os.path.join(REPO, "boards", board, "editor", "fx_board.json"), encoding="utf-8") as f:
        description = json.load(f)
    shared = os.path.join(REPO, build_editor.SHARED_PARTS)
    parts = build_editor.script_order([os.path.normpath(part) for part in
                                       build_editor.board_parts([shared], description)])
    return [server_root() + os.path.relpath(part, REPO).replace(os.sep, "/") for part in parts]


def open_picker(page, board):
    page.goto(picker_url(board))
    page.evaluate(EXPOSE, part_urls(board))


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
        open_picker(page, board)
        pages.append(page)
        return page

    yield open_board
    for page in pages:
        page.close()
