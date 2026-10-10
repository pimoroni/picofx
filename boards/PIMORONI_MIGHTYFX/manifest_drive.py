include("manifest.py")

# The FX drive: the module every board carrying one shares, and this board's own pages,
# manual and defaults
freeze("../fx_libs/")
freeze("./fx_libs/")

# The effects player and the screen libraries are frozen in, since the drive leaves the
# filesystem too small to hold them
freeze("../visible_libs/", "autofx.py")
freeze("./visible_libs/", ("logging.py", "spce.py", "st7789.py"))
package("screens", base_path="./visible_libs")
