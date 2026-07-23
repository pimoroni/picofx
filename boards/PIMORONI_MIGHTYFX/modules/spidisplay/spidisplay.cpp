// SPDX-License-Identifier: MIT
//
// SPIDisplay transport implementation and its MicroPython bindings. The C++
// class owns the SPI/DMA/GPIO and the overlapped band pump; the extern "C"
// block wraps it as the `SPIDisplay` type. Module registration lives in
// spidisplay_bindings.c.

#include <new>
#include <utility>
#include <algorithm>

#include "hardware/gpio.h"
#include "hardware/regs/addressmap.h"
#include "hardware/spi.h"
#include "pico/time.h"

#include "scanline.hpp"
#include "spidisplay.hpp"

namespace spidisplay {

// Two static SRAM band buffers: one is streamed by DMA while the CPU converts
// the next into the other. Sized to the tunable upper bound MAX_BAND_LINES rows
// at the widest in-scope panel (240px, 480 bytes/row at RGB565); the actual
// band height is SPIDisplay's band_lines, clamped to this. SRAM is required:
// the RP2350 M33 has no SRAM data cache, so DMA sees CPU writes without
// maintenance.
static constexpr int MAX_BAND_LINES = 32;
static constexpr size_t MAX_ROW_BYTES = 240 * 2;
static constexpr size_t BAND_BYTES = MAX_BAND_LINES * MAX_ROW_BYTES;
static uint8_t band_a[BAND_BYTES] __attribute__((aligned(4)));
static uint8_t band_b[BAND_BYTES] __attribute__((aligned(4)));

SPIDisplay::SPIDisplay(uint spi_index, uint sck, uint mosi, uint cs, uint dc,
                       uint baudrate, int te, uint8_t ram_write, int bitdepth,
                       int band_lines)
    : cs_pin(cs), dc_pin(dc), te_pin(te), ram_write_cmd(ram_write),
      fmt(bitdepth == 12 ? RGB444::format : RGB565::format),
      band_lines(band_lines < 1 ? 1 : (band_lines > MAX_BAND_LINES ? MAX_BAND_LINES : band_lines)) {
    spi = spi_index == 0 ? spi0 : spi1;
    spi_init(spi, baudrate);
    spi_set_format(spi, 8, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);
    gpio_set_function(sck, GPIO_FUNC_SPI);
    gpio_set_function(mosi, GPIO_FUNC_SPI);

    gpio_init(cs_pin);
    gpio_set_dir(cs_pin, GPIO_OUT);
    gpio_put(cs_pin, 1);

    gpio_init(dc_pin);
    gpio_set_dir(dc_pin, GPIO_OUT);
    gpio_put(dc_pin, 1);

    if (te_pin >= 0) {
        gpio_init((uint)te_pin);
        gpio_set_dir((uint)te_pin, GPIO_IN);
    }

    dma_chan = dma_claim_unused_channel(true);
    dma_channel_config c = dma_channel_get_default_config(dma_chan);
    channel_config_set_transfer_data_size(&c, DMA_SIZE_8);
    channel_config_set_dreq(&c, spi_get_dreq(spi, true));
    channel_config_set_read_increment(&c, true);
    channel_config_set_write_increment(&c, false);
    dma_channel_configure(dma_chan, &c, &spi_get_hw(spi)->dr, nullptr, 0, false);
}

SPIDisplay::~SPIDisplay() {
    // Runs from the __del__ finaliser, including gc_sweep_all() on soft reset.
    // Abort any transfer and release the channel so re-runs do not exhaust DMA.
    // Guarded so a double call (explicit __del__ then finaliser) is a no-op.
    if (dma_chan >= 0) {
        dma_channel_abort(dma_chan);
        dma_channel_unclaim(dma_chan);
        dma_chan = -1;
    }
}

void SPIDisplay::command(const uint8_t *cmd, size_t cmd_len,
                         const uint8_t *data, size_t data_len) {
    gpio_set_dir(dc_pin, GPIO_OUT);
    gpio_put(dc_pin, 0);
    gpio_put(cs_pin, 0);
    spi_write_blocking(spi, cmd, cmd_len);
    if (data_len) {
        gpio_put(dc_pin, 1);
        spi_write_blocking(spi, data, data_len);
    }
    gpio_put(cs_pin, 1);
}

void SPIDisplay::te_wait() {
    uint pin = te_pin >= 0 ? (uint)te_pin : dc_pin;
    if (te_pin < 0) {
        gpio_set_dir(dc_pin, GPIO_IN);
    }
    while (gpio_get(pin) == 0) {
    }
    while (gpio_get(pin) != 0) {
    }
    if (te_pin < 0) {
        gpio_set_dir(dc_pin, GPIO_OUT);
    }
}

void SPIDisplay::update(const uint8_t *src, int src_w, int src_h,
                        int dst_w, int dst_h,
                        int rotation, int mirror, int pixel_double,
                        uint32_t bg, bool centred_x, int off_x, bool centred_y, int off_y,
                        bool v_sync) {
    bool dbl = pixel_double != 0;

    Transform t = map_transform(rotation, mirror);
    Descriptor d = make_descriptor(src, src_w, src_h, dst_w, dst_h, t, dbl, bg, fmt,
                                   centred_x, off_x, centred_y, off_y);

    // A strided row walk (rotation 90/270: step_x is a whole source row) gets no
    // reuse from the XIP cache's 8-byte line fills, and its fills evict flash
    // code and dirty heap lines. When the source is in the cached PSRAM window,
    // read it through the no-allocate alias: shorter QMI bursts, cache untouched.
    // constexpr uintptr_t PSRAM_WINDOW = 0x01000000;  // 16 MB XIP window per chip select
    // constexpr uintptr_t PSRAM_CACHED_BASE = XIP_BASE + PSRAM_WINDOW;  // CS1
    // if ((uintptr_t)d.src - PSRAM_CACHED_BASE < PSRAM_WINDOW
    //    && d.step_x != RGBA8888::bytes && d.step_x != -RGBA8888::bytes) {
    //    d.src += XIP_NOCACHE_NOALLOC_BASE - XIP_BASE;
    //}

    ConvertFn convert = select_convert(fmt, dbl);

    uint8_t *front = band_a;   // converted, DMA in flight
    uint8_t *back = band_b;    // converted next, while front streams

    int band_rows = band_lines > dst_h ? dst_h : band_lines;

    // Every band is this size except a possibly-shorter final one. The count
    // still has to be reloaded per band: the channel decrements TRANS_COUNT to
    // zero as it runs, and read_addr advances past the buffer.
    const size_t full_band_bytes = (size_t)band_rows * d.dst_row_bytes;

    // 16 columns wide * 240 source rows tall * 4 bytes per pixel = 15,360 bytes.
    // This fits easily into SRAM, handles 16 pixels at a time, and keeps step_x = 16 * 4 = 64 bytes!
    constexpr int CACHE_COLS = MAX_BAND_LINES;
    static uint32_t vertical_sram_cache[BAND_BYTES * 2] __attribute__((aligned(4)));

    // Leverage your existing codebase variables to find the CS1 window
    constexpr uintptr_t PSRAM_WINDOW = 0x01000000;         // 16 MB window per CS
    constexpr uintptr_t PSRAM_CACHED_BASE = XIP_BASE + PSRAM_WINDOW; // Start of PSRAM (0x11000000)

    // Check if the source address sits anywhere inside the 16MB hardware window for CS1
    uintptr_t src_addr = (uintptr_t)d.src;
    bool src_in_psram = (src_addr >= PSRAM_CACHED_BASE && src_addr < PSRAM_CACHED_BASE + PSRAM_WINDOW);

    uint32_t t_conv = time_us_32();

    // Optimized lambda that cleanly intercepts the pipeline
    auto convert_band_optimized = [&](Descriptor &d, uint8_t *dst_band, int row0, int nrows) {
        if (src_in_psram && (rotation == 90 || rotation == 270)) {

            // 1. CALCULATE ACTIVE COLUMN BOUNDS (Source X plane)
            int col_start_edge = d.ub * row0 + d.uc;
            int col_end_edge   = d.ub * (row0 + nrows - 1) + d.uc;

            int col_min = std::min(col_start_edge, col_end_edge);
            int col_max = std::max(col_start_edge, col_end_edge);

            col_min = std::max(0, col_min);
            col_max = std::min(src_w - 1, col_max);
            int actual_cols = (col_max - col_min) + 1;

            if (actual_cols > CACHE_COLS) {
                actual_cols = CACHE_COLS;
            }

            // 2. LINEAR BURST COPY: DRIVE BY SOURCE ROWS, NOT DESTINATION ROWS
            // Under 90 deg, convert_band steps through source rows from v_min to v_max 
            // based on destination columns (d.dx0 to d.dx1). We must populate all of them.
            int v_edge0 = d.va * d.dx0 + d.vc;
            int v_edge1 = d.va * (d.dx1 - 1) + d.vc;
            int v_min   = std::min(v_edge0, v_edge1);
            int v_max   = std::max(v_edge0, v_edge1);

            v_min = std::max(0, v_min);
            v_max = std::min(src_h - 1, v_max);

            // We populate the cache using the literal source row index 'srow'
            for (int srow = v_min; srow <= v_max; ++srow) {
                // The memory destination inside our SRAM cache corresponds directly to the source row index
                uint32_t *sram_row = &vertical_sram_cache[srow * actual_cols];

                // Point to the linear memory block starting at the minimum column
                const uint8_t *psram_block_start = d.src + ((long)srow * d.src_row_bytes) + ((long)col_min * sizeof(uint32_t));

                // Execute high-speed sequential burst copy into SRAM
                std::memcpy(sram_row, psram_block_start, actual_cols * sizeof(uint32_t));
            }

            // 3. APPLY VIRTUAL POINTER CORRECTION
            Descriptor local_d = d;
            local_d.src_row_bytes = actual_cols * sizeof(uint32_t);
            local_d.step_x = (d.step_x > 0 ? 1 : -1) * (int)local_d.src_row_bytes;

            local_d.src = (const uint8_t*)vertical_sram_cache;

            // Shift the coordinate space by col_min
            local_d.uc = d.uc - col_min;
            local_d.vc = d.vc;

            convert(local_d, dst_band, row0, nrows);
        } else {
            convert(d, dst_band, row0, nrows);
        }
    };

    // Convert the first band using our optimized row-interception
    convert_band_optimized(d, front, 0, band_rows);

    last_convert_us = time_us_32() - t_conv;

    gpio_set_dir(dc_pin, GPIO_OUT);
    uint32_t t_te = time_us_32();
    if (v_sync) {
        te_wait();
    }
    last_te_wait_us = time_us_32() - t_te;

    uint32_t t_frame = time_us_32();
    gpio_put(dc_pin, 0);
    gpio_put(cs_pin, 0);
    spi_write_blocking(spi, &ram_write_cmd, 1);
    gpio_put(dc_pin, 1);

    // Dispatch the first band
    dma_channel_set_read_addr(dma_chan, front, false);
    dma_channel_set_trans_count(dma_chan, full_band_bytes, true);  // true starts it

    int row = band_rows;
    while (row < dst_h) {
        int rows = dst_h - row < band_rows ? dst_h - row : band_rows;

        // Convert the subsequent bands using the SRAM row optimization
        convert_band_optimized(d, back, row, rows);

        dma_channel_wait_for_finish_blocking(dma_chan);
        dma_channel_set_read_addr(dma_chan, back, false);
        size_t bytes = rows == band_rows ? full_band_bytes : (size_t)rows * d.dst_row_bytes;
        dma_channel_set_trans_count(dma_chan, bytes, true);
        std::swap(front, back);
        row += rows;
    }
    dma_channel_wait_for_finish_blocking(dma_chan);
    // The DMA finishes when the last bytes reach the SPI TX FIFO, not when they
    // leave the wire. Drain the FIFO before releasing CS or the final few pixels
    // (up to the 8-entry FIFO) are truncated.
    while (spi_is_busy(spi)) {
    }
    gpio_put(cs_pin, 1);
    last_frame_us = time_us_32() - t_frame;
}

}  // namespace spidisplay

