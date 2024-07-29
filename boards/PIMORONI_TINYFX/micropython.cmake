set(PIMORONI_PICO_PATH ../../../../pimoroni-pico)
include(${CMAKE_CURRENT_LIST_DIR}/../pimoroni_pico_import.cmake)

include_directories(${PIMORONI_PICO_PATH}/micropython)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../../")
list(APPEND CMAKE_MODULE_PATH "${PIMORONI_PICO_PATH}/micropython")
list(APPEND CMAKE_MODULE_PATH "${PIMORONI_PICO_PATH}/micropython/modules")

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

include(micropython-common)

# C++ Magic Memory
include(cppmem/micropython)

# Disable build-busting C++ exceptions
# TODO: Defer to micropython-disable-exceptions.cmake when we bump pimoroni pico
# Do not include stack unwinding & exception handling for C++ user modules
target_compile_definitions(usermod INTERFACE PICO_CXX_ENABLE_EXCEPTIONS=0)
target_compile_options(usermod INTERFACE $<$<COMPILE_LANGUAGE:CXX>:
    -fno-exceptions
    -fno-unwind-tables
    -fno-rtti
    -fno-use-cxa-atexit
>)
target_link_options(usermod INTERFACE -specs=nano.specs)
