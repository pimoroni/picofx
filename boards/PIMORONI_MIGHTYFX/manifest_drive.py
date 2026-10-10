include("manifest.py")

# The FX drive: the module every board carrying one shares, and this board's own pages,
# manual and defaults
freeze("../fx_libs/")
freeze("./fx_libs/")

# The effects player and the screen libraries are frozen in, since the drive leaves the
# filesystem too small to hold them
freeze("../visible_libs/", "autofx.py")
freeze("$(BOARD_DIR)/../../../spidisplay/src", ("logging.py", "st7789.py"))
package("screens", base_path="$(BOARD_DIR)/../../../spidisplay/src")
freeze("$(PORT_DIR)/../../../pimoroni-pico/micropython/modules_py", "spce.py")
