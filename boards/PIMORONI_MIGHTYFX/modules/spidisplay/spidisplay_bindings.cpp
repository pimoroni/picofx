// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// The MicroPython types wrapping SPIDisplayBus and SPIDisplay, and the two module
// functions taking several displays at once, update_all() and te_phase(). The driver
// they wrap is in spidisplay.cpp and knows nothing of MicroPython. Module
// registration is in spidisplay_bindings.c.

#include "column_cache.hpp"
#include "interleaver.hpp"
#include "scanline.hpp"
#include "spidisplay.hpp"

extern "C" {

#include "py/mphal.h"
#include "py/objtuple.h"
#include "py/runtime.h"

#include "spidisplay_bindings.h"

// The C++ objects live inline in their mp_objs: one allocation and one lifetime
typedef struct _SPIDisplayBus_obj_t {
    mp_obj_base_t base;
    spidisplay::SPIDisplayBus bus;
} SPIDisplayBus_obj_t;

// Three GC roots for pointers the C++ object holds bare. bus_obj roots the bus.
// sram_owner_obj roots the member whose SRAM claim a broadcast group shares, so the
// owner cannot be finalised under the group. staged_image roots a prepare()d frame's
// source, Python running between prepare() and update_all().
typedef struct _SPIDisplay_obj_t {
    mp_obj_base_t base;
    mp_obj_t bus_obj;
    mp_obj_t sram_owner_obj;
    mp_obj_t staged_image;
    spidisplay::SPIDisplay display;
} SPIDisplay_obj_t;

static mp_obj_t SPIDisplayBus_make_new(const mp_obj_type_t *type, size_t n_args,
                                       size_t n_kw, const mp_obj_t *all_args) {
    enum { ARG_spi, ARG_sck, ARG_mosi, ARG_baudrate };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_spi, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_sck, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_mosi, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_baudrate, MP_ARG_INT, {.u_int = 24000000} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args,
                              MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    if (args[ARG_baudrate].u_int < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("baudrate must be positive"));
    }

    uint sck = mp_hal_get_pin_obj(args[ARG_sck].u_obj);
    uint mosi = mp_hal_get_pin_obj(args[ARG_mosi].u_obj);

    SPIDisplayBus_obj_t *self = mp_obj_malloc_with_finaliser(SPIDisplayBus_obj_t, type);
    new (&self->bus) spidisplay::SPIDisplayBus((uint)args[ARG_spi].u_int, sck, mosi,
                                               (uint)args[ARG_baudrate].u_int);
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t SPIDisplayBus___del__(mp_obj_t self_in) {
    SPIDisplayBus_obj_t *self = (SPIDisplayBus_obj_t *)MP_OBJ_TO_PTR(self_in);
    self->bus.~SPIDisplayBus();  // Safe to call twice: the destructor checks dma_chan
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplayBus___del___obj, SPIDisplayBus___del__);

// broadcast(display, display, ...) -> a display whose CS and DC masks carry every
// member's bit, so one frame lands on all of them. Settings come from the first
// member, once, here.
static mp_obj_t SPIDisplayBus_broadcast(size_t n_args, const mp_obj_t *args) {
    // One member is allowed: the group is then a copy of that display, which is the
    // same frame the member's own update writes, so a wall written for a hub still
    // runs where a single panel answered.
    if (n_args < 2) {
        mp_raise_ValueError(MP_ERROR_TEXT("a broadcast group needs at least one display"));
    }

    for (size_t i = 1; i < n_args; ++i) {
        if (!mp_obj_is_type(args[i], &SPIDisplay_type)) {
            mp_raise_TypeError(MP_ERROR_TEXT("broadcast takes SPIDisplay objects"));
        }
        if (((SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[i]))->bus_obj != args[0]) {
            mp_raise_ValueError(MP_ERROR_TEXT("every member must be on this bus"));
        }
    }

    SPIDisplay_obj_t *first = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[1]);
    SPIDisplay_obj_t *group = mp_obj_malloc_with_finaliser(SPIDisplay_obj_t, &SPIDisplay_type);
    group->bus_obj = first->bus_obj;
    group->staged_image = mp_const_none;
    // The copy shares the first member's SRAM claim, so root that member for the
    // group's lifetime. Explicitly deleting the member still dangles the group,
    // the same misuse as deleting the bus under a display.
    group->sram_owner_obj = args[1];
    new (&group->display) spidisplay::SPIDisplay(first->display);

    for (size_t i = 2; i < n_args; ++i) {
        SPIDisplay_obj_t *member = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[i]);
        if (!group->display.compatible_with(member->display)) {
            mp_raise_ValueError(MP_ERROR_TEXT("members must agree on bit depth, dimensions, rate and tuning"));
        }
        group->display.add(member->display);
    }
    return MP_OBJ_FROM_PTR(group);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR(SPIDisplayBus_broadcast_obj, 2, SPIDisplayBus_broadcast);

static const mp_rom_map_elem_t SPIDisplayBus_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&SPIDisplayBus___del___obj) },
    { MP_ROM_QSTR(MP_QSTR_broadcast), MP_ROM_PTR(&SPIDisplayBus_broadcast_obj) },
};
static MP_DEFINE_CONST_DICT(SPIDisplayBus_locals_dict, SPIDisplayBus_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    SPIDisplayBus_type,
    MP_QSTR_SPIDisplayBus,
    MP_TYPE_FLAG_NONE,
    make_new, (const void *)SPIDisplayBus_make_new,
    locals_dict, &SPIDisplayBus_locals_dict
);

