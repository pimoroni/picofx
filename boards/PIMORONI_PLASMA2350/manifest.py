include("$(PORT_DIR)/boards/manifest.py")

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

# A cellular modem on SP/CE, over PPP, from the pimoroni-pico clone
freeze("$(BOARD_DIR)/../../../pimoroni-pico/micropython/modules_py", "lte.py")

# The FX drive: the module every board carrying one shares, and this board's own pages,
# manual and defaults
freeze("../fx_libs/")
freeze("./fx_libs/")

# The effects player and the screen library are frozen on this board. Its heap is the
# chip's SRAM alone, and compiling either from /lib at import would take most of it.
# The screen library is the spidisplay repository's own, cloned beside this one.
freeze("../visible_libs/", "autofx.py")
freeze("$(BOARD_DIR)/../../../spidisplay/src")
