// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// An SRAM cache for staging frame columns from PSRAM that become display rows under
// a 90 / 270 degree rotation, so their conversion completes inside a frame period.
//
// At those rotations a destination row walks down a source column, so successive
// source reads can be hundreds of bytes apart. With a PSRAM source that read pattern
// misses the XIP cache on nearly every pixel and dominates the conversion time.
// Without a column cache a rotated frame does not convert inside a frame period at
// the higher refresh rates the panels are run at.
//
// What makes it avoidable is that a run of destination rows sample only a narrow
// strip of source columns. By copying that strip into SRAM first, as a window, and
// rebasing the Descriptor to point at it, convert_band is able to run unchanged over
// a small contiguous sub-image. A window serves as many destination rows as it holds
// source columns, and is refilled once the rows advance past it. Being in SRAM also
// lets its conversion split across both cores, the 1.60x an SRAM source gets.
//
// Rebasing is the u and v origins and the source strides, nothing else. Descriptor
// coordinates stay in destination space, so a window's rows still clip against
// absolute destination rows.

#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include "scanline.hpp"

namespace spidisplay {

class ColumnCache {
public:
    // Give the cache its SRAM storage and its window size, in source columns. One
    // destination row walks one source column, so that is also how many rows a window
    // serves. A pixel-doubled window spans half as many and refills twice as often.
    ColumnCache(uint32_t *storage, int capacity_bytes, int columns)
        : storage(storage), capacity_bytes(capacity_bytes), columns(columns) {}

    // Set the cache up for one frame, deciding whether it will cache at all and
    // precomputing what every window shares. Caching needs a rotation whose row walk
    // strides by whole source rows, and a source slower than SRAM.
    void begin(const Descriptor &desc, ConvertFn convert, bool slow_source) {
        frame_desc = desc;
        convert_fn = convert;
        this->slow_source = slow_source;
        pixel_shift = frame_desc.pixel_double ? 1 : 0;
        invalidate();

        // Check whether this frame is one the cache serves
        active = slow_source && !frame_desc.row_walks_along_src_row && columns >= 1
                 && frame_desc.dst_x_start < frame_desc.dst_x_end
                 && frame_desc.dst_y_start < frame_desc.dst_y_end;
        if (!active) {
            return;    // Nothing is cached for this frame
        }

        // Calculate the source rows this frame samples. v does not vary with dst_y, so
        // one range serves every window, and a wrapped v is left unreduced.
        int v_lo = frame_desc.dv_dx * frame_desc.dst_x_start + frame_desc.v_at_origin;
        int v_hi = frame_desc.dv_dx * (frame_desc.dst_x_end - 1) + frame_desc.v_at_origin;
        if (v_lo > v_hi) {
            std::swap(v_lo, v_hi);
        }
        src_row_min = v_lo >> pixel_shift;
        src_rows = (v_hi >> pixel_shift) - src_row_min + 1;

        // Build the descriptor a window is converted through. Only the parts that hold
        // for the whole frame are set here, fill() setting the rest. The wrap flags are
        // turned off because fill() copies a repeating source out row by row.
        cached_desc = frame_desc;
        cached_desc.src = (const uint8_t *)storage;
        cached_desc.v_at_origin = frame_desc.v_at_origin - (src_row_min << pixel_shift);
        cached_desc.wrap_u = false;
        cached_desc.wrap_mirror_u = false;
        cached_desc.wrap_v = false;
        cached_desc.wrap_mirror_v = false;
    }

