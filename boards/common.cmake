# Make sure we get our VirtualEnv Python
set(Python_FIND_VIRTUALENV "FIRST")
set(Python_FIND_UNVERSIONED_NAMES "FIRST")
set(Python_FIND_STRATEGY "LOCATION")
find_package (Python COMPONENTS Interpreter Development)

message(STATUS "dir2uf2/py_decl: Using Python ${Python_EXECUTABLE}")

set(UF2_STAGING_DIR "${CMAKE_CURRENT_BINARY_DIR}/filesystem")

# Set --sparse for RP2350 builds
if(PICO_PLATFORM STREQUAL "rp2350")
    message(STATUS "dir2uf2: Building sparse UF2 (rp2350 only)")
    set(UF2_SPARSE "--sparse")
else()
    set(UF2_SPARSE "")
endif()

# Convert supplies paths to absolute, for a quieter life
get_filename_component(PIMORONI_UF2_MANIFEST ${PIMORONI_UF2_MANIFEST} REALPATH)

if (EXISTS "${PIMORONI_TOOLS_DIR}/py_decl/py_decl.py")
    add_custom_target("${MICROPY_TARGET}-verify" ALL
        COMMAND ${Python_EXECUTABLE} "${PIMORONI_TOOLS_DIR}/py_decl/py_decl.py" --to-json --verify "${CMAKE_CURRENT_BINARY_DIR}/${MICROPY_TARGET}.uf2"
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        COMMENT "pydecl: Verifying ${MICROPY_TARGET}.uf2"
        DEPENDS ${MICROPY_TARGET}
    )
endif()

# Generate a .bin file containing the data for ROMFS
if (EXISTS "${MICROPY_DIR}/tools/mpremote/mpremote.py" AND EXISTS "${PIMORONI_ROMFS_DIR}")
    get_filename_component(PIMORONI_ROMFS_DIR ${PIMORONI_ROMFS_DIR} REALPATH)
    MESSAGE("mpremote romfs build: Using root ${PIMORONI_ROMFS_DIR}.")
    MESSAGE("mpremote romfs build: Outputting filesystem binary: ${CMAKE_BINARY_DIR}/${MICROPY_TARGET}-romfs.bin")
    add_custom_target("${MICROPY_TARGET}-romfs.bin" ALL
        COMMAND ${Python_EXECUTABLE} "${MICROPY_DIR}/tools/mpremote/mpremote.py" romfs --output "${CMAKE_BINARY_DIR}/${MICROPY_TARGET}-romfs.bin" build "${PIMORONI_ROMFS_DIR}"
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        COMMENT "mpremote romfs build: Packing ROMFS filesystem to ${MICROPY_TARGET}-romfs.bin."
        DEPENDS ${MICROPY_TARGET}
        DEPENDS "${MICROPY_TARGET}-verify"
    )
endif()

# Append the ROMFS .bin file to the UF2 in blockdev "ROMFS"
if (EXISTS "${PIMORONI_TOOLS_DIR}/dir2uf2/dir2uf2" AND EXISTS "${PIMORONI_ROMFS_DIR}")
    MESSAGE("dir2uf2: Using ROMFS binary: ${CMAKE_BINARY_DIR}/${MICROPY_TARGET}-romfs.bin")
    add_custom_target("${MICROPY_TARGET}-romfs.uf2" ALL
        COMMAND ${Python_EXECUTABLE} "${PIMORONI_TOOLS_DIR}/dir2uf2/dir2uf2" --fs-blockdev ROMFS ${UF2_SPARSE} --append-to "${MICROPY_TARGET}.uf2" --filename romfs.uf2 "${CMAKE_BINARY_DIR}/${MICROPY_TARGET}-romfs.bin"
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        COMMENT "dir2uf2: Appending ROMFS to ${MICROPY_TARGET}.uf2."
        DEPENDS ${MICROPY_TARGET}
        DEPENDS "${MICROPY_TARGET}-romfs.bin"
        DEPENDS "${MICROPY_TARGET}.uf2"
        DEPENDS "${MICROPY_TARGET}-verify"
    )
endif()

# Build and append the LittleFS filesystem to the UF2 in blockdev "MicroPython"
if (EXISTS "${PIMORONI_TOOLS_DIR}/dir2uf2/dir2uf2" AND EXISTS "${PIMORONI_UF2_MANIFEST}" AND EXISTS "${UF2_STAGING_SCRIPT}")
    MESSAGE(STATUS "dir2uf2: Using manifest ${PIMORONI_UF2_MANIFEST}.")
    MESSAGE(STATUS "dir2uf2: Using root ${UF2_STAGING_DIR}.")

    # Create filesystem directory
    file(MAKE_DIRECTORY ${UF2_STAGING_DIR})


    # Add a target to prep the staging filesystem
    add_custom_target("${MICROPY_TARGET}-staging" ALL
        COMMAND CI_BUILD_ROOT=${CI_BUILD_ROOT} bash "${UF2_STAGING_SCRIPT}" "${UF2_STAGING_DIR}"
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        COMMENT "dir2uf2: Preparing staging filesystem."
        DEPENDS ${MICROPY_TARGET}
        DEPENDS "${MICROPY_TARGET}-verify")

    if(EXISTS "${PIMORONI_ROMFS_DIR}")
        set(UF2_EXT "-romfs.uf2")
    else()
        set(UF2_EXT ".uf2")
    endif()

    # Add a target to prep the build
    add_custom_target("${MICROPY_TARGET}-with-libs-and-examples.uf2" ALL
        COMMAND ${Python_EXECUTABLE} "${PIMORONI_TOOLS_DIR}/dir2uf2/dir2uf2" --verbose --fs-blockdev MicroPython --fs-compact ${UF2_SPARSE} --append-to "${MICROPY_TARGET}${UF2_EXT}" --manifest "${PIMORONI_UF2_MANIFEST}" --filename with-libs-and-examples.uf2 "${UF2_STAGING_DIR}"
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        COMMENT "dir2uf2: Appending filesystem to ${MICROPY_TARGET}${UF2_EXT}."
        DEPENDS ${MICROPY_TARGET}
        DEPENDS "${MICROPY_TARGET}${UF2_EXT}"
        DEPENDS "${MICROPY_TARGET}-staging"
    )
endif()