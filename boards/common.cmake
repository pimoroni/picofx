# Make sure we get our VirtualEnv Python
set(Python_FIND_VIRTUALENV "FIRST")
set(Python_FIND_UNVERSIONED_NAMES "FIRST")
set(Python_FIND_STRATEGY "LOCATION")
find_package (Python COMPONENTS Interpreter Development)

message(STATUS "dir2uf2/py_decl: Using Python ${Python_EXECUTABLE}")

set(UF2_STAGING_DIR "${CMAKE_CURRENT_BINARY_DIR}/filesystem")

# Convert supplies paths to absolute, for a quieter life
get_filename_component(PIMORONI_UF2_MANIFEST ${PIMORONI_UF2_MANIFEST} REALPATH)

# Create filesystem directory
file(MAKE_DIRECTORY ${UF2_STAGING_DIR})

function(copy_recursive SOURCE_PATH DESTINATION_PATH REGEX)

    file(GLOB_RECURSE
        FILES
        ${SOURCE_PATH}
        "${SOURCE_PATH}/${REGEX}")

    foreach(file ${FILES})
        file(RELATIVE_PATH RELATIVE_FILE_PATH ${SOURCE_PATH} ${file})
        get_filename_component(FOLDER ${RELATIVE_FILE_PATH} DIRECTORY ${SOURCE_PATH})
        file(MAKE_DIRECTORY ${DESTINATION_PATH}/${FOLDER} )
        message(STATUS "Copy file ${file} -> ${DESTINATION_PATH}/${RELATIVE_FILE_PATH}")
        configure_file(${file} "${DESTINATION_PATH}/${RELATIVE_FILE_PATH}" COPYONLY)
    endforeach()

endfunction()


# Prepare LittleFS filesystem
foreach(dir in ${UF2_COPY_DIRS})
    get_filename_component(dir "${dir}" REALPATH)
    message(STATUS "Copy directory ${dir} -> ${UF2_STAGING_DIR}")
    copy_recursive("${dir}" "${UF2_STAGING_DIR}" "*")
endforeach()

if (EXISTS "${PIMORONI_TOOLS_DIR}/py_decl/py_decl.py")
    add_custom_target("${MICROPY_TARGET}-verify" ALL
        COMMAND ${Python_EXECUTABLE} "${PIMORONI_TOOLS_DIR}/py_decl/py_decl.py" --to-json --verify "${CMAKE_CURRENT_BINARY_DIR}/${MICROPY_TARGET}.uf2"
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        COMMENT "pydecl: Verifying ${MICROPY_TARGET}.uf2"
        DEPENDS ${MICROPY_TARGET}
    )
endif()

if (EXISTS "${PIMORONI_TOOLS_DIR}/dir2uf2/dir2uf2" AND EXISTS "${PIMORONI_UF2_MANIFEST}" AND EXISTS "${UF2_STAGING_DIR}")
    MESSAGE(STATUS "dir2uf2: Using manifest ${PIMORONI_UF2_MANIFEST}.")
    MESSAGE(STATUS "dir2uf2: Using root ${UF2_STAGING_DIR}.")
    if(PICO_PLATFORM STREQUAL "rp2350")
        message(STATUS "dir2uf2: Building sparse UF2 (rp2350 only)")
        set(UF2_SPARSE "--sparse")
    else()
        set(UF2_SPARSE "")
    endif()
    add_custom_target("${MICROPY_TARGET}-with-filesystem.uf2" ALL
        COMMAND ${Python_EXECUTABLE} "${PIMORONI_TOOLS_DIR}/dir2uf2/dir2uf2" --fs-compact ${UF2_SPARSE} --append-to "${MICROPY_TARGET}.uf2" --manifest "${PIMORONI_UF2_MANIFEST}" --filename with-libs-and-examples.uf2 "${UF2_STAGING_DIR}"
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        COMMENT "dir2uf2: Appending filesystem to ${MICROPY_TARGET}.uf2."
        DEPENDS ${MICROPY_TARGET}
        DEPENDS "${MICROPY_TARGET}-verify"
    )
endif()