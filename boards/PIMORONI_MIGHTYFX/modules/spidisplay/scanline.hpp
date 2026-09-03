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

namespace spidisplay {

// Loop-invariant conversion parameters, calculated once per frame by
// make_descriptor.
//
// The source sits at its offset in the canvas, which is the destination before
// rotation. The canvas is then rotated clockwise and mirror-flipped. Inverting that
// maps each destination pixel onto u and v, the source column and row before
// pixel-double halving.
//
//   u = du_dx*dst_x + du_dy*dst_y + u_at_origin
//   v = dv_dx*dst_x + dv_dy*dst_y + v_at_origin
//
// One of u, v varies with dst_x and the other with dst_y, by rotation. So the
// source covers an axis-aligned destination box, and a row walk advances the
// source pointer by a constant step.
struct Descriptor {
    const uint8_t *src;
    const uint8_t *palette;   // 256 RGBA words for an indexed source, else null
    int dst_w;
    int dst_h;
    // The destination box the source covers, half-open on both axes.
    int dst_x_start, dst_x_end;
    int dst_y_start, dst_y_end;
    int du_dx, du_dy, u_at_origin;
    int dv_dx, dv_dy, v_at_origin;
    int src_row_bytes;      // Source pitch in bytes, row to row
    int src_pixel_bytes;    // Source bytes per pixel
    int src_step_x;         // Source pointer advance in bytes, per pixel along a row
    bool row_walks_src_columns;
    bool pixel_double;      // Each source pixel covers a 2x2 destination block
    // Which way the row walk moves through the source. Under pixel-double it also
    // fixes when a source pixel is used up, the source index being the coordinate
    // >> 1: a forward walk exhausts one on odd parity, a reverse walk on even.
    bool row_walks_forward;
    // A wrapped axis repeats the source: its coordinate reduces modulo the
    // extent instead of running out of it, so the covered box is the whole
    // frame on whichever destination axis it binds. A seam_reflects wrap reverses
    // every other repeat, the period doubling and the top half reading back
    // to front, so each seam is a reflection.
    bool wrap_u;
    bool wrap_v;
    bool wrap_mirror_u;
    bool wrap_mirror_v;
    int src_extent_w;       // Source extent in canvas pixels, doubled when pixel_double
    int src_extent_h;
    int dst_row_bytes;      // Packed bytes per destination row
    uint8_t bg_r;
    uint8_t bg_g;
    uint8_t bg_b;
};

// Floored modulo, reducing a coordinate of either sign into [0, period).
inline int floor_mod(int value, int period) {
    int m = value % period;
    return m < 0 ? m + period : m;
}

// A seam_reflects repeat's coordinate: the unfolded in [0, 2 * extent) folds onto
// [0, extent), the top half reading back to front, both edges repeating.
inline int fold(int unfolded, int extent) {
    return unfolded < extent ? unfolded : 2 * extent - 1 - unfolded;
}

// Source format traits, each carrying a Loader built once per band. RGBA8888's is
// empty and compiles away. Indexed8's reads the colour table, whose words sit in
// memory as RGBA bytes like a direct pixel.
//
// Only an indexed source composites, its table being the one thing compositable
// ahead of the pixel loop. So an RGBA source's alpha is ignored and its colour
// taken as premultiplied. Blending per pixel was measured to roughly double a
// panel-sized frame's conversion, taking it off its wire bound.
struct RGBA8888 {
    static constexpr int bytes = 4;

    struct Loader {
        explicit Loader(const Descriptor &) {}

        inline void load(const uint8_t *p, uint8_t &r, uint8_t &g, uint8_t &b) const {
            r = p[0];
            g = p[1];
            b = p[2];
        }
    };
};

struct Indexed8 {
    static constexpr int bytes = 1;

    struct Loader {
        explicit Loader(const Descriptor &desc) : pal(desc.palette) {}

        inline void load(const uint8_t *p, uint8_t &r, uint8_t &g, uint8_t &b) const {
            const uint8_t *entry = pal + ((size_t)*p << 2);
            r = entry[0];
            g = entry[1];
            b = entry[2];
        }

