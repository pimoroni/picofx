# List of directories to copy into the UF2 staging dir
# The contents of these will be available for packing into the filesystem build
list(APPEND UF2_COPY_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/../../examples/tiny_fx"
    "${CMAKE_CURRENT_LIST_DIR}/../../picofx"
    "${CMAKE_CURRENT_LIST_DIR}/visible_libs"
)

set(PIMORONI_UF2_MANIFEST ${CMAKE_CURRENT_LIST_DIR}/uf2-manifest.txt)
include(${CMAKE_CURRENT_LIST_DIR}/../common.cmake)