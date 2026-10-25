include("manifest.py")

# The FX drive's module, shared by every board carrying one
freeze("../fx_libs/")

# This board's own FX drive pages, manual and defaults
freeze("./fx_libs/")

# autofx is frozen on this board. Its heap is the chip's SRAM alone, and
# compiling it from /lib at import would take most of it
freeze("../visible_libs/", "autofx")

# aye_arr is frozen in too. Its many small files take far more of the filesystem than their size
package("aye_arr", base_path="$(BOARD_DIR)/../../../aye_arr")
