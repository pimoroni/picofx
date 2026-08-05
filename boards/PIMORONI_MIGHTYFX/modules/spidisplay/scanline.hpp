// SPDX-License-Identifier: MIT
//
// Templated RGBA8888 -> RGB444 / RGB565 scanline conversion for the MightyFX
// display pipeline, an indexed source composited over the background colour
// through its palette. Header-only so the host test harness compiles the same
// code the firmware runs.
//
// Geometry is resolved once per frame into a Descriptor: the source position in
// the destination reduces to an affine map, so the covered destination box and a
// pair of source pointer strides are computed up front. The inner loop then just
// walks a source pointer, with no per-pixel coordinate maths, multiply, or
// bounds branch across the covered span. Only the axes that change the loop body
// (source format, destination packer) are template parameters; rotation, mirror
// and pixel-double are carried in the Descriptor.

#pragma once

#include <cstdint>
#include <cstring>

namespace spidisplay {

// Runtime, loop-invariant conversion parameters. Computed once per frame by
// make_descriptor.
//
// The source is composed at its offset in an upright canvas, the whole screen is
// then rotated clockwise and mirror-flipped. Inverting that, each destination
// pixel maps to a canvas coordinate that is affine in (dst_x, dst_y):
//
//   u = ua*dst_x + ub*dst_y + uc   (source column, before pixel-double)
//   v = va*dst_x + vb*dst_y + vc   (source row,    before pixel-double)
//
// One of u, v varies with dst_x and the other with dst_y (rotation swaps which),
// so the region the source covers is an axis-aligned destination box
// [dx0, dx1) x [dy0, dy1), and along a row the source pointer advances by the
// constant step_x per pixel.
struct Descriptor {
    const uint8_t *src;
    const uint8_t *palette;   // 256 RGBA words for an indexed source, else null
    int dst_w;
    int dst_h;
    int dx0, dx1;        // Covered destination columns [dx0, dx1)
    int dy0, dy1;        // Covered destination rows [dy0, dy1)
    int ua, ub, uc;      // Canvas u = ua*dst_x + ub*dst_y + uc
    int va, vb, vc;      // Canvas v = va*dst_x + vb*dst_y + vc
    int src_row_bytes;   // Source pitch in bytes, row to row
    int src_bytes;       // Source bytes per pixel
    int step_x;          // Source pointer advance (bytes) per source pixel along a row
    bool x_uses_u;       // The row walk varies u (else v)
    bool pixel_double;   // Each source pixel covers a 2x2 destination block
    bool x_adv;          // Advance parity for the row walk (pixel-double only)
    int dst_row_bytes;   // Packed bytes per destination row
    uint8_t bg_r;
    uint8_t bg_g;
    uint8_t bg_b;
};

// Source format traits. Each carries a Loader, built once per band from the
// descriptor: RGBA8888's is empty and compiles away, and Indexed8's dereferences
// the colour table, whose words sit in memory as R, G, B, A exactly like a direct
// pixel.
//
// Only an indexed source composites, because only its table can be composited
// ahead of the pixel loop. A per-pixel blend was measured at 415ns per source
// pixel, which roughly doubles the conversion of a panel-sized RGBA frame and
// takes it off its wire bound, so an RGBA source's alpha byte is ignored. Its
// colour is premultiplied, so a translucent pixel draws as if composited against
// black.
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
        explicit Loader(const Descriptor &d) : pal(d.palette) {}

        inline void load(const uint8_t *p, uint8_t &r, uint8_t &g, uint8_t &b) const {
            const uint8_t *entry = pal + ((size_t)*p << 2);
            r = entry[0];
            g = entry[1];
            b = entry[2];
        }

        const uint8_t *pal;
    };
};

// One channel of a premultiplied source over the background. The panel holds no
// destination pixels to read back, so the background an uncovered pixel already
// takes is what a translucent one resolves against.
//
// picovector stores colour already multiplied by its own alpha, in palette
// entries and in RGBA pixels alike, so the source is added rather than scaled.
// Scaling it again would darken a translucent entry by up to a quarter of the
// range.
//
// The arithmetic matches picovector's own blend_over_premul() byte for byte, so
// compositing against bg here and blitting onto a canvas filled with bg give the
// same pixels. That is what the endpoint tests and the rounding bias are for; the
// bias alone moves 37% of channel values by one.
//
// The clamp is the one deliberate difference: picovector relies on its source
// being premultiplied, while palette here is caller-supplied bytes, and an entry
// claiming more colour than its alpha allows would otherwise carry into the next
// channel. It never engages on a valid entry, and runs per entry rather than per
// pixel.
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