static mp_obj_t SPIDisplay_make_new(const mp_obj_type_t *type, size_t n_args,
                                    size_t n_kw, const mp_obj_t *all_args) {
    enum { ARG_bus, ARG_cs, ARG_dc, ARG_width, ARG_height, ARG_te, ARG_ram_write,
           ARG_te_on, ARG_te_off, ARG_te_mode,
           ARG_bitdepth, ARG_baudrate, ARG_band_lines, ARG_cache_columns,
           ARG_stage_lines };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_bus, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_cs, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_dc, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_width, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_height, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_te, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_ram_write, MP_ARG_INT, {.u_int = 0x2C} },
        { MP_QSTR_te_on, MP_ARG_INT, {.u_int = 0x35} },
        { MP_QSTR_te_off, MP_ARG_INT, {.u_int = 0x34} },
        { MP_QSTR_te_mode, MP_ARG_INT, {.u_int = 0x00} },
        { MP_QSTR_bitdepth, MP_ARG_INT, {.u_int = 16} },
        { MP_QSTR_baudrate, MP_ARG_INT, {.u_int = 24000000} },
        { MP_QSTR_band_lines, MP_ARG_INT, {.u_int = 16} },
        { MP_QSTR_cache_columns, MP_ARG_INT, {.u_int = 16} },
        { MP_QSTR_stage_lines, MP_ARG_INT, {.u_int = 0} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args,
                              MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    if (!mp_obj_is_type(args[ARG_bus].u_obj, &SPIDisplayBus_type)) {
        mp_raise_TypeError(MP_ERROR_TEXT("bus must be an SPIDisplayBus"));
    }

    if (args[ARG_height].u_int < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("height must be positive"));
    }
    if (args[ARG_width].u_int < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("width must be positive"));
    }
    if (args[ARG_baudrate].u_int < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("baudrate must be positive"));
    }
    int format = spidisplay::format_for_bitdepth(args[ARG_bitdepth].u_int);
    if (format == 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("bitdepth must be 12 or 16"));
    }
    if (args[ARG_width].u_int % spidisplay::pixels_per_group(format) != 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("a 12-bit row packs two pixels in three bytes, so width must be even"));
    }

    // te=None is the shared DC line; a Pin is a dedicated TE input.
    int te = -1;
    if (args[ARG_te].u_obj != mp_const_none) {
        te = (int)mp_hal_get_pin_obj(args[ARG_te].u_obj);
    }
    uint cs = mp_hal_get_pin_obj(args[ARG_cs].u_obj);
    uint dc = mp_hal_get_pin_obj(args[ARG_dc].u_obj);

    SPIDisplayBus_obj_t *bus = (SPIDisplayBus_obj_t *)MP_OBJ_TO_PTR(args[ARG_bus].u_obj);
    SPIDisplay_obj_t *self = mp_obj_malloc_with_finaliser(SPIDisplay_obj_t, type);
    self->bus_obj = args[ARG_bus].u_obj;
    self->sram_owner_obj = mp_const_none;
    self->staged_image = mp_const_none;
    new (&self->display) spidisplay::SPIDisplay(
        &bus->bus, cs, dc, te, (uint8_t)args[ARG_ram_write].u_int,
        (uint8_t)args[ARG_te_on].u_int, (uint8_t)args[ARG_te_off].u_int,
        (uint8_t)args[ARG_te_mode].u_int,
        args[ARG_bitdepth].u_int, args[ARG_width].u_int, args[ARG_height].u_int,
        (uint32_t)args[ARG_baudrate].u_int, args[ARG_band_lines].u_int,
        args[ARG_cache_columns].u_int, args[ARG_stage_lines].u_int);

    // A failed claim configured no GPIO, so the orphan's finaliser has nothing to
    // undo; raise with both sides of the shortfall.
    if (!self->display.has_sram()) {
        mp_raise_msg_varg(&mp_type_ValueError,
            MP_ERROR_TEXT("display workspace needs %u bytes but only %u are free;"
                          " release old screens and collect them"
                          " or reduce band_lines/cache_columns"),
            (unsigned)self->display.sram_bytes(),
            (unsigned)spidisplay_sram_available());
    }
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t SPIDisplay___del__(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    self->display.~SPIDisplay();  // Safe to call twice: releases the SRAM claim and GPIO
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay___del___obj, SPIDisplay___del__);

