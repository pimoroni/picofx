set(MOD_NAME spidisplay)
add_library(usermod_${MOD_NAME} INTERFACE)

target_sources(usermod_${MOD_NAME} INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/spidisplay.cpp
    ${CMAKE_CURRENT_LIST_DIR}/spidisplay_bindings.c
)

target_include_directories(usermod_${MOD_NAME} INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod_${MOD_NAME} INTERFACE
    hardware_spi
    hardware_dma
)

target_link_libraries(usermod INTERFACE usermod_${MOD_NAME})
