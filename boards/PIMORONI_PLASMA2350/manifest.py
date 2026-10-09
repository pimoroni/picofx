import os
import sys

# A manifest runs with this file's directory as the working directory, and $(VAR) is
# substituted only inside the manifest API's own path arguments, so the tool and the list
# are both reached relatively
sys.path.insert(0, os.path.abspath("../../ci"))
from board_packages import read_packages  # noqa: E402

include("$(PORT_DIR)/boards/manifest.py")

# The hosted packages this board names, fetched by ci/micropython.sh. Each carries its own
# manifest, so require() takes its modules and anything it depends on
add_library("pimoroni", "$(LIB_DIR)")
for package in read_packages("board-packages.list"):
    require(package.name, library="pimoroni")

require("bundle-networking")
require("urllib.urequest")
require("umqtt.simple")

# Bluetooth
require("aioble")

# Handy for dealing with APIs
require("datetime")

freeze("../frozen_libs/")

# The QwSTPad, a Qw/ST gamepad of ten buttons and four LEDs, cloned by
# ci/micropython.sh at the version pinned there
freeze("$(BOARD_DIR)/../../../qwstpad-micropython/src", "qwstpad.py")

# The SP/CE connector's pins and the classes for its breakouts, from the pimoroni-pico clone
freeze("$(PORT_DIR)/../../../pimoroni-pico/micropython/modules_py", "spce.py")

# The FX drive: the module every board carrying one shares, and this board's own pages,
# manual and defaults
freeze("../fx_libs/")
freeze("./fx_libs/")

# The effects player and the screen library are frozen on this board. Its heap is the
# chip's SRAM alone, and compiling either from /lib at import would take most of it.
# The screen library is the spidisplay repository's own, cloned beside this one.
freeze("../visible_libs/", "autofx.py")
freeze("$(BOARD_DIR)/../../../spidisplay/src")
