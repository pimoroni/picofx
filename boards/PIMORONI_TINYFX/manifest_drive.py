include("manifest.py")

# The FX drive: the module every board carrying one shares, and this board's own pages,
# manual and defaults
freeze("../fx_libs/")
freeze("./fx_libs/")

# The effects player is frozen on this board. Its heap is the chip's SRAM alone, and
# compiling it from /lib at import would take most of it
freeze("../visible_libs/", "autofx.py")