        const uint8_t *pal;
    };
};

// One channel of a premultiplied source over the background, the panel holding no
// destination pixels to read back.
//
// picovector stores colour already multiplied by its alpha, so the source is added
// and not scaled. Scaling again would darken a translucent entry by up to a quarter
// of the range. The arithmetic matches its blend_over_premul() byte for byte,
// rounding bias included.
//
// The clamp never engages on a valid entry. It is here because palette is
// caller-supplied, where an over-bright entry would carry into the next channel.
inline uint8_t composite_over(int src, int bg, int alpha) {
    if (alpha == 0) {
        return (uint8_t)bg;
    }
    if (alpha == 255) {
        return (uint8_t)src;
    }
    const int value = src + ((bg * (255 - alpha) + 128) >> 8);
    return (uint8_t)(value > 255 ? 255 : value);
}

// An index byte reaches all 256 entries whatever the source's table length, so
// prepare_palette zeroes the rest and an index past the source reads transparent.
static constexpr size_t PALETTE_BYTES = 256 * 4;

inline void prepare_palette(uint8_t *table, const uint8_t *palette, size_t palette_len,
                            uint8_t bg_r, uint8_t bg_g, uint8_t bg_b) {
    if (palette_len > PALETTE_BYTES) {
        palette_len = PALETTE_BYTES;
    }
    memcpy(table, palette, palette_len);
    memset(table + palette_len, 0, PALETTE_BYTES - palette_len);
    for (size_t i = 0; i < PALETTE_BYTES; i += 4) {
        const int alpha = table[i + 3];
        table[i] = composite_over(table[i], bg_r, alpha);
        table[i + 1] = composite_over(table[i + 1], bg_g, alpha);
        table[i + 2] = composite_over(table[i + 2], bg_b, alpha);
    }
}

// A wide pair-format background fill, four packed pixel pairs per 12-byte piece.
// A separate function deliberately: held in convert_band's body, block or loops,
// it cost the covered path 1% in register pressure. The count is even, as every
// fill's is.
__attribute__((noinline))
inline uint8_t *fill_bg_pairs(uint8_t *dst_ptr, int pixels, const uint8_t *bg_packed) {
    uint8_t block[12];
    for (int i = 0; i < 12; ++i) {
        block[i] = bg_packed[i % 3];
    }
    int i = 0;
    for (; i + 7 < pixels; i += 8) {
        memcpy(dst_ptr, block, 12);
        dst_ptr += 12;
    }
    for (; i < pixels; i += 2) {
        dst_ptr[0] = bg_packed[0];
        dst_ptr[1] = bg_packed[1];
        dst_ptr[2] = bg_packed[2];
        dst_ptr += 3;
    }
    return dst_ptr;
}

// Destination packers. RGB444 packs two pixels into three bytes; RGB565 packs one
// into two big-endian bytes. format is the runtime tag, and the panel bit depth.
// The three functions below are where a format is selected and its row priced. The
// kernels still carry each group's byte count as literals, and a tag neither packer
// owns is treated as RGB565, so a third packer touches convert_band and
// convert_wrapped_row as well as this block.
struct RGB444 {
    static constexpr int format = 444;
    static constexpr int bitdepth = 12;
    static constexpr bool pairs = true;
    static constexpr int group_pixels = 2;
    static constexpr int group_bytes = 3;

    static inline void pack2(uint8_t *out,
                             uint8_t r0, uint8_t g0, uint8_t b0,
                             uint8_t r1, uint8_t g1, uint8_t b1) {
        out[0] = (r0 & 0xf0) | (g0 >> 4);   // R1 | G1
        out[1] = (b0 & 0xf0) | (r1 >> 4);   // B1 | R2
        out[2] = (g1 & 0xf0) | (b1 >> 4);   // G2 | B2
    }
};

struct RGB565 {
    static constexpr int format = 565;
    static constexpr int bitdepth = 16;
    static constexpr bool pairs = false;
    static constexpr int group_pixels = 1;
    static constexpr int group_bytes = 2;

    static inline void pack1(uint8_t *out, uint8_t r, uint8_t g, uint8_t b) {
        const uint16_t value = (uint16_t)__builtin_bswap16(
            ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3));
        memcpy(out, &value, 2);
    }
};

// The packer tag for a panel bit depth, 0 where no packer exists for it
inline int format_for_bitdepth(int bitdepth) {
    if (bitdepth == RGB444::bitdepth) {
        return RGB444::format;
    }
    if (bitdepth == RGB565::bitdepth) {
        return RGB565::format;
    }
    return 0;
}

// Pixels a row width has to be a multiple of, so a packed row ends on a whole group
inline int pixels_per_group(int format) {
    return format == RGB444::format ? RGB444::group_pixels : RGB565::group_pixels;
}

