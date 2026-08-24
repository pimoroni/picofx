include("$(PORT_DIR)/boards/manifest.py")

require("bundle-networking")

# Bluetooth
require("aioble")

freeze("../frozen_libs/")
freeze("./frozen_libs/")

# The LSM6DS3, the accelerometer and gyroscope on the multi sensor stick, cloned by
# ci/micropython.sh at the version pinned there. The other two sensors on that breakout
# are C modules in the build, and this is the third
freeze("$(BOARD_DIR)/../../../lsm6ds3-micropython/src", "lsm6ds3.py")

# The QwSTPad, a Qw/ST gamepad of ten buttons and four LEDs, cloned by
# ci/micropython.sh at the version pinned there. Four of them fit one bus, which is
# what the infrared remote cannot do, and its buttons read as held rather than as
# presses
freeze("$(BOARD_DIR)/../../../qwstpad-micropython/src", "qwstpad.py")

# TODO: Convince Chris this is the one true and holy path
# package("picofx", base_path="../../")