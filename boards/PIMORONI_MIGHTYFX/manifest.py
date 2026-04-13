include("$(PORT_DIR)/boards/manifest.py")

freeze("frozen_libs/")

# TODO: Convince Chris this is the one true and holy path
# package("picofx", base_path="../../")