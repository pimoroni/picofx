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
// display; then at most one convert slice runs. A pass that advances nothing
// calls idle_wait(), a no-op on hardware and the mock clock on the host.
// slice_rows bounds the latency a conversion can add to the sweep.
//
// The convert pick is sticky: the current display keeps the slice while its
// ring has room, so its source reads stay coherent through the shared XIP
// cache, where alternating slices between a PSRAM rotation-90 pair evicts the
// reuse between one display's consecutive cache-window fills. Two thresholds
// bound the burst: a streaming display fallen to its low water, one slice
// plus two bands staged, preempts it before that wire can starve; and a full
// ring hands the burst only to a display whose free room clears
// hysteresis_rows (negative selects half that display's ring), so one freed
// slot cannot bounce it straight back.
template <typename Display>
void interleave(Display *const *displays, int n, bool v_sync, uint32_t te_timeout_us,
                int slice_rows, int hysteresis_rows) {
    for (int i = 0; i < n; ++i) {
        displays[i]->arm(v_sync, te_timeout_us);
    }

    int rotate = 0;
    int sticky = -1;
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

        if (sticky >= 0 && displays[sticky]->convert_done()) {
            sticky = -1;
        }

        int pick = -1;
        int lowest = 0;
        for (int k = 0; k < n; ++k) {
            int idx = (k + rotate) % n;
            Display *d = displays[idx];
            if (!d->wants_convert()) {
                continue;
            }
            int staged = d->staged_rows();
            if (staged <= slice_rows + 2 * d->band_rows()
                    && (pick < 0 || staged < lowest)) {
                pick = idx;
                lowest = staged;
            }
        }
        if (pick < 0 && sticky >= 0 && displays[sticky]->wants_convert()) {
            pick = sticky;
        }
        if (pick < 0) {
            int most_free = 0;
            for (int k = 0; k < n; ++k) {
                int idx = (k + rotate) % n;
                Display *d = displays[idx];
                if (!d->wants_convert()) {
                    continue;
                }
                int clear = hysteresis_rows < 0 ? d->stage_capacity_rows() / 2
                                                : hysteresis_rows;
                int free_rows = d->stage_free_rows();
                if ((sticky < 0 || free_rows >= clear)
                        && (pick < 0 || free_rows > most_free)) {
                    pick = idx;
                    most_free = free_rows;
                }
            }
        }
        if (pick >= 0) {
            sticky = pick;
            progressed |= displays[pick]->step(slice_rows);
        }

        if (!progressed) {
            displays[0]->idle_wait();
        }
    }
}

}  // namespace spidisplay
