// SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
//
// SPDX-License-Identifier: MIT
//
// Where a frame lands on a panel, and the affine map the pixel loops walk. Filled by
// make_descriptor once a frame, then read by every conversion that frame does.

#pragma once

#include <cstdint>

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

// Runtime transform: clockwise rotation (0/90/180/270) then a horizontal
// mirror of the output.
struct Transform {
    int rotation;
    bool mirror;
};

// Fill a descriptor for a whole-frame conversion. Each axis is centred, or placed
// by its off_x/off_y top-left in the canvas. wrap_x and wrap_y repeat the source
// on that axis of its own: any offset is then valid, the origin reducing modulo
// the period here so a caller's ever-growing offset never overflows the affine
// ints. wrap_mirror_x and wrap_mirror_y reverse every other repeat, and imply
// the wrap on their axis. src_row_bytes is the source pitch, wider than a row
// on a strided view into a larger image.
inline Descriptor make_descriptor(const uint8_t *src, int src_w, int src_h,
                                  int dst_w, int dst_h, int dst_row_bytes,
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

    desc.dst_row_bytes = dst_row_bytes;
    desc.bg_r = bg & 0xff;
    desc.bg_g = (bg >> 8) & 0xff;
    desc.bg_b = (bg >> 16) & 0xff;
    return desc;
}


}  // namespace spidisplay