// The colour table an indexed source is drawn through, its RGBA words copied
// into table and composited over the background. Entries past palette_len are
// zeroed, so an index byte reaching past the source's own entries reads as
// transparent; an index byte reaches all 256 whatever the table's length.
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

// Destination packers. RGB444 packs two pixels into three bytes; RGB565 packs
// one pixel into two big-endian bytes. format is the runtime tag carried
// through the pipeline (also the panel bit depth: 444 = 12-bit, 565 = 16-bit).
struct RGB444 {
    static constexpr int format = 444;
    static constexpr bool pairs = true;

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
    static constexpr bool pairs = false;

    static inline void pack1(uint8_t *out, uint8_t r, uint8_t g, uint8_t b) {
        uint16_t value = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
        out[0] = (value >> 8) & 0xff;
        out[1] = value & 0xff;
    }
};

// Convert nrows destination rows starting at row0 into dst_band (packed, one
// destination row per dst_row_bytes). Rows outside the covered box, and the
// uncovered ends of covered rows, are filled with the background.
//
// Fields read inside the pixel loops are copied to locals first: the output is
// written through a uint8_t pointer, which may alias the descriptor, so field
// reads would otherwise be repeated after every store. Each covered row is
// emitted as background / covered span / background, keeping the bounds test
// out of the covered loop; for pair formats a pair straddling an odd covered
// boundary mixes source and background and is emitted separately.
template <class Src, class Dst>
void convert_band(const Descriptor &d, uint8_t *dst_band, int row0, int nrows) {
    const int dst_w = d.dst_w;
    const int dx0 = d.dx0, dx1 = d.dx1;
    const int step_x = d.step_x;
    const bool dbl = d.pixel_double;
    const int x_adv = d.x_adv ? 1 : 0;
    const uint8_t bg_r = d.bg_r, bg_g = d.bg_g, bg_b = d.bg_b;
    const typename Src::Loader loader(d);

    // Packed background: one pixel pair (three bytes) or one pixel (two bytes).
    uint8_t bgp[3] = {0, 0, 0};
    if constexpr (Dst::pairs) {
        Dst::pack2(bgp, bg_r, bg_g, bg_b, bg_r, bg_g, bg_b);
    } else {
        Dst::pack1(bgp, bg_r, bg_g, bg_b);
    }

    // Fill n background pixels (n is even for pair formats) and return the
    // advanced output pointer.
    auto fill_bg = [&](uint8_t *o, int n) {
        if constexpr (Dst::pairs) {
            for (int i = 0; i < n; i += 2) {
                o[0] = bgp[0]; o[1] = bgp[1]; o[2] = bgp[2];
                o += 3;
            }
        } else {
            const uint32_t pat = (uint32_t)bgp[0] | ((uint32_t)bgp[1] << 8)
                               | ((uint32_t)bgp[0] << 16) | ((uint32_t)bgp[1] << 24);
            int i = 0;
            for (; i + 1 < n; i += 2) {
                memcpy(o, &pat, 4);
                o += 4;
            }
            if (i < n) {
                o[0] = bgp[0]; o[1] = bgp[1];
                o += 2;
            }
        }
        return o;
    };

    for (int row = 0; row < nrows; ++row) {
        const int dst_y = row0 + row;
        uint8_t *out = dst_band + row * d.dst_row_bytes;

        if (dst_y < d.dy0 || dst_y >= d.dy1 || dx0 >= dx1) {
            fill_bg(out, dst_w);
            continue;
        }

        // Seed the row walk at the first covered column (dst_x == dx0). The
        // pointer is only read and advanced inside the covered span, so seeding
        // it here and stepping from there tracks the affine map exactly.
        const int u0 = d.ua * dx0 + d.ub * dst_y + d.uc;
        const int v0 = d.va * dx0 + d.vb * dst_y + d.vc;
        const int col = dbl ? (u0 >> 1) : u0;
        const int srow = dbl ? (v0 >> 1) : v0;
        const uint8_t *sp = d.src + (long)srow * d.src_row_bytes + (long)col * Src::bytes;
        int xpar = 0;
        if (dbl) {
            xpar = (d.x_uses_u ? u0 : v0) & 1;
        }

        if constexpr (!Dst::pairs) {
            out = fill_bg(out, dx0);
            uint8_t r, g, b;
            if (dbl) {
                // The source advances once per two destination pixels, when
                // xpar == x_adv. A leading pixel where that lands first aligns
                // the walk so each remaining source pixel is emitted twice.
                int x = dx0;
                if (xpar == x_adv) {
                    loader.load(sp, r, g, b);
                    sp += step_x;
                    Dst::pack1(out, r, g, b);
                    out += 2;
                    ++x;
                }
                for (; x + 1 < dx1; x += 2) {
                    loader.load(sp, r, g, b);
                    sp += step_x;
                    Dst::pack1(out, r, g, b);
                    Dst::pack1(out + 2, r, g, b);
                    out += 4;
                }
                if (x < dx1) {
                    loader.load(sp, r, g, b);
                    Dst::pack1(out, r, g, b);
                    out += 2;
                }
            } else {
                for (int x = dx0; x < dx1; ++x) {
                    loader.load(sp, r, g, b);
                    sp += step_x;
                    Dst::pack1(out, r, g, b);
                    out += 2;
                }
            }
            fill_bg(out, dst_w - dx1);
        } else {
            // Pair-aligned bounds of the covered span. The pairs at a and b - 2
            // are mixed when the boundary is odd; pairs between them are fully
            // covered.
            const int a = dx0 & ~1;
            const int b = (dx1 + 1) & ~1;
            out = fill_bg(out, a);

            // Emit one mixed pair with a per-pixel bounds test. Pixel-double
            // advances the source every second covered pixel, phased so
            // clipping and mirroring stay aligned; xpar tracks that phase
            // across the whole covered span.
            auto fetch = [&](int x, uint8_t &r, uint8_t &g, uint8_t &b) {
                if ((unsigned)(x - dx0) < (unsigned)(dx1 - dx0)) {
                    loader.load(sp, r, g, b);
                    if (dbl) {
                        if (xpar == x_adv) {
                            sp += step_x;
                        }
                        xpar ^= 1;
                    } else {
                        sp += step_x;
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

            int p = a;
            if (dx0 & 1) {
                mixed_pair(p);
                p += 2;
            }
            const int ie = (dx1 & 1) ? b - 2 : b;
            if (dbl) {
                // One source advance per pair. Whole pairs leave xpar
                // unchanged, so the phase holds across the loop.
                uint8_t r, g, b;
                if (xpar == x_adv) {
                    // The advance lands after the first pixel: a pair spans two
                    // adjacent source pixels, and doubling straddles pairs.
                    for (; p < ie; p += 2) {
                        uint8_t r1, g1, b1;
                        loader.load(sp, r, g, b);
                        sp += step_x;
                        loader.load(sp, r1, g1, b1);
                        Dst::pack2(out, r, g, b, r1, g1, b1);
                        out += 3;
                    }
                } else {
                    // Pair-aligned doubling: both pixels repeat one source pixel.
                    for (; p < ie; p += 2) {
                        loader.load(sp, r, g, b);
                        sp += step_x;
                        Dst::pack2(out, r, g, b, r, g, b);
                        out += 3;
                    }
                }
            } else {
                for (; p < ie; p += 2) {
                    uint8_t r0, g0, b0, r1, g1, b1;
                    loader.load(sp, r0, g0, b0);
                    sp += step_x;
                    loader.load(sp, r1, g1, b1);
                    sp += step_x;
                    Dst::pack2(out, r0, g0, b0, r1, g1, b1);
                    out += 3;
                }
            }
            if ((dx1 & 1) && p < b) {
                mixed_pair(p);
            }
            fill_bg(out, dst_w - b);
        }
    }
}

// Runtime transform: clockwise rotation (0/90/180/270) then a horizontal
// mirror of the output.
struct Transform {
    int rotation;
    bool mirror;
};

inline Transform map_transform(int rotation, int mirror) {
    return {rotation, mirror != 0};
}

// A selected kernel instantiation: converts nrows destination rows from row0.
using ConvertFn = void (*)(const Descriptor &, uint8_t *, int, int);

// Resolve the runtime formats to a kernel instantiation. Rotation, mirror and
// pixel-double are carried in the descriptor, so they are not part of the
// selection; the source format is, because a per-pixel palette test in the loop
// body cannot be hoisted and costs the direct path about 5% of its convert
// budget.
inline ConvertFn select_convert(int fmt, bool indexed) {
    if (fmt == RGB444::format) {
        return indexed ? &convert_band<Indexed8, RGB444>
                       : &convert_band<RGBA8888, RGB444>;
    }
    return indexed ? &convert_band<Indexed8, RGB565>
                   : &convert_band<RGBA8888, RGB565>;
}

// Fill a descriptor for a whole-frame conversion. Each axis is centred, or
// placed by its off_x/off_y top-left in the upright canvas. src_row_bytes is
// the source pitch, which exceeds src_w * src_bytes when the source is a
// strided view into a wider image; 0 means contiguous.
inline Descriptor make_descriptor(const uint8_t *src, int src_w, int src_h,
                                  int dst_w, int dst_h, const Transform &t,
                                  bool dbl, uint32_t bg, int fmt,
                                  bool centred_x, int off_x, bool centred_y, int off_y,
                                  int src_row_bytes, int src_bytes) {
    int scale = dbl ? 2 : 1;
    int region_w = src_w * scale;   // Source extent in canvas pixels
    int region_h = src_h * scale;
    int W = dst_w;
    int H = dst_h;

    // Upright canvas: rotating it clockwise yields the dst_w x dst_h output, so
    // for 90/270 the canvas dimensions are swapped. The offset centres the
    // source's own extent within that canvas.
    bool swap = (t.rotation == 90 || t.rotation == 270);
    int canvas_w = swap ? dst_h : dst_w;
    int canvas_h = swap ? dst_w : dst_h;
    int off_x_r = centred_x ? ((canvas_w - region_w) >> 1) : off_x;
    int off_y_r = centred_y ? ((canvas_h - region_h) >> 1) : off_y;

    // mx = m*dst_x + k folds the output mirror into the coefficients below.
    int m = t.mirror ? -1 : 1;
    int k = t.mirror ? (W - 1) : 0;

    // Canvas coordinates as affine functions of the destination pixel. cx/cy are
    // the inverse-rotated (un-mirrored) destination pixel; u/v subtract the
    // source offset. Exactly one of u, v varies with dst_x, the other with dst_y.
    int ua, ub, uc, va, vb, vc;
    switch (t.rotation) {
        case 90:   // cx = dst_y ; cy = (W-1) - mx
            ua = 0;  ub = 1;  uc = -off_x_r;
            va = -m; vb = 0;  vc = (W - 1 - k) - off_y_r;
            break;
        case 180:  // cx = (W-1) - mx ; cy = (H-1) - dst_y
            ua = -m; ub = 0;  uc = (W - 1 - k) - off_x_r;
            va = 0;  vb = -1; vc = (H - 1) - off_y_r;
            break;
        case 270:  // cx = (H-1) - dst_y ; cy = mx
            ua = 0;  ub = -1; uc = (H - 1) - off_x_r;
            va = m;  vb = 0;  vc = k - off_y_r;
            break;
        default:   // 0: cx = mx ; cy = dst_y
            ua = m;  ub = 0;  uc = k - off_x_r;
            va = 0;  vb = 1;  vc = -off_y_r;
            break;
    }

    // Solve 0 <= a*t + c < lim for integer t (a is +/-1), then clamp to the
    // destination extent. Yields the covered span on one destination axis.
    auto range = [](int a, int c, int lim, int dst_lim, int &lo, int &hi) {
        if (a > 0) {
            lo = -c;
            hi = lim - c;
        } else {
            lo = c - lim + 1;
            hi = c + 1;
        }
        if (lo < 0) lo = 0;
        if (hi > dst_lim) hi = dst_lim;
        if (hi < lo) hi = lo;
    };

    Descriptor d;
    d.src = src;
    d.palette = nullptr;   // An indexed caller points this at its colour table
    d.dst_w = dst_w;
    d.dst_h = dst_h;
    d.ua = ua; d.ub = ub; d.uc = uc;
    d.va = va; d.vb = vb; d.vc = vc;
    d.src_row_bytes = src_row_bytes > 0 ? src_row_bytes : src_w * src_bytes;
    d.src_bytes = src_bytes;
    d.pixel_double = dbl;

    // dst_x is bound by whichever coordinate varies with it, and supplies the
    // per-pixel source stride; dst_y is bound by the other coordinate.
    if (ua != 0) {
        range(ua, uc, region_w, W, d.dx0, d.dx1);
        d.x_uses_u = true;
        d.step_x = (ua > 0 ? 1 : -1) * src_bytes;
        d.x_adv = (ua > 0);
    } else {
        range(va, vc, region_h, W, d.dx0, d.dx1);
        d.x_uses_u = false;
        d.step_x = (va > 0 ? 1 : -1) * d.src_row_bytes;
        d.x_adv = (va > 0);
    }
    if (ub != 0) {
        range(ub, uc, region_w, H, d.dy0, d.dy1);
    } else {
        range(vb, vc, region_h, H, d.dy0, d.dy1);
    }

    d.dst_row_bytes = (fmt == RGB444::format) ? (dst_w * 3 / 2) : (dst_w * 2);
    d.bg_r = bg & 0xff;
    d.bg_g = (bg >> 8) & 0xff;
    d.bg_b = (bg >> 16) & 0xff;
    return d;
}

}  // namespace spidisplay