static mp_obj_t SPIDisplay_command(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    if (self->display.released()) {
        mp_raise_ValueError(MP_ERROR_TEXT("this screen's bus has been released, so it can no longer stream. Create a new screen, on a bus that has not been released."));
    }
    // A staged or streaming frame owns DC, which a command would force low.
    if (self->display.frame_state() != spidisplay::SPIDisplay::FrameState::IDLE) {
        mp_raise_ValueError(MP_ERROR_TEXT("a frame is staged or streaming; update_all() or abort_frame() first"));
    }

    uint8_t cmd_byte;
    const uint8_t *cmd;
    size_t cmd_len;
    mp_buffer_info_t cbuf;
    if (mp_obj_is_int(args[1])) {
        cmd_byte = (uint8_t)mp_obj_get_int(args[1]);
        cmd = &cmd_byte;
        cmd_len = 1;
    } else {
        mp_get_buffer_raise(args[1], &cbuf, MP_BUFFER_READ);
        cmd = (const uint8_t *)cbuf.buf;
        cmd_len = cbuf.len;
    }

    uint8_t data_byte;
    const uint8_t *data = nullptr;
    size_t data_len = 0;
    mp_buffer_info_t dbuf;
    if (n_args > 2 && args[2] != mp_const_none) {
        if (mp_obj_is_int(args[2])) {
            data_byte = (uint8_t)mp_obj_get_int(args[2]);
            data = &data_byte;
            data_len = 1;
        } else {
            mp_get_buffer_raise(args[2], &dbuf, MP_BUFFER_READ);
            data = (const uint8_t *)dbuf.buf;
            data_len = dbuf.len;
        }
    }

    self->display.command(cmd, cmd_len, data, data_len);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(SPIDisplay_command_obj, 2, 3, SPIDisplay_command);

// update()'s arguments after parsing and validation, shared with prepare().
typedef struct _FrameArgs {
    SPIDisplay_obj_t *self;
    mp_obj_t image;
    mp_buffer_info_t buf;
    int src_w, src_h, src_stride;
    const uint8_t *palette;
    size_t palette_len;
    mp_int_t rotation, mirror, pixel_double;
    bool centred_x, centred_y;
    int off_x, off_y;
    bool tile_x, tile_y;
    bool tile_mirror_x, tile_mirror_y;
    uint32_t bg;
    bool v_sync;
    mp_int_t timeout_us;
    mp_int_t sync_delay_us;
    uint64_t target_cs, target_dc;    // 0 for every line this display drives
    uint64_t sync_cs, sync_dc;        // 0 to leave TE alone
} FrameArgs;

// with_sync parses the trailing v_sync, timeout_us and sync_delay_us; prepare()
// leaves them out, since the TE wait belongs to update_all(), and they raise as
// unknown keywords there.
static void SPIDisplay_parse_frame(size_t n_args, const mp_obj_t *pos_args,
                                   mp_map_t *kw_args, bool with_sync, FrameArgs *out) {
    enum { ARG_self, ARG_image,
           ARG_rotation, ARG_mirror, ARG_pixel_double, ARG_offset, ARG_tile,
           ARG_bg, ARG_to, ARG_sync, ARG_v_sync, ARG_timeout_us, ARG_sync_delay_us };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_image, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_rotation, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_mirror, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_pixel_double, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_offset, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_tile, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_bg, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_to, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_sync, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_v_sync, MP_ARG_BOOL, {.u_bool = false} },
        { MP_QSTR_timeout_us, MP_ARG_INT, {.u_int = 50000} },
        { MP_QSTR_sync_delay_us, MP_ARG_INT, {.u_int = 0} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)] = {};
    size_t n_allowed = MP_ARRAY_SIZE(allowed_args) - (with_sync ? 0 : 3);
    mp_arg_parse_all(n_args, pos_args, kw_args, n_allowed, allowed_args, args);

    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[ARG_self].u_obj);
    if (self->display.released()) {
        mp_raise_ValueError(MP_ERROR_TEXT("this screen's bus has been released, so it can no longer stream. Create a new screen, on a bus that has not been released."));
    }
    if (!self->display.has_sram()) {
        mp_raise_ValueError(MP_ERROR_TEXT("this screen has been deleted and its SRAM released"));
    }

    mp_buffer_info_t buf;
    mp_get_buffer_raise(args[ARG_image].u_obj, &buf, MP_BUFFER_READ);
    int src_w = mp_obj_get_int(mp_load_attr(args[ARG_image].u_obj, MP_QSTR_width));
    int src_h = mp_obj_get_int(mp_load_attr(args[ARG_image].u_obj, MP_QSTR_height));
    int src_stride = mp_obj_get_int(mp_load_attr(args[ARG_image].u_obj, MP_QSTR_stride));

    // An empty or negative extent converts to a background-filled frame, since the
    // covered box comes out empty and no source pixel is read. Report it instead.
    if (src_w < 1 || src_h < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("image width and height must be positive"));
    }
    // A palettised source is one index byte per pixel, drawn through its colour
    // table; the table's bytes are reachable here by reference and are copied
    // per frame into the display's own SRAM before this call returns.
    mp_obj_t palette_obj = mp_load_attr(args[ARG_image].u_obj, MP_QSTR_palette);
    const uint8_t *palette = NULL;
    size_t palette_len = 0;
    if (palette_obj != mp_const_none) {
        mp_buffer_info_t pbuf;
        mp_get_buffer_raise(palette_obj, &pbuf, MP_BUFFER_READ);
        palette = (const uint8_t *)pbuf.buf;
        palette_len = pbuf.len;
    }
    int px_bytes = palette != NULL ? spidisplay::Indexed8::bytes
                                   : spidisplay::RGBA8888::bytes;

    if (src_stride < src_w * px_bytes) {
        mp_raise_ValueError(MP_ERROR_TEXT("image stride is narrower than its width"));
    }

    // The kernel walks src_h rows of the pitch the image reports, so a buffer
    // shorter than that is read out of bounds and an empty one locks the board.
    // The bound is exactly the extent a strided view reports for itself.
    size_t src_bytes = (size_t)(src_h - 1) * (size_t)src_stride
                     + (size_t)src_w * px_bytes;
    if (buf.len < src_bytes) {
        mp_raise_ValueError(MP_ERROR_TEXT("image buffer is shorter than its dimensions"));
    }

    // offset=None centres both axes; an (x, y) pair places the top-left, where
    // either element may be None to centre just that axis.
    bool centred_x = true;
    bool centred_y = true;
    int off_x = 0;
    int off_y = 0;
    if (args[ARG_offset].u_obj != mp_const_none) {
        size_t len;
        mp_obj_t *items;
        mp_obj_get_array(args[ARG_offset].u_obj, &len, &items);
        if (len != 2) {
            mp_raise_ValueError(MP_ERROR_TEXT("offset must be an (x, y) pair"));
        }
        if (items[0] != mp_const_none) {
            centred_x = false;
            off_x = mp_obj_get_int(items[0]);
        }
        if (items[1] != mp_const_none) {
            centred_y = false;
            off_y = mp_obj_get_int(items[1]);
        }
    }

    // tile repeats the source on its own axes, one value for both or an (x, y)
    // pair: the read wraps at the source's size, so any offset is valid. Each
    // value is False, True or Tile.MIRROR, the last reversing every other
    // repeat so each seam is a reflection.
    mp_int_t tile_mode_x = 0;
    mp_int_t tile_mode_y = 0;
    if (args[ARG_tile].u_obj != mp_const_none) {
        if (mp_obj_is_bool(args[ARG_tile].u_obj) || mp_obj_is_int(args[ARG_tile].u_obj)) {
            tile_mode_x = tile_mode_y = mp_obj_get_int(args[ARG_tile].u_obj);
        } else {
            size_t len;
            mp_obj_t *items;
            mp_obj_get_array(args[ARG_tile].u_obj, &len, &items);
            if (len != 2) {
                mp_raise_ValueError(MP_ERROR_TEXT("tile is one value for both axes, or an (x, y) pair"));
            }
            tile_mode_x = mp_obj_get_int(items[0]);
            tile_mode_y = mp_obj_get_int(items[1]);
        }
        if (tile_mode_x < 0 || tile_mode_x > 2 || tile_mode_y < 0 || tile_mode_y > 2) {
            mp_raise_ValueError(MP_ERROR_TEXT("a tile value is False, True or Tile.MIRROR"));
        }
    }

    // A packed colour carries alpha in the top byte, so it can exceed a signed
    // machine word; truncate to 32 bits (only the low 24 are used).
    uint32_t bg = 0;
    if (args[ARG_bg].u_obj != mp_const_none) {
        bg = (uint32_t)mp_obj_get_int_truncated(args[ARG_bg].u_obj);
    }

    out->self = self;
    out->image = args[ARG_image].u_obj;
    out->buf = buf;
    out->src_w = src_w;
    out->src_h = src_h;
    out->src_stride = src_stride;
    out->palette = palette;
    out->palette_len = palette_len;
    out->rotation = args[ARG_rotation].u_int;
    out->mirror = args[ARG_mirror].u_int;
    out->pixel_double = args[ARG_pixel_double].u_int;
    out->bg = bg;
    out->centred_x = centred_x;
    out->centred_y = centred_y;
    out->off_x = off_x;
    out->off_y = off_y;
    out->tile_x = tile_mode_x != 0;
    out->tile_y = tile_mode_y != 0;
    out->tile_mirror_x = tile_mode_x == 2;
    out->tile_mirror_y = tile_mode_y == 2;
    out->v_sync = with_sync ? args[ARG_v_sync].u_bool : false;
    out->timeout_us = with_sync ? args[ARG_timeout_us].u_int : 0;
    out->sync_delay_us = with_sync ? args[ARG_sync_delay_us].u_int : 0;
    if (out->sync_delay_us < 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("sync_delay_us cannot be negative, since the wait cannot release before the tearing edge"));
    }

    // to= narrows the write to some of a group's members, named as displays so the
    // 64-bit masks never cross into Python. Each must be one of this display's own,
    // so a subset cannot write a panel its group does not hold.
    out->target_cs = 0;
    out->target_dc = 0;
    if (args[ARG_to].u_obj != mp_const_none) {
        size_t n_to;
        mp_obj_t *members;
        mp_obj_get_array(args[ARG_to].u_obj, &n_to, &members);
        if (n_to == 0) {
            mp_raise_ValueError(MP_ERROR_TEXT("to= names no displays, so there is nothing to write"));
        }
        for (size_t i = 0; i < n_to; ++i) {
            if (!mp_obj_is_type(members[i], &SPIDisplay_type)) {
                mp_raise_TypeError(MP_ERROR_TEXT("to= takes SPIDisplay objects"));
            }
            spidisplay::SPIDisplay &member = ((SPIDisplay_obj_t *)MP_OBJ_TO_PTR(members[i]))->display;
            if (member.cs_lines() & ~self->display.cs_lines()) {
                mp_raise_ValueError(MP_ERROR_TEXT("to= names a display this one does not drive, so it is not a member of this group"));
            }
            out->target_cs |= member.cs_lines();
            out->target_dc |= member.dc_lines();
        }
    }

    // sync= names the one member whose TE this frame waits on, and with it asks for
    // the transient TEON and TEOFF around the wait. One display and not a tuple: a
    // shared DC line carries one panel's blanking at a time, which is the whole
    // reason the discipline exists.
    out->sync_cs = 0;
    out->sync_dc = 0;
    if (args[ARG_sync].u_obj != mp_const_none) {
        if (!mp_obj_is_type(args[ARG_sync].u_obj, &SPIDisplay_type)) {
            mp_raise_TypeError(MP_ERROR_TEXT("sync= takes one SPIDisplay"));
        }
        spidisplay::SPIDisplay &member =
            ((SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[ARG_sync].u_obj))->display;
        uint64_t lines = member.cs_lines();
        if (lines & ~self->display.cs_lines()) {
            mp_raise_ValueError(MP_ERROR_TEXT("sync= names a display this one does not drive, so it is not a member of this group"));
        }
        if (lines & (lines - 1)) {
            mp_raise_ValueError(MP_ERROR_TEXT("sync= names one panel to wait on, and this one drives several"));
        }
        out->sync_cs = lines;
        out->sync_dc = member.dc_lines();
    }
}

