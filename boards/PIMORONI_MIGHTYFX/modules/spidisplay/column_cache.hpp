// SPDX-License-Identifier: MIT
//
// SRAM column cache for the 90/270 degree scanline path.
//
// At those rotations a destination row walks down a source column, so successive
// source reads are src_row_bytes apart. Against PSRAM that misses the XIP cache on
// nearly every pixel and dominates conversion time. A block of destination rows
// samples only a narrow band of source columns, so that band is copied into SRAM
// once and a rebased Descriptor pointed at it, leaving convert_band to run
// unchanged over a small contiguous sub-image.
//
// Rebasing is the two origins plus the source strides. Descriptor coordinates stay
// in destination space, so the covered box still clips against absolute rows.

#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include "scanline.hpp"

namespace spidisplay {

class ColumnCache {
public:
    // columns is the source columns a window caches, and so also the destination
    // rows it serves, one row walking one column here. A pixel-doubled window
    // spans half as many and refreshes twice as often.
    ColumnCache(uint32_t *storage, int capacity_bytes, int columns)
        : storage(storage), capacity_bytes(capacity_bytes), columns(columns) {}

    // Per frame. The cache serves the rotations whose row walk strides by whole
    // source rows, and only pays for itself on a source slower than SRAM. Anything
    // else converts straight from the source.
    void begin(const Descriptor &desc, ConvertFn convert, bool slow_source) {
        frame_desc = desc;
        convert_fn = convert;
        this->slow_source = slow_source;
        pixel_shift = frame_desc.pixel_double ? 1 : 0;
        invalidate();

        window_max_rows = columns;

        // A row walking source rows is rotation 90 or 270, the case this serves.
        active = slow_source && !frame_desc.row_walks_src_columns && columns >= 1
                 && frame_desc.dst_x_start < frame_desc.dst_x_end
                 && frame_desc.dst_y_start < frame_desc.dst_y_end;
        if (!active) {
            return;
        }

        // v does not vary with dst_y here, so the source rows sampled are fixed.
        // A wrapped v keeps the unreduced range: fill() materialises the repeat
        // into the window row by row, so the walk over it needs no wrap of its
        // own.
        int v_lo = frame_desc.dv_dx * frame_desc.dst_x_start + frame_desc.v_at_origin;
        int v_hi = frame_desc.dv_dx * (frame_desc.dst_x_end - 1) + frame_desc.v_at_origin;
        if (v_lo > v_hi) {
            std::swap(v_lo, v_hi);
        }
        src_row_min = v_lo >> pixel_shift;
        src_rows = (v_hi >> pixel_shift) - src_row_min + 1;

        // The frame-wide part of the rebase; fill() supplies the rest per window.
        // fill() materialises a wrapped axis into a contiguous window, mirrored
        // or not, so the cached descriptor drops the flags and convert_band runs
        // the same loops an unwrapped frame does.
        cached_desc = frame_desc;
        cached_desc.src = (const uint8_t *)storage;
        cached_desc.v_at_origin = frame_desc.v_at_origin - (src_row_min << pixel_shift);
        cached_desc.wrap_u = false;
        cached_desc.wrap_mirror_u = false;
        cached_desc.wrap_v = false;
        cached_desc.wrap_mirror_v = false;
    }

    // Convert row_count destination rows from first_row into dst_band, refreshing
    // the window as the rows advance past it. A window outlives one call, so one
    // seeded near the end of a band is reused by the next.
    //
    // Rows go out through emit_rows(), which hands half a range to core1 when that
    // range reads SRAM: a cached window always does, the source itself only when it
    // is not the slow one. The bookkeeping below stays on the calling core.
    void convert(uint8_t *dst_band, int first_row, int row_count) {
        if (!active) {
            emit_rows(convert_fn, frame_desc, dst_band, first_row, row_count,
                      !slow_source);
            return;
        }

        const int end = first_row + row_count;
        int row = first_row;
        while (row < end) {
            uint8_t *out = dst_band
                         + (size_t)(row - first_row) * frame_desc.dst_row_bytes;

            // Background-only rows read no source, so they always split.
            if (row < frame_desc.dst_y_start || row >= frame_desc.dst_y_end) {
                int rows = (row < frame_desc.dst_y_start
                            ? std::min(end, frame_desc.dst_y_start) : end) - row;
                emit_rows(convert_fn, frame_desc, out, row, rows, true);
                row += rows;
                continue;
            }

            // Clipping to covered rows means every column spanned is one the
            // source has, a wrapped u reducing to one inside fill(), so no
            // clamp to the source extent is needed.
            const int window_rows = std::min(window_max_rows, frame_desc.dst_y_end - row);
            if (row < window_start || row >= window_end) {
                if (!fill(row, window_rows)) {
                    int rows = std::min(end, row + window_rows) - row;
                    emit_rows(convert_fn, frame_desc, out, row, rows, !slow_source);
                    row += rows;
                    continue;
                }
            }

            // The window is SRAM, so these rows split whatever the source is.
            int rows = std::min(end, window_end) - row;
            emit_rows(convert_fn, cached_desc, out, row, rows, true);
            row += rows;
        }
    }

private:
    void invalidate() {
        window_start = 0;
        window_end = 0;   // An empty window never matches
    }

