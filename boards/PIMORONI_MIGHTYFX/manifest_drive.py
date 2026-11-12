include("manifest.py")

# The FX drive: the module every board carrying one shares, and this board's own pages,
# manual and defaults
freeze("../fx_libs/")
freeze("./fx_libs/")

# autofx and the screen libraries are frozen in, since the drive leaves the
# filesystem too small to hold them
freeze("../visible_libs/", "autofx")
freeze("$(BOARD_DIR)/../../../spidisplay/src", ("logging.py", "st7789.py"))
package("screens", base_path="$(BOARD_DIR)/../../../spidisplay/src")
freeze("$(PORT_DIR)/../../../pimoroni-pico/micropython/modules_py", "spce.py")

# aye_arr is frozen in too. Its many small files take far more of the filesystem than their size
package("aye_arr", base_path="$(BOARD_DIR)/../../../aye_arr")
