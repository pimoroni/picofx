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
        int v_lo = frame_desc.dv_dx * frame_desc.dst_x_start + frame_desc.v_at_origin;
        int v_hi = frame_desc.dv_dx * (frame_desc.dst_x_end - 1) + frame_desc.v_at_origin;
        if (v_lo > v_hi) {
            std::swap(v_lo, v_hi);
        }
        src_row_min = v_lo >> pixel_shift;
        src_rows = (v_hi >> pixel_shift) - src_row_min + 1;

        // The frame-wide part of the rebase; fill() supplies the rest per window.
        cached_desc = frame_desc;
        cached_desc.src = (const uint8_t *)storage;
        cached_desc.v_at_origin = frame_desc.v_at_origin - (src_row_min << pixel_shift);
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
            // source has, so no clamp to the source extent is needed.
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

        const size_t row_bytes = (size_t)src_columns * frame_desc.src_pixel_bytes;
        if ((size_t)src_rows * row_bytes > (size_t)capacity_bytes) {
            return false;
        }

        const uint8_t *src = frame_desc.src
                           + (size_t)src_row_min * frame_desc.src_row_bytes
                           + (size_t)src_column_min * frame_desc.src_pixel_bytes;
        uint8_t *dst = (uint8_t *)storage;
        for (int i = 0; i < src_rows; ++i) {
            std::memcpy(dst + (size_t)i * row_bytes, src, row_bytes);
            src += frame_desc.src_row_bytes;
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
