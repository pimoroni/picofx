// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// What the module's three binding files share. spidisplay_bindings.c holds the module
// table, spidisplay_bindings.cpp the two types, and spidisplay.cpp the C-linkage calls
// reaching the driver's own state.

#pragma once

#include "py/runtime.h"

#ifdef __cplusplus
extern "C" {
#endif

/***** The types and their module functions, from spidisplay_bindings.cpp *****/
extern const mp_obj_type_t SPIDisplayBus_type;
extern const mp_obj_type_t SPIDisplay_type;
extern const mp_obj_fun_builtin_var_t spidisplay_update_all_obj;
extern const mp_obj_fun_builtin_var_t spidisplay_te_phase_obj;

/***** The SRAM allocator, over the region the PSRAM-only GC heap leaves free *****/
extern uint8_t __GcHeapStart[];   // A linker symbol, so the region's base
extern size_t spidisplay_sram_available(void);
extern size_t spidisplay_sram_headroom(void);
extern long long spidisplay_sram_claim_low(size_t bytes);
extern void spidisplay_sram_release_low(void);

/***** The dual-core conversion setting *****/
extern int spidisplay_dual_convert(void);
extern void spidisplay_set_dual_convert(int enable);

#ifdef __cplusplus
}
#endif
