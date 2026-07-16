// SPDX-License-Identifier: MIT
//
// Templated RGBA8888 -> RGB444 / RGB565 scanline conversion for the MightyFX
// display pipeline. Header-only so the host test harness compiles the same code
// the firmware runs (see boards/PIMORONI_MIGHTYFX/DISPLAY_PIPELINE_PLAN.md).
//
// The hot axes (packer, mirror, flip, rotate, pixel-double) are template
// parameters so each combination compiles to a branch-free, constant-folded
// loop. The loop-invariant fields (dimensions, offset, background, geometry)
// live in the runtime Descriptor. Output must match tests/reference.py
// byte-for-byte.

#pragma once

#include <cstdint>

namespace spidisplay {

// Runtime, loop-invariant conversion parameters. Computed once per frame.
struct Descriptor {
    const uint8_t *src;
    int src_w;
    int src_h;
    int dst_w;
    int dst_h;
    int off_x;          // Source top-left in the upright canvas (pre-rotation)
    int off_y;
    int region_w;       // Source extent in canvas pixels (src_w * scale)
    int region_h;       // Source extent in canvas pixels (src_h * scale)
    int dst_row_bytes;  // Packed bytes per destination row
    uint8_t bg_r;
    uint8_t bg_g;
    uint8_t bg_b;
};

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

// Resolve one destination pixel to its (r, g, b). The source is composed at its
// offset in an upright canvas, then the whole screen is rotated clockwise and
// mirror-flipped; here we invert that (un-mirror, inverse-rotate the output
// pixel back to the canvas) so destination rows are still produced in scan
// order and the origin corner tracks the transform.
template <class Src, int Rotation, bool Mirror, bool Double>
inline void sample(const Descriptor &d, int dst_x, int dst_y,
                   uint8_t &r, uint8_t &g, uint8_t &b) {
    int mx = Mirror ? (d.dst_w - 1 - dst_x) : dst_x;
    int my = dst_y;

    int cx;
    int cy;
    if constexpr (Rotation == 90) {
        cx = my;
        cy = d.dst_w - 1 - mx;
    } else if constexpr (Rotation == 180) {
        cx = d.dst_w - 1 - mx;
        cy = d.dst_h - 1 - my;
    } else if constexpr (Rotation == 270) {
        cx = d.dst_h - 1 - my;
        cy = mx;
    } else {
        cx = mx;
        cy = my;
    }

    int u = cx - d.off_x;
    int v = cy - d.off_y;
    if (u < 0 || u >= d.region_w || v < 0 || v >= d.region_h) {
        r = d.bg_r;
        g = d.bg_g;
        b = d.bg_b;
        return;
    }

    int sx = Double ? (u >> 1) : u;
    int sy = Double ? (v >> 1) : v;
    Src::load(d.src + (sy * d.src_w + sx) * Src::bytes, r, g, b);
}

// Convert a band of nrows destination rows, starting at row0, into dst_band
// (packed, one destination row per dst_row_bytes).
template <class Src, class Dst, int Rotation, bool Mirror, bool Double>
void convert_band(const Descriptor &d, uint8_t *dst_band, int row0, int nrows) {
    for (int row = 0; row < nrows; ++row) {
        int dst_y = row0 + row;
        uint8_t *out = dst_band + row * d.dst_row_bytes;

        if constexpr (Dst::pairs) {
            for (int dst_x = 0; dst_x < d.dst_w; dst_x += 2) {
                uint8_t r0, g0, b0, r1, g1, b1;
                sample<Src, Rotation, Mirror, Double>(d, dst_x, dst_y, r0, g0, b0);
                sample<Src, Rotation, Mirror, Double>(d, dst_x + 1, dst_y, r1, g1, b1);
                Dst::pack2(out, r0, g0, b0, r1, g1, b1);
                out += 3;
            }
        } else {
            for (int dst_x = 0; dst_x < d.dst_w; ++dst_x) {
                uint8_t r, g, b;
                sample<Src, Rotation, Mirror, Double>(d, dst_x, dst_y, r, g, b);
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

template <class Src, class Dst, int Rotation, bool Mirror>
inline ConvertFn select_dbl(bool dbl) {
    return dbl ? &convert_band<Src, Dst, Rotation, Mirror, true>
               : &convert_band<Src, Dst, Rotation, Mirror, false>;
}

template <class Src, class Dst, int Rotation>
inline ConvertFn select_mirror(bool mirror, bool dbl) {
    return mirror ? select_dbl<Src, Dst, Rotation, true>(dbl)
                  : select_dbl<Src, Dst, Rotation, false>(dbl);
}

template <class Src, class Dst>
inline ConvertFn select_rotation(int rotation, bool mirror, bool dbl) {
    switch (rotation) {
        case 90:
            return select_mirror<Src, Dst, 90>(mirror, dbl);
        case 180:
            return select_mirror<Src, Dst, 180>(mirror, dbl);
        case 270:
            return select_mirror<Src, Dst, 270>(mirror, dbl);
        default:
            return select_mirror<Src, Dst, 0>(mirror, dbl);
    }
}

// Resolve the runtime (format, transform, double) to a kernel instantiation.
inline ConvertFn select_convert(int fmt, const Transform &t, bool dbl) {
    if (fmt == RGB444::format) {
        return select_rotation<RGBA8888, RGB444>(t.rotation, t.mirror, dbl);
    }
    return select_rotation<RGBA8888, RGB565>(t.rotation, t.mirror, dbl);
}

// Fill a descriptor for a whole-frame conversion. Each axis is centred, or
// placed by its off_x/off_y top-left (before any whole-frame flip).
inline Descriptor make_descriptor(const uint8_t *src, int src_w, int src_h,
                                  int dst_w, int dst_h, const Transform &t,
                                  bool dbl, uint32_t bg, int fmt,
                                  bool centred_x, int off_x, bool centred_y, int off_y) {
    int scale = dbl ? 2 : 1;
    // Upright canvas: rotating it clockwise yields the dst_w x dst_h output, so
    // for 90/270 the canvas dimensions are swapped. The offset centres the
    // source's own extent within that canvas.
    bool swap = t.rotation == 90 || t.rotation == 270;
    int canvas_w = swap ? dst_h : dst_w;
    int canvas_h = swap ? dst_w : dst_h;

    Descriptor d;
    d.src = src;
    d.src_w = src_w;
    d.src_h = src_h;
    d.dst_w = dst_w;
    d.dst_h = dst_h;
    d.region_w = src_w * scale;
    d.region_h = src_h * scale;
    d.off_x = centred_x ? ((canvas_w - d.region_w) >> 1) : off_x;
    d.off_y = centred_y ? ((canvas_h - d.region_h) >> 1) : off_y;
    d.dst_row_bytes = (fmt == RGB444::format) ? (dst_w * 3 / 2) : (dst_w * 2);
    d.bg_r = bg & 0xff;
    d.bg_g = (bg >> 8) & 0xff;
    d.bg_b = (bg >> 16) & 0xff;
    return d;
}

}  // namespace spidisplay