static mp_obj_t SPIDisplay_update(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    FrameArgs a;
    SPIDisplay_parse_frame(n_args, pos_args, kw_args, true, &a);
    a.self->display.update((const uint8_t *)a.buf.buf, a.src_w, a.src_h, a.src_stride,
        a.palette, a.palette_len,
        a.rotation, a.mirror, a.pixel_double,
        a.centred_x, a.off_x, a.centred_y, a.off_y,
        a.tile_x, a.tile_y, a.tile_mirror_x, a.tile_mirror_y, a.bg,
        a.v_sync, a.timeout_us, (uint32_t)a.sync_delay_us,
        a.target_cs, a.target_dc, a.sync_cs, a.sync_dc);
    a.self->staged_image = mp_const_none;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_KW(SPIDisplay_update_obj, 2, SPIDisplay_update);

// fill(colour=black) streams one solid frame, which is update()'s path with no
// source: an empty extent covers no destination pixel, so every one takes the
// background. For putting a panel in a known state at bringup, where no image exists
// yet and the frame is wanted before a canvas is worth claiming.
static mp_obj_t SPIDisplay_fill(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    if (self->display.released()) {
        mp_raise_ValueError(MP_ERROR_TEXT("this screen's bus has been released, so it can no longer stream. Create a new screen, on a bus that has not been released."));
    }
    if (!self->display.has_sram()) {
        mp_raise_ValueError(MP_ERROR_TEXT("this screen has been deleted and its SRAM released"));
    }

    uint32_t bg = 0;
    if (n_args > 1 && args[1] != mp_const_none) {
        bg = (uint32_t)mp_obj_get_int_truncated(args[1]);
    }
    self->display.update(nullptr, 0, 0, 0, nullptr, 0,
                         0, 0, 0,
                         true, 0, true, 0,
                         false, false, false, false, bg,
                         false, 0, 0, 0, 0, 0, 0);
    self->staged_image = mp_const_none;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(SPIDisplay_fill_obj, 1, 2, SPIDisplay_fill);

// prepare(image, ...) stages a frame for update_all(): descriptor, cache and
// the first band's conversion, no bus traffic. The image is rooted on the
// display until the stream completes or abort_frame(), since the staged
// descriptor holds a raw pointer into it.
static mp_obj_t SPIDisplay_prepare(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    FrameArgs a;
    SPIDisplay_parse_frame(n_args, pos_args, kw_args, false, &a);
    a.self->display.prepare((const uint8_t *)a.buf.buf, a.src_w, a.src_h, a.src_stride,
        a.palette, a.palette_len,
        a.rotation, a.mirror, a.pixel_double,
        a.centred_x, a.off_x, a.centred_y, a.off_y,
        a.tile_x, a.tile_y, a.tile_mirror_x, a.tile_mirror_y, a.bg,
        a.target_cs, a.target_dc, a.sync_cs, a.sync_dc);
    a.self->staged_image = a.image;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_KW(SPIDisplay_prepare_obj, 2, SPIDisplay_prepare);

// Abandon a staged or streaming frame and release the image root. The panel
// keeps its GRAM write pointer, so the next full frame recovers the glass.
static mp_obj_t SPIDisplay_abort_frame(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    self->display.abort_frame();
    self->staged_image = mp_const_none;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_abort_frame_obj, SPIDisplay_abort_frame);

// update_all(*displays, v_sync=False, timeout_us=50000, slice_rows=8, hysteresis_rows=-1)
// streams every prepared display's frame concurrently, each starting on its own TE
// edge. The displays must sit on different buses. slice_rows bounds the TE poll
// latency; the default keeps one slice's conversion under the TE pulse width.
// hysteresis_rows is the free ring room a display needs to take the convert burst
// from another, and negative selects half its ring.
mp_obj_t spidisplay_update_all(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_v_sync, ARG_timeout_us, ARG_slice_rows, ARG_hysteresis_rows };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_v_sync, MP_ARG_KW_ONLY | MP_ARG_BOOL, {.u_bool = false} },
        { MP_QSTR_timeout_us, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 50000} },
        { MP_QSTR_slice_rows, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 8} },
        { MP_QSTR_hysteresis_rows, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = -1} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(0, NULL, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    if (n_args < 1 || n_args > 4) {
        mp_raise_ValueError(MP_ERROR_TEXT("update_all takes 1 to 4 displays"));
    }
    if (args[ARG_slice_rows].u_int < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("slice_rows must be positive"));
    }

    SPIDisplay_obj_t *objs[4];
    spidisplay::SPIDisplay *displays[4];
    for (size_t i = 0; i < n_args; ++i) {
        if (!mp_obj_is_type(pos_args[i], &SPIDisplay_type)) {
            mp_raise_TypeError(MP_ERROR_TEXT("update_all takes SPIDisplay objects"));
        }
        SPIDisplay_obj_t *obj = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(pos_args[i]);
        if (obj->display.released()) {
            mp_raise_ValueError(MP_ERROR_TEXT("this screen's bus has been released, so it can no longer stream. Create a new screen, on a bus that has not been released."));
        }
        if (obj->display.frame_state() != spidisplay::SPIDisplay::FrameState::PREPARED) {
            mp_raise_ValueError(MP_ERROR_TEXT("prepare() every display before update_all()"));
        }
        for (size_t j = 0; j < i; ++j) {
            if (obj == objs[j]) {
                mp_raise_ValueError(MP_ERROR_TEXT("a display is listed twice"));
            }
            if (obj->display.shares_bus_with(objs[j]->display)) {
                mp_raise_ValueError(MP_ERROR_TEXT("displays must be on different buses; broadcast() shares one"));
            }
        }
        objs[i] = obj;
        displays[i] = &obj->display;
    }

    // Will the conversion keep every wire fed? Each display prices its own
    // remaining rows at the rate prepare() measured on them, so this follows the
    // real rotation, source memory and cache rather than a table of constants. The
    // longest wire window is the deadline, every row having to be converted by the
    // time the last stream drains.
    uint32_t debt_us = 0;
    uint32_t window_us = 0;
    for (size_t i = 0; i < n_args; ++i) {
        debt_us += displays[i]->convert_debt_us();
        uint32_t window = displays[i]->wire_window_us();
        if (window > window_us) {
            window_us = window;
        }
    }
    if (window_us > 0 && debt_us > window_us) {
        mp_raise_msg_varg(&mp_type_ValueError,
                          MP_ERROR_TEXT("conversion cannot keep the wires fed: %u us still to convert against a %u us frame, so it would tear. Build the screens with a deeper stage_lines, or halve the source and pass pixel_double"),
                          (unsigned)debt_us, (unsigned)window_us);
    }

    // Everything that can raise has; the interleaver runs without the GC or NLR.
    spidisplay::interleave(displays, (int)n_args, args[ARG_v_sync].u_bool,
                           (uint32_t)args[ARG_timeout_us].u_int,
                           (int)args[ARG_slice_rows].u_int,
                           (int)args[ARG_hysteresis_rows].u_int);

    for (size_t i = 0; i < n_args; ++i) {
        objs[i]->staged_image = mp_const_none;
    }
    return mp_const_none;
}
// Declared extern first: a const object compiled as C++ takes internal linkage
// otherwise, and spidisplay_bindings.c links against this name.
extern const mp_obj_fun_builtin_var_t spidisplay_update_all_obj;
MP_DEFINE_CONST_FUN_OBJ_KW(spidisplay_update_all_obj, 1, spidisplay_update_all);

