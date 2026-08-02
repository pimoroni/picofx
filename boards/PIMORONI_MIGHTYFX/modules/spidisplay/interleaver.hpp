// SPDX-License-Identifier: MIT
//
// The cross-port interleaver: drives several prepared displays through one
// frame each, overlapping their TE waits and time-slicing conversion between
// them so both wires stream at once. Header-only and templated on the display
// type, so the host harness runs the same loop against a mock with simulated
// wire and convert costs.
//
// The displays must be on different buses and already prepare()d. How far a
// display can convert ahead of its stream is its own buffering, band_capacity()
// deep, so staging depth is a display setting and not an interleaver one.

#pragma once

#include <cstdint>

namespace spidisplay {

// Arm every display so the TE waits overlap, then loop until each frame has
// drained. Each pass makes a latency-critical sweep first, edges and free
// channels, rotating the start index so ties do not always favour the same
// display; then at most one convert slice goes to the display with the nearest
// deadline, an idle channel counting as deadline zero. A pass that advances
// nothing calls idle_wait(), a no-op on hardware and the mock clock on the
// host. slice_rows bounds the latency a conversion can add to the sweep.
template <typename Display>
void interleave(Display *const *displays, int n, bool v_sync, uint32_t te_timeout_us,
                int slice_rows) {
    for (int i = 0; i < n; ++i) {
        displays[i]->arm(v_sync, te_timeout_us);
    }

    int rotate = 0;
    for (;;) {
        bool progressed = false;
        bool all_done = true;

        for (int k = 0; k < n; ++k) {
            Display *d = displays[(k + rotate) % n];
            if (d->done()) {
                continue;
            }
            all_done = false;
            if (d->poll_te()) {
                d->start_stream();
                progressed = true;
            } else {
                progressed |= d->step(0);
            }
        }
        if (all_done) {
            break;
        }
        rotate = (rotate + 1) % n;

        Display *pick = nullptr;
        uint32_t nearest = 0;
        for (int k = 0; k < n; ++k) {
            Display *d = displays[(k + rotate) % n];
            if (!d->wants_convert()) {
                continue;
            }
            uint32_t deadline = d->deadline_us();
            if (pick == nullptr || deadline < nearest) {
                pick = d;
                nearest = deadline;
            }
        }
        if (pick != nullptr) {
            progressed |= pick->step(slice_rows);
        }

        if (!progressed) {
            displays[0]->idle_wait();
        }
    }
}

}  // namespace spidisplay
