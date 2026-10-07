include("$(PORT_DIR)/boards/manifest.py")

freeze("../frozen_libs/")

# The FX drive: the module every board carrying one shares, and this board's own pages,
# manual and defaults
freeze("../fx_libs/")
freeze("./fx_libs/")

# The effects player and the screen library are frozen on this board. Its heap is the
# chip's SRAM alone, and compiling either from /lib at import would take most of it.
# The screen library is the spidisplay repository's own, cloned beside this one.
freeze("../visible_libs/", "autofx.py")
freeze("$(BOARD_DIR)/../../../spidisplay/src")