// te_phase(first, second, period_us, edges=2, timeout_ms=500) -> (skew_us, age_us).
// None when either TE line yields too few falls in time. skew_us is first's falling
// edge relative to second's, folded to +-period_us/2. age_us is how old the capture
// already is at return, so a caller can price the drift since. Neither display may
// hold a staged or streaming frame, a staged frame owning the DC lines TE is read from.
mp_obj_t spidisplay_te_phase(size_t n_args, const mp_obj_t *args) {
    if (!mp_obj_is_type(args[0], &SPIDisplay_type) || !mp_obj_is_type(args[1], &SPIDisplay_type)) {
        mp_raise_TypeError(MP_ERROR_TEXT("te_phase takes two SPIDisplay objects"));
    }
    SPIDisplay_obj_t *first = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    SPIDisplay_obj_t *second = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[1]);
    if (first == second) {
        mp_raise_ValueError(MP_ERROR_TEXT("te_phase needs two different displays"));
    }
    // Two panels sharing a DC line resolve to one signal, so a capture from both
    // reads the same edges and folds to a meaningless zero. Sweep them one at a
    // time with te_capture() instead, ageing each fall by that panel's own period.
    if (first->display.te_line() == second->display.te_line()) {
        mp_raise_ValueError(MP_ERROR_TEXT("these displays read TE from one line, so there is no phase between them. Sweep them with te_capture(), one panel at TEON at a time"));
    }
    if (first->display.frame_state() != spidisplay::SPIDisplay::FrameState::IDLE
        || second->display.frame_state() != spidisplay::SPIDisplay::FrameState::IDLE) {
        mp_raise_ValueError(MP_ERROR_TEXT("te_phase cannot run with a frame staged, since a staged frame owns the DC lines"));
    }
    mp_int_t period_us = mp_obj_get_int(args[2]);
    if (period_us < 1000) {
        mp_raise_ValueError(MP_ERROR_TEXT("period_us must be at least 1000"));
    }
    mp_int_t edges = n_args > 3 ? mp_obj_get_int(args[3]) : 2;
    if (edges < 2 || edges > 8) {
        mp_raise_ValueError(MP_ERROR_TEXT("edges must be 2..8"));
    }
    mp_int_t timeout_ms = n_args > 4 ? mp_obj_get_int(args[4]) : 500;
    if (timeout_ms < 1 || timeout_ms > 5000) {
        mp_raise_ValueError(MP_ERROR_TEXT("timeout_ms must be 1..5000"));
    }

    spidisplay::TePhase p = spidisplay::SPIDisplay::te_phase(
        first->display, second->display,
        (uint32_t)period_us, (uint32_t)edges, (uint32_t)timeout_ms);
    if (!p.ok) {
        return mp_const_none;
    }
    mp_obj_t items[2] = {
        mp_obj_new_int(p.skew_us),
        mp_obj_new_int_from_uint(p.age_us),
    };
    return mp_obj_new_tuple(2, items);
}
extern const mp_obj_fun_builtin_var_t spidisplay_te_phase_obj;
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(spidisplay_te_phase_obj, 3, 5, spidisplay_te_phase);

