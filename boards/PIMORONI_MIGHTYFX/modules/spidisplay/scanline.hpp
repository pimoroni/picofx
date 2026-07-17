// SPDX-License-Identifier: MIT
//
// Templated RGBA8888 -> RGB444 / RGB565 scanline conversion for the MightyFX
// display pipeline. Header-only so the host test harness compiles the same code
// the firmware runs (see boards/PIMORONI_MIGHTYFX/DISPLAY_PIPELINE_PLAN.md).
//
// Geometry is resolved once per frame into a Descriptor: the source position in
// the destination reduces to an affine map, so the covered destination box and a
// pair of source pointer strides are computed up front. The inner loop then just
// walks a source pointer, with no per-pixel coordinate maths, multiply, or
// bounds branch across the covered span. Only the axes that change the loop body
// (destination packer, pixel-double) are template parameters; rotation and
// mirror are carried as runtime strides. Output must match tests/reference.py
// byte-for-byte.

#pragma once

#include <cstdint>

namespace spidisplay {

// Source format trait.
struct RGBA8888 {
    static constexpr int bytes = 4;

    static inline void load(const uint8_t *p, uint8_t &r, uint8_t &g, uint8_t &b) {
        r = p[0];
        g = p[1];
        b = p[2];
    }
};

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
    int dst_w;
    int dst_h;
    int dx0, dx1;        // Covered destination columns [dx0, dx1)
    int dy0, dy1;        // Covered destination rows [dy0, dy1)
    int ua, ub, uc;      // Canvas u = ua*dst_x + ub*dst_y + uc
    int va, vb, vc;      // Canvas v = va*dst_x + vb*dst_y + vc
    int src_row_bytes;   // src_w * source bytes/pixel
    int step_x;          // Source pointer advance (bytes) per source pixel along a row
    bool x_uses_u;       // The row walk varies u (else v)
    bool x_adv;          // Advance parity for the row walk (pixel-double only)
    int dst_row_bytes;   // Packed bytes per destination row
    uint8_t bg_r;
    uint8_t bg_g;
    uint8_t bg_b;
};

// Convert nrows destination rows starting at row0 into dst_band (packed, one
// destination row per dst_row_bytes). Rows outside the covered box, and the
// uncovered ends of covered rows, are filled with the background.
template <class Src, class Dst, bool Double>
void convert_band(const Descriptor &d, uint8_t *dst_band, int row0, int nrows) {
    for (int row = 0; row < nrows; ++row) {
        int dst_y = row0 + row;
        uint8_t *out = dst_band + row * d.dst_row_bytes;
        bool row_covered = (dst_y >= d.dy0 && dst_y < d.dy1);

        // Seed the row walk at the first covered column (dst_x == dx0). The
        // pointer is only read and advanced inside the covered span, so seeding
        // it here and stepping from there tracks the affine map exactly.
        const uint8_t *sp = d.src;
        int xpar = 0;
        if (row_covered) {
            int u0 = d.ua * d.dx0 + d.ub * dst_y + d.uc;
            int v0 = d.va * d.dx0 + d.vb * dst_y + d.vc;
            int col = Double ? (u0 >> 1) : u0;
            int srow = Double ? (v0 >> 1) : v0;
            sp = d.src + (long)srow * d.src_row_bytes + (long)col * Src::bytes;
            if constexpr (Double) {
                xpar = (d.x_uses_u ? u0 : v0) & 1;
            }
        }

        // Fetch one destination pixel: the source sample inside the covered span,
        // background outside it. Pixel-double advances the source every second
        // pixel, phased so clipping and mirroring stay aligned.
        auto fetch = [&](int dst_x, uint8_t &r, uint8_t &g, uint8_t &b) {
            if (row_covered && (unsigned)(dst_x - d.dx0) < (unsigned)(d.dx1 - d.dx0)) {
                Src::load(sp, r, g, b);
                if constexpr (Double) {
                    if (xpar == (int)d.x_adv) {
                        sp += d.step_x;
                    }
                    xpar ^= 1;
                } else {
                    sp += d.step_x;
                }
            } else {
                r = d.bg_r;
                g = d.bg_g;
                b = d.bg_b;
            }
        };

        if constexpr (Dst::pairs) {
            for (int dst_x = 0; dst_x < d.dst_w; dst_x += 2) {
                uint8_t r0, g0, b0, r1, g1, b1;
                fetch(dst_x, r0, g0, b0);
                fetch(dst_x + 1, r1, g1, b1);
                Dst::pack2(out, r0, g0, b0, r1, g1, b1);
                out += 3;
            }
        } else {
            for (int dst_x = 0; dst_x < d.dst_w; ++dst_x) {
                uint8_t r, g, b;
                fetch(dst_x, r, g, b);
                Dst::pack1(out, r, g, b);
                out += 2;
            }
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

template <class Src, class Dst>
inline ConvertFn select_dbl(bool dbl) {
    return dbl ? &convert_band<Src, Dst, true>
               : &convert_band<Src, Dst, false>;
}

// Resolve the runtime format to a kernel instantiation. Rotation and mirror are
// runtime strides in the descriptor, so they are not part of the selection.
inline ConvertFn select_convert(int fmt, bool dbl) {
    if (fmt == RGB444::format) {
        return select_dbl<RGBA8888, RGB444>(dbl);
    }
    return select_dbl<RGBA8888, RGB565>(dbl);
}

// Fill a descriptor for a whole-frame conversion. Each axis is centred, or
// placed by its off_x/off_y top-left in the upright canvas.
inline Descriptor make_descriptor(const uint8_t *src, int src_w, int src_h,
                                  int dst_w, int dst_h, const Transform &t,
                                  bool dbl, uint32_t bg, int fmt,
                                  bool centred_x, int off_x, bool centred_y, int off_y) {
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
    d.dst_w = dst_w;
    d.dst_h = dst_h;
    d.ua = ua; d.ub = ub; d.uc = uc;
    d.va = va; d.vb = vb; d.vc = vc;
    d.src_row_bytes = src_w * RGBA8888::bytes;

    // dst_x is bound by whichever coordinate varies with it, and supplies the
    // per-pixel source stride; dst_y is bound by the other coordinate.
    if (ua != 0) {
        range(ua, uc, region_w, W, d.dx0, d.dx1);
        d.x_uses_u = true;
        d.step_x = (ua > 0 ? 1 : -1) * RGBA8888::bytes;
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
