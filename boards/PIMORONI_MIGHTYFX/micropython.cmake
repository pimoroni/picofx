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

# PicoVector & MicroPython bindings
# Rasterise/blur on core1 (PV_DUAL_CORE is off by default in picovector-micropython).
set(PV_DUAL_CORE ON)
find_package(PICOVECTOR_MICROPYTHON CONFIG REQUIRED)

# Build picovector for Tufty 2350
target_compile_definitions(usermod_picovector INTERFACE m_malloc_no_scan=m_malloc)

# A GIF composites to one indexed byte per pixel per frame, and picovector caps that
# at 2MB by default. This board's heap is PSRAM, so a full-screen animation of a few
# dozen frames is affordable: 6MB admits 320x320 over 60 frames and still leaves the
# heap room to present them.
target_compile_definitions(usermod_picovector INTERFACE PV_GIF_MAX_BYTES=6291456)

# Essential
include(pimoroni_i2c/micropython)

# QR Code Library
include(qrcode/micropython/micropython)

# Sensors & Breakouts
include(micropython-common-breakouts)

# LEDs & Matrices
include(plasma/micropython)

# Servos & Motors
include(pwm/micropython)
include(servo/micropython)
include(encoder/micropython)
include(motor/micropython)

# Utility
include(adcfft/micropython)

# Display transform + DMA transport
include(${CMAKE_CURRENT_LIST_DIR}/modules/spidisplay/micropython.cmake)

# C++ Magic Memory
include(cppmem/micropython)

# Disable build-busting C++ exceptions
include(micropython-disable-exceptions)

# Must call `enable_ulab()` to enable
include(micropython-common-ulab)
enable_ulab()