extern "C" {

#include "py/runtime.h"

// The C++ object lives inline in the mp_obj rather than a separate m_new block:
// one fewer allocation and a single lifetime to manage.
typedef struct _SPIDisplay_obj_t {
    mp_obj_base_t base;
    spidisplay::SPIDisplay display;
} SPIDisplay_obj_t;

static mp_obj_t SPIDisplay_make_new(const mp_obj_type_t *type, size_t n_args,
                                    size_t n_kw, const mp_obj_t *all_args) {
    enum { ARG_spi, ARG_sck, ARG_mosi, ARG_cs, ARG_dc, ARG_baudrate, ARG_te,
           ARG_ram_write, ARG_bitdepth, ARG_band_lines };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_spi, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_sck, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_mosi, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_cs, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_dc, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_baudrate, MP_ARG_INT, {.u_int = 25000000} },
        { MP_QSTR_te, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_ram_write, MP_ARG_INT, {.u_int = 0x2C} },
        { MP_QSTR_bitdepth, MP_ARG_INT, {.u_int = 16} },
        { MP_QSTR_band_lines, MP_ARG_INT, {.u_int = 16} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args,
                              MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    int te = -1;
    if (args[ARG_te].u_obj != mp_const_none) {
        te = mp_obj_get_int(args[ARG_te].u_obj);
    }

    SPIDisplay_obj_t *self = mp_obj_malloc_with_finaliser(SPIDisplay_obj_t,
                                                          (mp_obj_type_t *)type);
    new (&self->display) spidisplay::SPIDisplay(
        (uint)args[ARG_spi].u_int, (uint)args[ARG_sck].u_int,
        (uint)args[ARG_mosi].u_int, (uint)args[ARG_cs].u_int,
        (uint)args[ARG_dc].u_int, (uint)args[ARG_baudrate].u_int, te,
        (uint8_t)args[ARG_ram_write].u_int, args[ARG_bitdepth].u_int,
        args[ARG_band_lines].u_int);
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t SPIDisplay___del__(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    self->display.~SPIDisplay();  // idempotent: the destructor guards on dma_chan
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay___del___obj, SPIDisplay___del__);

static mp_obj_t SPIDisplay_command(size_t n_args, const mp_obj_t *args) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[0]);

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

static mp_obj_t SPIDisplay_update(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_self, ARG_image, ARG_width, ARG_height,
           ARG_rotation, ARG_mirror, ARG_pixel_double, ARG_bg, ARG_offset, ARG_v_sync };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_image, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_width, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_height, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_rotation, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_mirror, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_pixel_double, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_bg, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_offset, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_v_sync, MP_ARG_BOOL, {.u_bool = false} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args,
                     MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(args[ARG_self].u_obj);

    mp_buffer_info_t buf;
    mp_get_buffer_raise(args[ARG_image].u_obj, &buf, MP_BUFFER_READ);
    int src_w = mp_obj_get_int(mp_load_attr(args[ARG_image].u_obj, MP_QSTR_width));
    int src_h = mp_obj_get_int(mp_load_attr(args[ARG_image].u_obj, MP_QSTR_height));

    // A packed colour carries alpha in the top byte, so it can exceed a signed
    // machine word; truncate to 32 bits (only the low 24 are used).
    uint32_t bg = 0;
    if (args[ARG_bg].u_obj != mp_const_none) {
        bg = (uint32_t)mp_obj_get_int_truncated(args[ARG_bg].u_obj);
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

    self->display.update((const uint8_t *)buf.buf, src_w, src_h,
                          args[ARG_width].u_int, args[ARG_height].u_int,
                          args[ARG_rotation].u_int,
                          args[ARG_mirror].u_int, args[ARG_pixel_double].u_int,
                          bg, centred_x, off_x, centred_y, off_y, args[ARG_v_sync].u_bool);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_KW(SPIDisplay_update_obj, 4, SPIDisplay_update);

// (convert_us, te_wait_us, frame_us) from the most recent update().
static mp_obj_t SPIDisplay_profile(mp_obj_t self_in) {
    SPIDisplay_obj_t *self = (SPIDisplay_obj_t *)MP_OBJ_TO_PTR(self_in);
    mp_obj_t items[3] = {
        mp_obj_new_int_from_uint(self->display.convert_us()),
        mp_obj_new_int_from_uint(self->display.te_wait_us()),
        mp_obj_new_int_from_uint(self->display.frame_us()),
    };
    return mp_obj_new_tuple(3, items);
}
static MP_DEFINE_CONST_FUN_OBJ_1(SPIDisplay_profile_obj, SPIDisplay_profile);

static const mp_rom_map_elem_t SPIDisplay_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&SPIDisplay___del___obj) },
    { MP_ROM_QSTR(MP_QSTR_command), MP_ROM_PTR(&SPIDisplay_command_obj) },
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&SPIDisplay_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_profile), MP_ROM_PTR(&SPIDisplay_profile_obj) },
};
static MP_DEFINE_CONST_DICT(SPIDisplay_locals_dict, SPIDisplay_locals_dict_table);

// External linkage so spidisplay_bindings.c can reference the type (a C++
// namespace-scope const is otherwise internal).
extern const mp_obj_type_t SPIDisplay_type;

MP_DEFINE_CONST_OBJ_TYPE(
    SPIDisplay_type,
    MP_QSTR_SPIDisplay,
    MP_TYPE_FLAG_NONE,
    make_new, (const void *)SPIDisplay_make_new,
    locals_dict, &SPIDisplay_locals_dict
);

}  // extern "C"