// One packed destination row's bytes at this width
inline int packed_row_bytes(int format, int dst_w) {
    return format == RGB444::format
        ? dst_w / RGB444::group_pixels * RGB444::group_bytes
        : dst_w / RGB565::group_pixels * RGB565::group_bytes;
}

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

// Runtime transform: clockwise rotation (0/90/180/270) then a horizontal
// mirror of the output.
struct Transform {
    int rotation;
    bool mirror;
};

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

// Fill a descriptor for a whole-frame conversion. Each axis is centred, or placed
// by its off_x/off_y top-left in the canvas. wrap_x and wrap_y repeat the source
// on that axis of its own: any offset is then valid, the origin reducing modulo
// the period here so a caller's ever-growing offset never overflows the affine
// ints. wrap_mirror_x and wrap_mirror_y reverse every other repeat, and imply
// the wrap on their axis. src_row_bytes is the source pitch, wider than a row
// on a strided view into a larger image.
inline Descriptor make_descriptor(const uint8_t *src, int src_w, int src_h,
                                  int dst_w, int dst_h, int format,
                                  const Transform &transform, bool pixel_double,
                                  bool centred_x, int off_x, bool centred_y, int off_y,
                                  bool wrap_x, bool wrap_y,
                                  bool wrap_mirror_x, bool wrap_mirror_y,
                                  uint32_t bg,
                                  int src_row_bytes, int src_pixel_bytes) {
    int scale = pixel_double ? 2 : 1;
    int src_extent_w = src_w * scale;   // Source extent in canvas pixels
    int src_extent_h = src_h * scale;

    // Rotating the canvas clockwise yields the dst_w x dst_h output, so for 90/270
    // its dimensions are the swapped ones.
    bool swap_axes = (transform.rotation == 90 || transform.rotation == 270);
    int canvas_w = swap_axes ? dst_h : dst_w;
    int canvas_h = swap_axes ? dst_w : dst_h;
    int place_x = centred_x ? ((canvas_w - src_extent_w) >> 1) : off_x;
    int place_y = centred_y ? ((canvas_h - src_extent_h) >> 1) : off_y;

    // Keep the affine arithmetic clear of the machine word's edges: a wrapped
    // axis reduces its placement here, and an unwrapped one already far enough
    // out to cover nothing clamps to a band that still covers nothing. Every
    // offset the binding can pass is then exact.
    wrap_x = wrap_x || wrap_mirror_x;
    wrap_y = wrap_y || wrap_mirror_y;
    constexpr int PLACE_LIMIT = 1 << 28;
    if (wrap_x) {
        place_x = floor_mod(place_x, wrap_mirror_x ? 2 * src_extent_w : src_extent_w);
    } else if (place_x > PLACE_LIMIT) {
        place_x = PLACE_LIMIT;
    } else if (place_x < -PLACE_LIMIT) {
        place_x = -PLACE_LIMIT;
    }
    if (wrap_y) {
        place_y = floor_mod(place_y, wrap_mirror_y ? 2 * src_extent_h : src_extent_h);
    } else if (place_y > PLACE_LIMIT) {
        place_y = PLACE_LIMIT;
    } else if (place_y < -PLACE_LIMIT) {
        place_y = -PLACE_LIMIT;
    }

    // mx = mirror_step*dst_x + mirror_base folds the output mirror into the
    // coefficients below.
    int mirror_step = transform.mirror ? -1 : 1;
    int mirror_base = transform.mirror ? (dst_w - 1) : 0;

    // Canvas coordinates as affine functions of the destination pixel. cx/cy are
    // the inverse-rotated (un-seam_reflects) destination pixel; u/v subtract the
    // source offset. Exactly one of u, v varies with dst_x, the other with dst_y.
    int du_dx, du_dy, u_at_origin, dv_dx, dv_dy, v_at_origin;
    switch (transform.rotation) {
        case 90:   // cx = dst_y, cy = (dst_w-1) - mx
            du_dx = 0;             du_dy = 1;
            dv_dx = -mirror_step;  dv_dy = 0;
            u_at_origin = -place_x;
            v_at_origin = (dst_w - 1 - mirror_base) - place_y;
            break;
        case 180:  // cx = (dst_w-1) - mx, cy = (dst_h-1) - dst_y
            du_dx = -mirror_step;  du_dy = 0;
            dv_dx = 0;             dv_dy = -1;
            u_at_origin = (dst_w - 1 - mirror_base) - place_x;
            v_at_origin = (dst_h - 1) - place_y;
            break;
        case 270:  // cx = (dst_h-1) - dst_y, cy = mx
            du_dx = 0;             du_dy = -1;
            dv_dx = mirror_step;   dv_dy = 0;
            u_at_origin = (dst_h - 1) - place_x;
            v_at_origin = mirror_base - place_y;
            break;
        default:   // 0: cx = mx, cy = dst_y
            du_dx = mirror_step;   du_dy = 0;
            dv_dx = 0;             dv_dy = 1;
            u_at_origin = mirror_base - place_x;
            v_at_origin = -place_y;
            break;
    }

    if (wrap_x) {
        u_at_origin = floor_mod(u_at_origin,
                                wrap_mirror_x ? 2 * src_extent_w : src_extent_w);
    }
    if (wrap_y) {
        v_at_origin = floor_mod(v_at_origin,
                                wrap_mirror_y ? 2 * src_extent_h : src_extent_h);
    }

    // Solve 0 <= coeff*dst + base < src_extent for integer dst (coeff is +/-1),
    // then clamp to the destination extent. Yields the covered span on one axis.
    // A wrapped coordinate covers the whole frame on the axis it binds.
    auto range = [](int coeff, int base, int src_extent, int dst_extent,
                    int &span_start, int &span_end) {
        if (coeff > 0) {
            span_start = -base;
            span_end = src_extent - base;
        } else {
            span_start = base - src_extent + 1;
            span_end = base + 1;
        }
        if (span_start < 0) span_start = 0;
        if (span_end > dst_extent) span_end = dst_extent;
        if (span_end < span_start) span_end = span_start;
    };

    Descriptor desc;
    desc.src = src;
    desc.palette = nullptr;   // An indexed caller points this at its colour table
    desc.dst_w = dst_w;
    desc.dst_h = dst_h;
    desc.du_dx = du_dx; desc.du_dy = du_dy; desc.u_at_origin = u_at_origin;
    desc.dv_dx = dv_dx; desc.dv_dy = dv_dy; desc.v_at_origin = v_at_origin;
    desc.src_row_bytes = src_row_bytes;
    desc.src_pixel_bytes = src_pixel_bytes;
    desc.pixel_double = pixel_double;

    desc.wrap_u = wrap_x;
    desc.wrap_v = wrap_y;
    desc.wrap_mirror_u = wrap_mirror_x;
    desc.wrap_mirror_v = wrap_mirror_y;
    desc.src_extent_w = src_extent_w;
    desc.src_extent_h = src_extent_h;

    // dst_x is bound by whichever coordinate varies with it, and supplies the
    // per-pixel source stride; dst_y is bound by the other coordinate.
    if (du_dx != 0) {
        if (wrap_x) {
            desc.dst_x_start = 0;
            desc.dst_x_end = dst_w;
        } else {
            range(du_dx, u_at_origin, src_extent_w, dst_w,
                  desc.dst_x_start, desc.dst_x_end);
        }
        desc.row_walks_src_columns = true;
        desc.src_step_x = (du_dx > 0 ? 1 : -1) * src_pixel_bytes;
        desc.row_walks_forward = (du_dx > 0);
    } else {
        if (wrap_y) {
            desc.dst_x_start = 0;
            desc.dst_x_end = dst_w;
        } else {
            range(dv_dx, v_at_origin, src_extent_h, dst_w,
                  desc.dst_x_start, desc.dst_x_end);
        }
        desc.row_walks_src_columns = false;
        desc.src_step_x = (dv_dx > 0 ? 1 : -1) * desc.src_row_bytes;
        desc.row_walks_forward = (dv_dx > 0);
    }
    if (du_dy != 0) {
        if (wrap_x) {
            desc.dst_y_start = 0;
            desc.dst_y_end = dst_h;
        } else {
            range(du_dy, u_at_origin, src_extent_w, dst_h,
                  desc.dst_y_start, desc.dst_y_end);
        }
    } else {
        if (wrap_y) {
            desc.dst_y_start = 0;
            desc.dst_y_end = dst_h;
        } else {
            range(dv_dy, v_at_origin, src_extent_h, dst_h,
                  desc.dst_y_start, desc.dst_y_end);
        }
    }

    desc.dst_row_bytes = packed_row_bytes(format, dst_w);
    desc.bg_r = bg & 0xff;
    desc.bg_g = (bg >> 8) & 0xff;
    desc.bg_b = (bg >> 16) & 0xff;
    return desc;
}

}  // namespace spidisplay