// The panel's own dimensions, fixed when it was built.
static mp_obj_t SPIDisplay_size(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    mp_obj_t items[2] = {
        mp_obj_new_int(self->display.width()),
        mp_obj_new_int(self->display.height()),
    };
    return mp_obj_new_tuple(2, items);
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_size_obj, SPIDisplay_size);

// What this panel's rate reached, which is not the request: the divider rounds
// down. Panels on one port each carry their own.
static mp_obj_t SPIDisplay_baudrate(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.baudrate());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_baudrate_obj, SPIDisplay_baudrate);

// The most recent update() as one snapshot, reachable by name or by index. See
// FrameStats for what each field means. What the frame went out at, and how it was
// banded, are not here, being fixed at construction: read baudrate() and band_rows().
static mp_obj_t SPIDisplay_stats(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    static const qstr fields[] = {
        MP_QSTR_pre_us, MP_QSTR_convert_us, MP_QSTR_te_wait_us, MP_QSTR_frame_us,
        MP_QSTR_convert_total_us, MP_QSTR_stall_us, MP_QSTR_write_start_us,
        MP_QSTR_core1_rows, MP_QSTR_stall_row,
    };
    spidisplay::FrameStats s = self->display.stats();
    mp_obj_t items[MP_ARRAY_SIZE(fields)] = {
        mp_obj_new_int_from_uint(s.pre_us),
        mp_obj_new_int_from_uint(s.convert_us),
        mp_obj_new_int_from_uint(s.te_wait_us),
        mp_obj_new_int_from_uint(s.frame_us),
        mp_obj_new_int_from_uint(s.convert_total_us),
        mp_obj_new_int_from_uint(s.stall_us),
        mp_obj_new_int_from_uint(s.write_start_us),
        mp_obj_new_int_from_uint(s.core1_rows),
        mp_obj_new_int(s.stall_row),
    };
    return mp_obj_new_attrtuple(fields, MP_ARRAY_SIZE(fields), items);
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_stats_obj, SPIDisplay_stats);

