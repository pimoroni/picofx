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

# Bluetooth
require("aioble")

freeze("../frozen_libs/")

# The multi sensor stick's accelerometer and gyroscope, cloned by ci/micropython.sh at its pinned
# version. The stick's other two sensors are C modules in the build
freeze("$(BOARD_DIR)/../../../lsm6ds3-micropython/src", "lsm6ds3.py")

# The QwSTPad gamepad, cloned by ci/micropython.sh at its pinned version
freeze("$(BOARD_DIR)/../../../qwstpad-micropython/src", "qwstpad.py")