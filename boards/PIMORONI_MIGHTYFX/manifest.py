include("$(PORT_DIR)/boards/manifest.py")

require("bundle-networking")

# Bluetooth
require("aioble")

freeze("../frozen_libs/")

# TODO: Convince Chris this is the one true and holy path
# package("picofx", base_path="../../")