// Frames whose TE wait timed out. Zero is the only healthy value on a panel wired
// for v_sync.
static mp_obj_t SPIDisplay_te_timeouts(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.te_timeouts());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_te_timeouts_obj, SPIDisplay_te_timeouts);

// Frames whose wait ended on a pulse it watched rise and that fell too soon to be a
// blanking, which te_timeouts() reads as healthy. A pulse train books as joined
// instead, its next rise landing inside JOINED_HIGH_US, so te_probe() names TE mode 2.
static mp_obj_t SPIDisplay_te_short_waits(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.te_short_waits());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_te_short_waits_obj, SPIDisplay_te_short_waits);

// Frames whose wait began with the line already high, so the pulse it ended on has
// no length to judge. One a frame is a line decaying through the pull-down; the
// occasional one is a frame arming inside a blanking, which is no fault.
static mp_obj_t SPIDisplay_te_joined_waits(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.te_joined_waits());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_te_joined_waits_obj, SPIDisplay_te_joined_waits);

// What a full frame costs on this wire, the measured per-band overhead included, so
// a tearing margin can be priced before any frame has gone out. stats().frame_us is
// the same figure once one has.
static mp_obj_t SPIDisplay_wire_window(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.wire_window_us());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_wire_window_obj, SPIDisplay_wire_window);

// Destination rows per DMA band, after the clamp the request went through, so the
// band count is height over this. Fixed at construction.
static mp_obj_t SPIDisplay_band_rows(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->display.band_rows());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_band_rows_obj, SPIDisplay_band_rows);

