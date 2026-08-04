// SPDX-License-Identifier: MIT
//
// SRAM column cache for the 90/270 degree scanline path. Header-only so the host
// test harness compiles the same code the firmware runs.
//
// At those rotations a destination row walks down a source column, so successive
// source reads are src_row_bytes apart. Against PSRAM that misses the XIP cache
// on nearly every pixel and dominates conversion time. A block of destination
// rows only samples a narrow band of source columns, so that band is copied into
// SRAM once and a rebased Descriptor is pointed at it: convert_band then runs
// unchanged over a small, contiguous sub-image.
//
// Rebasing is only the two offsets uc/vc plus the source strides. Descriptor
// coordinates stay in destination space, so the covered box still clips against
// absolute destination rows and columns.

#pragma once

#include <algorithm>
#include <cstdint>
#include <cstring>

#include "scanline.hpp"

namespace spidisplay {

class ColumnCache {
public:
    // storage holds capacity_bytes of SRAM scratch. columns is the source
    // columns a window caches, and so the destination rows it serves. A
    // pixel-doubled frame's window spans half that many source columns and
    // simply refreshes more often.
    ColumnCache(uint32_t *storage, int capacity_bytes, int columns)
        : storage(storage), capacity_bytes(capacity_bytes), columns(columns) {}

    // Per frame. The cache serves the rotations whose row walk strides by whole
    // source rows, and only pays for itself when the source is slower than SRAM.
    // Anything else converts straight from the source.
    void begin(const Descriptor &desc, ConvertFn convert, bool pixel_double,
               bool slow_source) {
        d = desc;
        convert_fn = convert;
        pixel_shift = pixel_double ? 1 : 0;
        invalidate();

        window_depth = columns;

        // x_uses_u false means the row walk varies v, the source row: rotation
        // 90 or 270, where u (the source column) varies with dst_y instead.
        active = slow_source && !d.x_uses_u && columns >= 1
                 && d.dx0 < d.dx1 && d.dy0 < d.dy1;
        if (!active) {
            return;
        }

        // v does not vary with dst_y at these rotations, so every destination row
        // samples the same span of source rows and the span is a frame constant.
        int v_lo = d.va * d.dx0 + d.vc;
        int v_hi = d.va * (d.dx1 - 1) + d.vc;
        if (v_lo > v_hi) {
            std::swap(v_lo, v_hi);
        }
        src_row_min = v_lo >> pixel_shift;
        src_rows = (v_hi >> pixel_shift) - src_row_min + 1;

        // The parts of the rebased descriptor that hold for the whole frame; the
        // window supplies the strides and uc in fill().
        cached_d = d;
        cached_d.src = (const uint8_t *)storage;
        cached_d.vc = d.vc - (src_row_min << pixel_shift);
    }

    // Convert nrows destination rows from row0 into dst_band, refreshing the
    // window as the rows advance past it. Windows outlive a single call, so a
    // window seeded near the end of one band is reused by the next.
    void convert(uint8_t *dst_band, int row0, int nrows) {
        if (!active) {
            convert_fn(d, dst_band, row0, nrows);
            return;
        }

        const int end = row0 + nrows;
        int row = row0;
        while (row < end) {
            uint8_t *out = dst_band + (size_t)(row - row0) * d.dst_row_bytes;

            // Rows outside the covered box sample no source at all; the kernel
            // fills them with the background.
            if (row < d.dy0 || row >= d.dy1) {
                int rows = (row < d.dy0 ? std::min(end, d.dy0) : end) - row;
                convert_fn(d, out, row, rows);
                row += rows;
                continue;
            }

            // Windows are clipped to the covered rows, so every column a window
            // spans is one the source has: no clamping to the source extent.
            const int window_rows = std::min(window_depth, d.dy1 - row);
            if (row < window_start || row >= window_end) {
                if (!fill(row, window_rows)) {
                    int rows = std::min(end, row + window_rows) - row;
                    convert_fn(d, out, row, rows);
                    row += rows;
                    continue;
                }
            }

            int rows = std::min(end, window_end) - row;
            convert_fn(cached_d, out, row, rows);
            row += rows;
        }
    }

private:
    void invalidate() {
        window_start = 0;
        window_end = 0;   // An empty window never matches
    }

    // Copy the columns sampled by destination rows [row, row + window_rows) into
    // SRAM. Returns false if the window is not worth caching or does not fit, in
    // which case the caller converts those rows from the source.
    bool fill(int row, int window_rows) {
        invalidate();

        // u is affine in dst_y with |ub| == 1, so the window's first and last
        // rows bound the source columns it samples.
        int u_lo = d.ub * row + d.uc;
        int u_hi = d.ub * (row + window_rows - 1) + d.uc;
        if (u_lo > u_hi) {
            std::swap(u_lo, u_hi);
        }
        const int col_min = u_lo >> pixel_shift;
        const int cols = (u_hi >> pixel_shift) - col_min + 1;

        const size_t row_bytes = (size_t)cols * d.src_bytes;
        if ((size_t)src_rows * row_bytes > (size_t)capacity_bytes) {
            return false;
        }

        const uint8_t *src = d.src + (size_t)src_row_min * d.src_row_bytes
                                   + (size_t)col_min * d.src_bytes;
        uint8_t *dst = (uint8_t *)storage;
        for (int i = 0; i < src_rows; ++i) {
            std::memcpy(dst + (size_t)i * row_bytes, src, row_bytes);
            src += d.src_row_bytes;
        }

        cached_d.src_row_bytes = (int)row_bytes;
        cached_d.step_x = d.step_x > 0 ? (int)row_bytes : -(int)row_bytes;
        cached_d.uc = d.uc - (col_min << pixel_shift);
        window_start = row;
        window_end = row + window_rows;
        return true;
    }

    uint32_t *storage;
    int capacity_bytes;   // storage size in bytes
    int columns;          // Source columns per window

    Descriptor d = {};
    Descriptor cached_d = {};
    ConvertFn convert_fn = nullptr;
    bool active = false;
    int pixel_shift = 0;  // u/v to source pixel: 1 when pixel-doubling
    int window_depth = 0; // Destination rows one window serves
    int src_row_min = 0;  // First source row a destination row samples
    int src_rows = 0;     // Source rows cached, the same for every window
    int window_start = 0;
    int window_end = 0;   // exclusive
};

}  // namespace spidisplay
