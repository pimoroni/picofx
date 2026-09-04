set(MOD_NAME spidisplay)
add_library(usermod_${MOD_NAME} INTERFACE)

target_sources(usermod_${MOD_NAME} INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/spidisplay.cpp
    ${CMAKE_CURRENT_LIST_DIR}/spidisplay_bindings.cpp
    ${CMAKE_CURRENT_LIST_DIR}/spidisplay_bindings.c
)

target_include_directories(usermod_${MOD_NAME} INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod_${MOD_NAME} INTERFACE
    hardware_spi
    hardware_dma
)

# Half of each row range converts on core1, through the worker picovector's
# rasteriser owns (pv_core1_run/pv_core1_join). That worker only exists when
# picovector is built with PV_DUAL_CORE, so the board's micropython.cmake must set
# that variable before including this file; without it, conversion stays on one
# core and nothing else changes.
if(PV_DUAL_CORE)
    target_compile_definitions(usermod_${MOD_NAME} INTERFACE SPIDISPLAY_PV_CORE1=1)
endif()

target_link_libraries(usermod INTERFACE usermod_${MOD_NAME})
