include("$(PORT_DIR)/boards/manifest.py")

freeze("../frozen_libs/")

# The multi sensor stick's accelerometer and gyroscope, cloned by ci/micropython.sh at its pinned
# version. The stick's other two sensors are C modules in the build
freeze("$(BOARD_DIR)/../../../lsm6ds3-micropython/src", "lsm6ds3.py")

# The QwSTPad gamepad, cloned by ci/micropython.sh at its pinned version
freeze("$(BOARD_DIR)/../../../qwstpad-micropython/src", "qwstpad.py")

# TODO: Convince Chris this is the one true and holy path
# package("picofx", base_path="../../")