    // Copy the columns sampled by destination rows [row, row + window_rows) into
    // SRAM. Returns false if the window will not fit, leaving the caller to convert
    // those rows from the source.
    bool fill(int row, int window_rows) {
        invalidate();

        // u is affine in dst_y with |du_dy| == 1, so the window's first and last
        // rows bound the source columns it samples.
        int u_lo = frame_desc.du_dy * row + frame_desc.u_at_origin;
        int u_hi = frame_desc.du_dy * (row + window_rows - 1) + frame_desc.u_at_origin;
        if (u_lo > u_hi) {
            std::swap(u_lo, u_hi);
        }
        const int src_column_min = u_lo >> pixel_shift;
        const int src_columns = (u_hi >> pixel_shift) - src_column_min + 1;

        const size_t px = (size_t)frame_desc.src_pixel_bytes;
        const size_t row_bytes = (size_t)src_columns * px;
        if ((size_t)src_rows * row_bytes > (size_t)capacity_bytes) {
            return false;
        }

        // The window is filled in nested runs, each sized once and never per
        // row: v runs of consecutive source rows for a wrapped v, u runs of
        // consecutive source columns for a wrapped u inside them, and the v
        // run's rows innermost, so per-row work is one fixed-size copy per u
        // run. A run never crosses a source edge: v_len and run are cut at the
        // next fold, so a mirrored axis alternates direction run by run, a 3-row
        // source over window rows -1 to 4 filling as 0 | 0 1 2 | 2 1. A descending
        // u run reads the source ascending, which is what the XIP cache
        // prefetches, and writes descending in fixed-size pieces, px being 1
        // or 4. An unwrapped axis is simply one run.
        const int src_w_px = frame_desc.src_extent_w >> pixel_shift;
        const int src_h_px = frame_desc.src_extent_h >> pixel_shift;
        uint8_t *dst = (uint8_t *)storage;
        int filled = 0;
        while (filled < src_rows) {
            int v_len = src_rows - filled;
            int v_stride = frame_desc.src_row_bytes;
            const uint8_t *v_src;
            if (!frame_desc.wrap_v) {
                v_src = frame_desc.src
                      + (size_t)(src_row_min + filled) * frame_desc.src_row_bytes;
            } else if (!frame_desc.wrap_mirror_v) {
                const int r = floor_mod(src_row_min + filled, src_h_px);
                v_len = std::min(v_len, src_h_px - r);
                v_src = frame_desc.src + (size_t)r * frame_desc.src_row_bytes;
            } else {
                const int unfolded = floor_mod(src_row_min + filled, 2 * src_h_px);
                const bool v_reversed = unfolded >= src_h_px;
                const int r = v_reversed ? 2 * src_h_px - 1 - unfolded : unfolded;
                v_len = std::min(v_len, v_reversed ? r + 1 : src_h_px - r);
                v_src = frame_desc.src + (size_t)r * frame_desc.src_row_bytes;
                if (v_reversed) {
                    v_stride = -frame_desc.src_row_bytes;
                }
            }

            int placed = 0;
            while (placed < src_columns) {
                int run = src_columns - placed;
                bool u_reversed = false;
                int column;
                if (!frame_desc.wrap_u) {
                    column = src_column_min + placed;
                } else if (!frame_desc.wrap_mirror_u) {
                    column = floor_mod(src_column_min + placed, src_w_px);
                    run = std::min(run, src_w_px - column);
                } else {
                    const int unfolded = floor_mod(src_column_min + placed, 2 * src_w_px);
                    u_reversed = unfolded >= src_w_px;
                    column = u_reversed ? 2 * src_w_px - 1 - unfolded : unfolded;
                    run = std::min(run, u_reversed ? column + 1 : src_w_px - column);
                }
                const uint8_t *u_src = v_src
                    + (size_t)(u_reversed ? column - run + 1 : column) * px;

                for (int k = 0; k < v_len; ++k) {
                    const uint8_t *row_src = u_src + (ptrdiff_t)k * v_stride;
                    uint8_t *out = dst + (size_t)(filled + k) * row_bytes
                                 + (size_t)placed * px;
                    if (!u_reversed) {
                        std::memcpy(out, row_src, (size_t)run * px);
                    } else if (px == 1) {
                        for (int n = 0; n < run; ++n) {
                            out[run - 1 - n] = row_src[n];
                        }
                    } else {
                        for (int n = 0; n < run; ++n) {
                            std::memcpy(out + (size_t)(run - 1 - n) * px,
                                        row_src + (size_t)n * px, 4);
                        }
                    }
                }
                placed += run;
            }
            filled += v_len;
        }

        cached_desc.src_row_bytes = (int)row_bytes;
        cached_desc.src_step_x =
            frame_desc.src_step_x > 0 ? (int)row_bytes : -(int)row_bytes;
        cached_desc.u_at_origin =
            frame_desc.u_at_origin - (src_column_min << pixel_shift);
        window_start = row;
        window_end = row + window_rows;
        return true;
    }

    uint32_t *storage;
    int capacity_bytes;   // storage size in bytes
    int columns;          // Source columns per window

    Descriptor frame_desc = {};
    Descriptor cached_desc = {};
    ConvertFn convert_fn = nullptr;
    bool active = false;
    bool slow_source = false;  // Source reached over XIP, so its rows never split
    int pixel_shift = 0;       // u/v to source pixel: 1 when pixel-doubling
    int window_max_rows = 0;   // Destination rows one window serves
    int src_row_min = 0;       // First source row a destination row samples
    int src_rows = 0;          // Source rows cached, the same for every window
    int window_start = 0;
    int window_end = 0;        // Exclusive
};

}  // namespace spidisplay