    // Convert row_count destination rows from first_row into dst_band, refilling the
    // window whenever the rows pass beyond it. A window outlives the call, so one
    // filled near the end of a band is reused by the next.
    void convert(uint8_t *dst_band, int first_row, int row_count) {
        if (!active) {
            // Not caching this frame, so the whole range converts from the source
            emit_rows(convert_fn, frame_desc, dst_band, first_row, row_count,
                      !slow_source);
            return;    // There is no window this frame
        }

        const int end = first_row + row_count;
        int row = first_row;
        while (row < end) {
            // Take the range in chunks, out being where the current chunk lands
            uint8_t *out = dst_band + (size_t)(row - first_row) * frame_desc.dst_row_bytes;

            if (row < frame_desc.dst_y_start || row >= frame_desc.dst_y_end) {
                // Background-only rows read no source, so they always split
                int rows = (row < frame_desc.dst_y_start
                            ? std::min(end, frame_desc.dst_y_start) : end) - row;
                emit_rows(convert_fn, frame_desc, out, row, rows, true);
                row += rows;
                continue;
            }

            // How many rows the next window serves, stopping at the end of the covered
            // region, so every column it spans is one the source has and needs no clamp
            const int window_rows = std::min(columns, frame_desc.dst_y_end - row);
            if (row < window_start || row >= window_end) {
                // The rows have moved outside the window, so refill it
                if (!fill(row, window_rows)) {
                    // Too large for the storage, so these rows come from the source
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
    // Forget the current window, so the next row converted refills it.
    void invalidate() {
        window_start = 0;
        window_end = 0;   // An empty window never matches
    }

    // Fill the window with the source columns that destination rows [row, row +
    // window_rows) sample. Returns false if they will not fit the storage, leaving
    // the caller to convert those rows from the source.
    bool fill(int row, int window_rows) {
        invalidate();

        // Calculate the source columns these rows sample. u moves one column per row,
        // so the window's first and last rows bound the range.
        int u_lo = frame_desc.du_dy * row + frame_desc.u_at_origin;
        int u_hi = frame_desc.du_dy * (row + window_rows - 1) + frame_desc.u_at_origin;
        if (u_lo > u_hi) {
            std::swap(u_lo, u_hi);
        }
        const int src_column_min = u_lo >> pixel_shift;
        const int src_columns = (u_hi >> pixel_shift) - src_column_min + 1;

        // A window holds src_rows rows of src_columns pixels, which has to fit storage
        const size_t px = (size_t)frame_desc.src_pixel_bytes;
        const size_t row_bytes = (size_t)src_columns * px;
        if ((size_t)src_rows * row_bytes > (size_t)capacity_bytes) {
            return false;
        }

        // The window is filled in nested runs, sized once and never per row. Outer
        // runs are consecutive source rows and inner runs consecutive source columns,
        // so per-row work is one fixed-size copy per inner run. A run cut at a fold
        // never crosses a source edge, and a descending one still reads the source
        // ascending, which is what the XIP cache prefetches.
        const int src_w_px = frame_desc.src_extent_w >> pixel_shift;
        const int src_h_px = frame_desc.src_extent_h >> pixel_shift;
        uint8_t *dst = (uint8_t *)storage;
        int filled = 0;
        while (filled < src_rows) {
            int v_len = src_rows - filled;
            int v_stride = frame_desc.src_row_bytes;
            const uint8_t *v_src;
            if (!frame_desc.wrap_v) {
                // No repeat, so every row wanted is a row the source has
                v_src = frame_desc.src
                      + (size_t)(src_row_min + filled) * frame_desc.src_row_bytes;
            } else if (!frame_desc.wrap_mirror_v) {
                // Repeating, so wrap into the source and stop at its last row
                const int r = floor_mod(src_row_min + filled, src_h_px);
                v_len = std::min(v_len, src_h_px - r);
                v_src = frame_desc.src + (size_t)r * frame_desc.src_row_bytes;
            } else {
                // Mirrored, so unfold to find the row, and read backwards past a fold
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
                    // No repeat, so the whole run is one span of source columns
                    column = src_column_min + placed;
                } else if (!frame_desc.wrap_mirror_u) {
                    // Repeating, so wrap in and cut the run at the source's last column
                    column = floor_mod(src_column_min + placed, src_w_px);
                    run = std::min(run, src_w_px - column);
                } else {
                    // Mirrored, so unfold and cut the run at the fold it meets
                    const int unfolded = floor_mod(src_column_min + placed, 2 * src_w_px);
                    u_reversed = unfolded >= src_w_px;
                    column = u_reversed ? 2 * src_w_px - 1 - unfolded : unfolded;
                    run = std::min(run, u_reversed ? column + 1 : src_w_px - column);
                }
                // Where the run starts in the source, a reversed one at its far end
                const uint8_t *u_src = v_src
                    + (size_t)(u_reversed ? column - run + 1 : column) * px;

                // Write the run into each of the window's rows
                for (int k = 0; k < v_len; ++k) {
                    const uint8_t *row_src = u_src + (ptrdiff_t)k * v_stride;
                    uint8_t *out = dst + (size_t)(filled + k) * row_bytes
                                 + (size_t)placed * px;
                    if (!u_reversed) {
                        // One copy, the run being contiguous in both
                        std::memcpy(out, row_src, (size_t)run * px);
                    } else if (px == 1) {
                        for (int n = 0; n < run; ++n) {
                            out[run - 1 - n] = row_src[n];
                        }
                    } else {
                        // px is only ever 1 or 4, so this is the 4-byte pixel
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

        // Finish the rebase for this window, then record the rows it serves
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
    int capacity_bytes;
    int columns;          // Source columns per window, and so the rows one serves

    Descriptor frame_desc = {};
    Descriptor cached_desc = {};  // The same frame, rebased onto the window
    ConvertFn convert_fn = nullptr;
    bool active = false;
    bool slow_source = false;  // Whether the source is reached over XIP, so its
                               // rows never split
    int pixel_shift = 0;       // Shifts u/v to a source pixel, 1 when pixel-doubling
    int src_row_min = 0;       // Lowest source row the frame samples, unreduced
                               // when v wraps
    int src_rows = 0;          // Source rows cached, the same for every window
    int window_start = 0;
    int window_end = 0;        // One past the last row the window serves
};

}  // namespace spidisplay
