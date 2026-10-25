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

# RGBA4444 canvases, half the bytes of RGBA8888, so a full 2.8" picture fits in a heap
# that is the chip's SRAM alone. picovector and the screen driver both read this, so it
# is set before either is found.
set(PV_PIXEL_FORMAT 2)

# PicoVector & MicroPython bindings
# Rasterise/blur on core1 (PV_DUAL_CORE is off by default in picovector-micropython).
set(PV_DUAL_CORE ON)
find_package(PICOVECTOR_MICROPYTHON CONFIG REQUIRED)

# Essential
include(pimoroni_i2c/micropython)

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

# Display transform + DMA transport, from the spidisplay repository. After PV_DUAL_CORE
# above, which it reads to decide whether frame conversion can use picovector's core1
# worker. The GC heap owns this board's SRAM, so the displays' region is a block taken
# from it, at the driver's default size for one panel.
find_package(SPIDISPLAY CONFIG REQUIRED)

# C++ Magic Memory
include(cppmem/micropython)

# Disable build-busting C++ exceptions
include(micropython-disable-exceptions)

# Fail the link where the firmware would run into the FX drive. A linker script given as a
# link input adds to the port's own
target_link_options(usermod INTERFACE
    "-Wl,--defsym=__board_firmware_bytes__=${FIRMWARE_SIZE_BYTES}"
    "${CMAKE_CURRENT_LIST_DIR}/../firmware_size.ld")
