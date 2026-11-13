import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BOARDS = ("PIMORONI_MIGHTYFX", "PIMORONI_TINYFX", "PIMORONI_PLASMA2350")
ENTRY = re.compile(r"^```entry\n(.*?)^```", re.MULTILINE | re.DOTALL)


def entries(board):
    with open(os.path.join(REPO, "boards", board, "manual", "MANUAL.md"), encoding="utf-8") as f:
        return [block for block in ENTRY.findall(f.read()) if block.strip()]


def main():
    for board in BOARDS:
        folder = os.path.join(HERE, "corpus", board)
        os.makedirs(folder, exist_ok=True)
        for at, block in enumerate(entries(board)):
            with open(os.path.join(folder, "manual_{:02d}.txt".format(at)), "w", encoding="utf-8") as f:
                f.write(block)
        print("{}: {} files".format(board, len(entries(board))))


if __name__ == "__main__":
    sys.exit(main())
