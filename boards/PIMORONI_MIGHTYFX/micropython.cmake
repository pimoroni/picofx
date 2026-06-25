if(NOT DEFINED PIMORONI_PICO_PATH)
message(FATAL_ERROR "PIMORONI_PICO_PATH must be set!")
endif()
include(${PIMORONI_PICO_PATH}/pimoroni_pico_import.cmake)

include_directories(${PIMORONI_PICO_PATH}/micropython)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../../")
list(APPEND CMAKE_MODULE_PATH "${PIMORONI_PICO_PATH}/micropython")
list(APPEND CMAKE_MODULE_PATH "${PIMORONI_PICO_PATH}/micropython/modules")

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# PicoVector and supporting libs
find_package(PICOVECTOR CONFIG REQUIRED)

# Build picovector with Tufty 2350 settings
target_compile_definitions(usermod_picovector INTERFACE TUFTY=1)

# Essential
include(pimoroni_i2c/micropython)

# QR Code Library
include(qrcode/micropython/micropython)

# Sensors & Breakouts
include(micropython-common-breakouts)

# Utility
include(adcfft/micropython)

# C++ Magic Memory
include(cppmem/micropython)

# Disable build-busting C++ exceptions
include(micropython-disable-exceptions)

# Must call `enable_ulab()` to enable
include(micropython-common-ulab)
enable_ulab()