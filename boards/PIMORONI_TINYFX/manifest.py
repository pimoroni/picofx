include("$(PORT_DIR)/boards/manifest.py")

freeze("lib/")

package("picofx", base_path="../../")