// Bytes of SRAM this display claimed for its band and cache workspace, fixed at
// construction: what buffer_size() dropped by when it was built. A broadcast
// group reports its first member's shared claim.
static mp_obj_t SPIDisplay_sram_bytes(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->display.sram_bytes());
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_sram_bytes_obj, SPIDisplay_sram_bytes);

// te_probe(ms=250) -> (period_us, high_us, edges). A short high against the
// period means the asserted level is vertical blanking.
static mp_obj_t SPIDisplay_te_probe(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    mp_int_t ms = n_args > 1 ? mp_obj_get_int(args[1]) : 250;
    if (ms < 1 || ms > 5000) {
        mp_raise_ValueError(MP_ERROR_TEXT("ms must be 1..5000"));
    }
    spidisplay::TeProbe p = self->display.te_probe((uint32_t)ms);
    mp_obj_t items[3] = {
        mp_obj_new_int_from_uint(p.period_us),
        mp_obj_new_int_from_uint(p.high_us),
        mp_obj_new_int_from_uint(p.edges),
    };
    return mp_obj_new_tuple(3, items);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(SPIDisplay_te_probe_obj, 1, 2, SPIDisplay_te_probe);

// te_capture(edges=4, timeout_ms=250) -> (falls, finished_us), the fall timestamps
// and the instant the capture stopped, both on the ticks_us clock. Fewer falls than
// asked for means the timeout ran out. A shared DC line carries one panel's TE at a
// time, so a hub is swept member by member and each fall aged by its own period onto
// one instant. te_probe() discards the timestamps and te_phase() needs two lines.
static mp_obj_t SPIDisplay_te_capture(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);
    if (self->display.frame_state() != spidisplay::SPIDisplay::FrameState::IDLE) {
        mp_raise_ValueError(MP_ERROR_TEXT("te_capture cannot run with a frame staged, since a staged frame owns the DC line"));
    }
    mp_int_t edges = n_args > 1 ? mp_obj_get_int(args[1]) : 4;
    mp_int_t timeout_ms = n_args > 2 ? mp_obj_get_int(args[2]) : 250;
    if (edges < 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("te_capture needs at least one edge"));
    }

    spidisplay::TeCapture c = self->display.te_capture((uint32_t)edges, (uint32_t)timeout_ms);
    mp_obj_t falls = mp_obj_new_tuple(0, nullptr);
    if (c.count > 0) {
        mp_obj_t items[spidisplay::TeCapture::MAX_EDGES];
        for (uint32_t i = 0; i < c.count; ++i) {
            items[i] = mp_obj_new_int_from_uint(c.falls[i]);
        }
        falls = mp_obj_new_tuple(c.count, items);
    }
    mp_obj_t out[2] = {falls, mp_obj_new_int_from_uint(c.finished_us)};
    return mp_obj_new_tuple(2, out);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(SPIDisplay_te_capture_obj, 1, 3, SPIDisplay_te_capture);

static const mp_rom_map_elem_t SPIDisplay_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&SPIDisplay___del___obj) },
    { MP_ROM_QSTR(MP_QSTR_command), MP_ROM_PTR(&SPIDisplay_command_obj) },
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&SPIDisplay_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_fill), MP_ROM_PTR(&SPIDisplay_fill_obj) },
    { MP_ROM_QSTR(MP_QSTR_prepare), MP_ROM_PTR(&SPIDisplay_prepare_obj) },
    { MP_ROM_QSTR(MP_QSTR_abort_frame), MP_ROM_PTR(&SPIDisplay_abort_frame_obj) },
    { MP_ROM_QSTR(MP_QSTR_size), MP_ROM_PTR(&SPIDisplay_size_obj) },
    { MP_ROM_QSTR(MP_QSTR_band_rows), MP_ROM_PTR(&SPIDisplay_band_rows_obj) },
    { MP_ROM_QSTR(MP_QSTR_sram_bytes), MP_ROM_PTR(&SPIDisplay_sram_bytes_obj) },
    { MP_ROM_QSTR(MP_QSTR_baudrate), MP_ROM_PTR(&SPIDisplay_baudrate_obj) },
    { MP_ROM_QSTR(MP_QSTR_stats), MP_ROM_PTR(&SPIDisplay_stats_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_probe), MP_ROM_PTR(&SPIDisplay_te_probe_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_capture), MP_ROM_PTR(&SPIDisplay_te_capture_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_timeouts), MP_ROM_PTR(&SPIDisplay_te_timeouts_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_short_waits), MP_ROM_PTR(&SPIDisplay_te_short_waits_obj) },
    { MP_ROM_QSTR(MP_QSTR_te_joined_waits), MP_ROM_PTR(&SPIDisplay_te_joined_waits_obj) },
    { MP_ROM_QSTR(MP_QSTR_wire_window_us), MP_ROM_PTR(&SPIDisplay_wire_window_obj) },
};
static MP_DEFINE_CONST_DICT(SPIDisplay_locals_dict, SPIDisplay_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    SPIDisplay_type,
    MP_QSTR_SPIDisplay,
    MP_TYPE_FLAG_NONE,
    make_new, (const void *)SPIDisplay_make_new,
    locals_dict, &SPIDisplay_locals_dict
);

}  // extern "C"
