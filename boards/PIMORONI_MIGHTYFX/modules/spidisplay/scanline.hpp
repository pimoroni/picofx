// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// Templated RGBA8888 -> RGB444 / RGB565 scanline conversion. An indexed source is
// composited over the background colour through its palette.
//
// Placement is calculated once per frame into a Descriptor, reducing to an affine
// map. The inner loop then only walks a source pointer: no per-pixel coordinate
// maths, multiply or bounds branch. Template parameters are the two axes that
// change the loop body, source format and destination packer; rotation, mirror and
// pixel-double sit in the Descriptor.

#pragma once

#include <algorithm>
#include <cstdint>
#include <cstring>

#include "descriptor.hpp"
#include "pixel_formats.hpp"

namespace spidisplay {

// One destination row whose walking axis wraps: the whole row is covered and
// the source repeats along it, a plain seam resetting the pointer to the
// source's start and a seam_reflects one reflecting, the pointer staying on the edge
// pixel and the step reversing so the edge repeats. A seam splits the row into
// runs, and inside one the walk is the plain machinery, so the pixel loops stay
// as tight as the unwrapped path's and only the seam pays.
//
// Kept out of convert_band and never inlined into it: sharing the row body was
// measured to move the unwrapped path's code generation, which byte-identity
// cannot catch, so the wrapped row seeds itself and pays that once per row.
template <class Src, class Dst>
__attribute__((noinline))
void convert_wrapped_row(const Descriptor &desc, uint8_t *out, int dst_y) {
    const int dst_w = desc.dst_w;
    const bool pixel_double = desc.pixel_double;
    const typename Src::Loader loader(desc);

    int u = desc.du_dx * desc.dst_x_start + desc.du_dy * dst_y + desc.u_at_origin;
    int v = desc.dv_dx * desc.dst_x_start + desc.dv_dy * dst_y + desc.v_at_origin;
    int u_unfolded = 0;
    int v_unfolded = 0;
    if (desc.wrap_u) {
        if (desc.wrap_mirror_u) {
            u_unfolded = floor_mod(u, 2 * desc.src_extent_w);
            u = fold(u_unfolded, desc.src_extent_w);
        } else {
            u = floor_mod(u, desc.src_extent_w);
            u_unfolded = u;
        }
    }
    if (desc.wrap_v) {
        if (desc.wrap_mirror_v) {
            v_unfolded = floor_mod(v, 2 * desc.src_extent_h);
            v = fold(v_unfolded, desc.src_extent_h);
        } else {
            v = floor_mod(v, desc.src_extent_h);
            v_unfolded = v;
        }
    }
    const int src_col = pixel_double ? (u >> 1) : u;
    const int src_row = pixel_double ? (v >> 1) : v;
    const uint8_t *src_ptr = desc.src + (long)src_row * desc.src_row_bytes
                      + (long)src_col * Src::bytes;
    int row_walk_parity = 0;
    if (pixel_double) {
        row_walk_parity = (desc.row_walks_src_columns ? u : v) & 1;
    }

    const int extent = desc.row_walks_src_columns ? desc.src_extent_w
                                                  : desc.src_extent_h;
    const bool seam_reflects = desc.row_walks_src_columns ? desc.wrap_mirror_u
                                                     : desc.wrap_mirror_v;
    const int unfolded = desc.row_walks_src_columns ? u_unfolded : v_unfolded;
    const bool starts_reflected = seam_reflects && unfolded >= extent;
    int step = starts_reflected ? -desc.src_step_x : desc.src_step_x;
    int advance_at_parity = desc.row_walks_forward ? 1 : 0;
    if (starts_reflected) {
        advance_at_parity ^= 1;
    }
    int until_seam;
    if (desc.row_walks_forward) {
        until_seam = (starts_reflected ? 2 * extent : extent) - unfolded;
    } else {
        until_seam = unfolded - (starts_reflected ? extent : 0) + 1;
    }
    const uint8_t *seam_ptr = nullptr;
    if (!seam_reflects) {
        const int seam_index = desc.row_walks_forward
            ? 0 : (pixel_double ? (extent - 1) >> 1 : extent - 1);
        seam_ptr = desc.row_walks_src_columns
            ? desc.src + (long)src_row * desc.src_row_bytes
                + (long)seam_index * Src::bytes
            : desc.src + (long)seam_index * desc.src_row_bytes
                + (long)src_col * Src::bytes;
    }

    // advanced_last is whether the pixel just packed moved src_ptr, which a
    // reflecting seam undoes so the edge pixel repeats. A plain walk always did;
    // pixel_double moves only on the half advance_at_parity names, and the parity
    // has toggled once since that pixel, so the caller reads it back one step.
    auto seam = [&](bool advanced_last) {
        if (seam_reflects) {
            if (advanced_last) {
                src_ptr -= step;
            }
            step = -step;
            if (pixel_double) {
                advance_at_parity ^= 1;
                row_walk_parity ^= 1;
            }
        } else {
            src_ptr = seam_ptr;
        }
        until_seam = extent;
    };

    if constexpr (!Dst::pairs) {
        uint8_t r, g, b;
        int x = 0;
        while (x < dst_w) {
            int n = std::min(until_seam, dst_w - x);
            x += n;
            until_seam -= n;
            if (pixel_double) {
                for (int i = 0; i < n; ++i) {
                    loader.load(src_ptr, r, g, b);
                    Dst::pack1(out, r, g, b);
                    out += 2;
                    if (row_walk_parity == advance_at_parity) {
                        src_ptr += step;
                    }
                    row_walk_parity ^= 1;
                }
                if (until_seam == 0) {
                    seam((row_walk_parity ^ 1) == advance_at_parity);
                }
            } else {
                for (int i = 0; i < n; ++i) {
                    loader.load(src_ptr, r, g, b);
                    src_ptr += step;
                    Dst::pack1(out, r, g, b);
                    out += 2;
                }
                if (until_seam == 0) {
                    seam(true);
                }
            }
        }
    } else {
        // A seam can fall mid-pair, so a run's odd tail is held and the next
        // run's first pixel completes it; dst_w is even, so a row never ends
        // holding. One held pixel is a group of two, so this assumes no packer
        // groups more.
        uint8_t r0, g0, b0, r1, g1, b1;
        bool holding = false;
        int x = 0;
        while (x < dst_w) {
            int n = std::min(until_seam, dst_w - x);
            x += n;
            until_seam -= n;
            if (pixel_double) {
                for (int i = 0; i < n; ++i) {
                    loader.load(src_ptr, r1, g1, b1);
                    if (row_walk_parity == advance_at_parity) {
                        src_ptr += step;
                    }
                    row_walk_parity ^= 1;
                    if (!holding) {
                        r0 = r1; g0 = g1; b0 = b1;
                        holding = true;
                    } else {
                        Dst::pack2(out, r0, g0, b0, r1, g1, b1);
                        out += 3;
                        holding = false;
                    }
                }
                if (until_seam == 0) {
                    seam((row_walk_parity ^ 1) == advance_at_parity);
                }
            } else {
                if (holding && n > 0) {
                    loader.load(src_ptr, r1, g1, b1);
                    src_ptr += step;
                    Dst::pack2(out, r0, g0, b0, r1, g1, b1);
                    out += 3;
                    holding = false;
                    --n;
                }
                for (; n >= 2; n -= 2) {
                    loader.load(src_ptr, r0, g0, b0);
                    src_ptr += step;
                    loader.load(src_ptr, r1, g1, b1);
                    src_ptr += step;
                    Dst::pack2(out, r0, g0, b0, r1, g1, b1);
                    out += 3;
                }
                if (n == 1) {
                    loader.load(src_ptr, r0, g0, b0);
                    src_ptr += step;
                    holding = true;
                }
                if (until_seam == 0) {
                    seam(true);
                }
            }
        }
    }
}

// Convert row_count destination rows from first_row into dst_band, one packed row
// per dst_row_bytes. Rows outside the covered box, and the uncovered ends of
// covered rows, are filled with the background.
//
// Each covered row goes out as background, covered span, background, keeping the
// bounds test out of the covered loop. Fields read inside the pixel loops are
// copied to locals first: the output pointer may alias the descriptor, so field
// reads would otherwise repeat after every store.
template <class Src, class Dst>
void convert_band(const Descriptor &desc, uint8_t *dst_band, int first_row,
                  int row_count) {
    const int dst_w = desc.dst_w;
    const int dst_x_start = desc.dst_x_start, dst_x_end = desc.dst_x_end;
    const int src_step_x = desc.src_step_x;
    const bool pixel_double = desc.pixel_double;
    const int advance_at_parity = desc.row_walks_forward ? 1 : 0;
    const uint8_t bg_r = desc.bg_r, bg_g = desc.bg_g, bg_b = desc.bg_b;
    const typename Src::Loader loader(desc);

    // Packed background, one group: a pixel pair for RGB444, one pixel for RGB565
    uint8_t bg_packed[Dst::group_bytes] = {};
    if constexpr (Dst::pairs) {
        Dst::pack2(bg_packed, bg_r, bg_g, bg_b, bg_r, bg_g, bg_b);
    } else {
        Dst::pack1(bg_packed, bg_r, bg_g, bg_b);
    }

    // Fill that many background pixels and return the advanced output pointer.
    // A pair format needs an even count, which every call site holds to.
    auto fill_bg = [&](uint8_t *dst_ptr, int pixels) {
        if constexpr (Dst::pairs) {
            if (pixels >= 8) {
                return fill_bg_pairs(dst_ptr, pixels, bg_packed);
            }
            for (int i = 0; i < pixels; i += 2) {
                dst_ptr[0] = bg_packed[0];
                dst_ptr[1] = bg_packed[1];
                dst_ptr[2] = bg_packed[2];
                dst_ptr += 3;
            }
        } else {
            const uint32_t bg_pair_pattern =
                  (uint32_t)bg_packed[0] | ((uint32_t)bg_packed[1] << 8)
                | ((uint32_t)bg_packed[0] << 16) | ((uint32_t)bg_packed[1] << 24);
            int i = 0;
            for (; i + 1 < pixels; i += 2) {
                memcpy(dst_ptr, &bg_pair_pattern, 4);
                dst_ptr += 4;
            }
            if (i < pixels) {
                dst_ptr[0] = bg_packed[0];
                dst_ptr[1] = bg_packed[1];
                dst_ptr += 2;
            }
        }
        return dst_ptr;
    };

    for (int row = 0; row < row_count; ++row) {
        const int dst_y = first_row + row;
        uint8_t *out = dst_band + row * desc.dst_row_bytes;

        if (dst_y < desc.dst_y_start || dst_y >= desc.dst_y_end
                || dst_x_start >= dst_x_end) {
            fill_bg(out, dst_w);
            continue;
        }

        // A row whose walking axis wraps seeds itself in convert_wrapped_row,
        // kept out of this body so the unwrapped rows' code generation never
        // moves with it.
        if (desc.row_walks_src_columns ? desc.wrap_u : desc.wrap_v) {
            convert_wrapped_row<Src, Dst>(desc, out, dst_y);
            continue;
        }

        // Seed the row walk at the first covered column. The pointer is only read
        // inside the covered span, so stepping from here tracks the map exactly.
        // A wrapped row-selecting coordinate reduces here, folding when seam_reflects.
        int u_at_row_start =
            desc.du_dx * dst_x_start + desc.du_dy * dst_y + desc.u_at_origin;
        int v_at_row_start =
            desc.dv_dx * dst_x_start + desc.dv_dy * dst_y + desc.v_at_origin;
        if (desc.wrap_u) {
            u_at_row_start = desc.wrap_mirror_u
                ? fold(floor_mod(u_at_row_start, 2 * desc.src_extent_w),
                       desc.src_extent_w)
                : floor_mod(u_at_row_start, desc.src_extent_w);
        }
        if (desc.wrap_v) {
            v_at_row_start = desc.wrap_mirror_v
                ? fold(floor_mod(v_at_row_start, 2 * desc.src_extent_h),
                       desc.src_extent_h)
                : floor_mod(v_at_row_start, desc.src_extent_h);
        }
        const int src_col = pixel_double ? (u_at_row_start >> 1) : u_at_row_start;
        const int src_row = pixel_double ? (v_at_row_start >> 1) : v_at_row_start;
        const uint8_t *src_ptr = desc.src + (long)src_row * desc.src_row_bytes
                          + (long)src_col * Src::bytes;
        int row_walk_parity = 0;
        if (pixel_double) {
            row_walk_parity =
                (desc.row_walks_src_columns ? u_at_row_start : v_at_row_start) & 1;
        }

        if constexpr (!Dst::pairs) {
            out = fill_bg(out, dst_x_start);
            uint8_t r, g, b;
            if (pixel_double) {
                // The source advances once per two destination pixels. A leading
                // pixel where that lands first aligns the walk, so each remaining
                // source pixel is emitted twice.
                int x = dst_x_start;
                if (row_walk_parity == advance_at_parity) {
                    loader.load(src_ptr, r, g, b);
                    src_ptr += src_step_x;
                    Dst::pack1(out, r, g, b);
                    out += 2;
                    ++x;
                }
                for (; x + 1 < dst_x_end; x += 2) {
                    loader.load(src_ptr, r, g, b);
                    src_ptr += src_step_x;
                    Dst::pack1(out, r, g, b);
                    Dst::pack1(out + 2, r, g, b);
                    out += 4;
                }
                if (x < dst_x_end) {
                    loader.load(src_ptr, r, g, b);
                    Dst::pack1(out, r, g, b);
                    out += 2;
                }
            } else {
                for (int x = dst_x_start; x < dst_x_end; ++x) {
                    loader.load(src_ptr, r, g, b);
                    src_ptr += src_step_x;
                    Dst::pack1(out, r, g, b);
                    out += 2;
                }
            }
            fill_bg(out, dst_w - dst_x_end);
        } else {
            // Pair-aligned bounds of the covered span. An odd boundary makes the
            // pair at that end mixed; pairs between are fully covered.
            const int pair_start = dst_x_start & ~1;
            const int pair_end = (dst_x_end + 1) & ~1;
            out = fill_bg(out, pair_start);

            // Emit one mixed pair with a per-pixel bounds test. row_walk_parity
            // carries which half of a doubled source pixel this is, across the
            // whole span, so clipping and mirroring stay aligned.
            auto fetch = [&](int x, uint8_t &r, uint8_t &g, uint8_t &b) {
                if ((unsigned)(x - dst_x_start) < (unsigned)(dst_x_end - dst_x_start)) {
                    loader.load(src_ptr, r, g, b);
                    if (pixel_double) {
                        if (row_walk_parity == advance_at_parity) {
                            src_ptr += src_step_x;
                        }
                        row_walk_parity ^= 1;
                    } else {
                        src_ptr += src_step_x;
                    }
                } else {
                    r = bg_r;
                    g = bg_g;
                    b = bg_b;
                }
            };
            auto mixed_pair = [&](int x) {
                uint8_t r0, g0, b0, r1, g1, b1;
                fetch(x, r0, g0, b0);
                fetch(x + 1, r1, g1, b1);
                Dst::pack2(out, r0, g0, b0, r1, g1, b1);
                out += 3;
            };

            int pair_x = pair_start;
            if (dst_x_start & 1) {
                mixed_pair(pair_x);
                pair_x += 2;
            }
            const int whole_pairs_end = (dst_x_end & 1) ? pair_end - 2 : pair_end;
            if (pixel_double) {
                // One source advance per pair. Whole pairs leave row_walk_parity
                // unchanged, so the parity holds across the loop.
                uint8_t r, g, b;
                if (row_walk_parity == advance_at_parity) {
                    // The advance lands after the first pixel: a pair spans two
                    // adjacent source pixels, and doubling straddles pairs.
                    for (; pair_x < whole_pairs_end; pair_x += 2) {
                        uint8_t r1, g1, b1;
                        loader.load(src_ptr, r, g, b);
                        src_ptr += src_step_x;
                        loader.load(src_ptr, r1, g1, b1);
                        Dst::pack2(out, r, g, b, r1, g1, b1);
                        out += 3;
                    }
                } else {
                    // Pair-aligned doubling: both pixels repeat one source pixel.
                    for (; pair_x < whole_pairs_end; pair_x += 2) {
                        loader.load(src_ptr, r, g, b);
                        src_ptr += src_step_x;
                        Dst::pack2(out, r, g, b, r, g, b);
                        out += 3;
                    }
                }
            } else {
                for (; pair_x < whole_pairs_end; pair_x += 2) {
                    uint8_t r0, g0, b0, r1, g1, b1;
                    loader.load(src_ptr, r0, g0, b0);
                    src_ptr += src_step_x;
                    loader.load(src_ptr, r1, g1, b1);
                    src_ptr += src_step_x;
                    Dst::pack2(out, r0, g0, b0, r1, g1, b1);
                    out += 3;
                }
            }
            if ((dst_x_end & 1) && pair_x < pair_end) {
                mixed_pair(pair_x);
            }
            fill_bg(out, dst_w - pair_end);
        }
    }
}

// A selected kernel instantiation: converts row_count destination rows from first_row.
using ConvertFn = void (*)(const Descriptor &, uint8_t *, int, int);

// Resolve the destination packer tag and the source kind to a kernel instantiation.
// The descriptor carries rotation, mirror and pixel-double, so only indexed selects
// on the source side: a per-pixel palette test in the loop body cannot be hoisted,
// and costs the direct path about 5% of its convert budget.
inline ConvertFn select_convert(int dst_format, bool indexed) {
    if (dst_format == RGB444::format) {
        return indexed ? &convert_band<Indexed8, RGB444>
                       : &convert_band<RGBA8888, RGB444>;
    }
    return indexed ? &convert_band<Indexed8, RGB565>
                   : &convert_band<RGBA8888, RGB565>;
}

// Whether a conversion is halved across both cores. The module's dual_convert()
// binding clears it, so a tool can measure one core against two on one firmware.
inline bool dual_convert = true;

// Rows core1 has converted since boot. Monotonic, and sampled either side of a
// conversion so a frame can report its own share: a split that never engages
// otherwise looks exactly like one that works.
inline uint32_t core1_rows_total = 0;

#if SPIDISPLAY_PV_CORE1
// picovector's core1 worker, which its rasteriser, blit and blur filter also
// dispatch to. Declared rather than included, as picovector's own blur filter
// does for the same pair.
extern "C" void pv_core1_run(void (*fn)());
extern "C" void pv_core1_join();

// The job core1 picks up. One is enough: the dispatch below is synchronous, so
// the core0 caller holds the worker until the join and two can never be in
// flight. The descriptor is held by pointer, which stays valid for the same
// reason.
struct ConvertJob {
    ConvertFn convert;
    const Descriptor *desc;
    uint8_t *out;
    int first_row;
    int row_count;
};
inline ConvertJob convert_job = {};

inline void convert_rows_on_core1() {
    convert_job.convert(*convert_job.desc, convert_job.out, convert_job.first_row,
                        convert_job.row_count);
}
#endif

// Convert row_count destination rows from first_row, halved across both cores.
// Rows are independent and each half writes only its own, so neither locking nor
// a copy is needed. Synchronous: this returns with both halves converted.
//
// Only rows that read SRAM may be split, which sram_source marks. Halving a PSRAM
// range leaves the two cores at distant row offsets, where two interleaved read
// streams cost the shared QMI more than the halved pixel work saves: 0.84x
// against 1.60x from SRAM. The column cache reaches 1.60x on a PSRAM source too,
// its windows being SRAM.
//
// With neither define set this is one call, for a board carrying no core1 worker.
// SPIDISPLAY_SPLIT_SERIAL runs the halves in sequence instead, so the split's
// arithmetic can be checked with no second core to dispatch to.
inline void emit_rows(ConvertFn convert, const Descriptor &desc, uint8_t *out,
                      int first_row, int row_count, bool sram_source) {
#if SPIDISPLAY_PV_CORE1 || SPIDISPLAY_SPLIT_SERIAL
    if (dual_convert && sram_source && row_count >= 2) {
        const int first_half_rows = row_count / 2;
        uint8_t *second_half_out =
            out + (size_t)first_half_rows * desc.dst_row_bytes;
#if SPIDISPLAY_PV_CORE1
        convert_job = {convert, &desc, second_half_out,
                       first_row + first_half_rows, row_count - first_half_rows};
        pv_core1_run(convert_rows_on_core1);
        convert(desc, out, first_row, first_half_rows);
        pv_core1_join();
        core1_rows_total += (uint32_t)(row_count - first_half_rows);
#else
        convert(desc, out, first_row, first_half_rows);
        convert(desc, second_half_out, first_row + first_half_rows,
                row_count - first_half_rows);
#endif
        return;
    }
#endif
    convert(desc, out, first_row, row_count);
}

}  // namespace spidisplay
