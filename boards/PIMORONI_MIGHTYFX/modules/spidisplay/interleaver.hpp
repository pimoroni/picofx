// SPDX-License-Identifier: MIT
//
// The cross-port interleaver: drives several prepared displays through one frame
// each, overlapping their TE waits and time-slicing conversion between them so
// every wire streams at once. Templated on the display type.
//
// The displays must be on different buses and already prepared. How far one can
// convert ahead of its stream is its own buffering, band_capacity() deep, so
// staging depth is a display setting and not an interleaver one.

#pragma once

#include <cstdint>

namespace spidisplay {

// The row budget that services a wire without converting.
static constexpr int NO_CONVERT_ROWS = 0;

// Arm every display so the TE waits overlap, then loop until every frame has
// drained. Each pass sweeps for latency first, then runs at most one convert
// slice of slice_rows. hysteresis_rows is the free ring rows another display must
// show before the burst leaves the one it is on; negative means half its ring.
template <typename Display>
void interleave(Display *const *displays, int count, bool v_sync,
                uint32_t te_timeout_us, int slice_rows, int hysteresis_rows) {
    for (int slot = 0; slot < count; ++slot) {
        displays[slot]->arm(v_sync, te_timeout_us);
    }

    int start_slot = 0;
    int sticky_slot = -1;
    for (;;) {
        bool progressed = false;
        bool all_done = true;

        // The latency-critical sweep: TE edges and freed channels, before any
        // conversion gets a look in.
        for (int offset = 0; offset < count; ++offset) {
            Display *display = displays[(offset + start_slot) % count];
            if (display->done()) {
                continue;
            }
            all_done = false;
            if (display->poll_te()) {
                display->start_stream();
                progressed = true;
            } else {
                progressed |= display->step(NO_CONVERT_ROWS);
            }
        }
        if (all_done) {
            break;
        }
        // Rotate the start so ties do not always favour the same display.
        start_slot = (start_slot + 1) % count;

        if (sticky_slot >= 0 && displays[sticky_slot]->convert_done()) {
            sticky_slot = -1;
        }

        // The pick is sticky, one display keeping the slice while its ring has room,
        // so its source reads stay coherent through the shared XIP cache:
        // alternating between a PSRAM rotation-90 pair evicts the reuse between one
        // display's consecutive cache-window fills. First of the two thresholds
        // bounding that burst, a display fallen to its low water of one slice plus
        // two bands takes the slice back before its wire starves.
        int chosen_slot = -1;
        int fewest_staged = 0;
        for (int offset = 0; offset < count; ++offset) {
            int slot = (offset + start_slot) % count;
            Display *display = displays[slot];
            if (!display->wants_convert()) {
                continue;
            }
            int staged = display->staged_rows();
            if (staged <= slice_rows + 2 * display->band_rows()
                    && (chosen_slot < 0 || staged < fewest_staged)) {
                chosen_slot = slot;
                fewest_staged = staged;
            }
        }
        if (chosen_slot < 0 && sticky_slot >= 0
                && displays[sticky_slot]->wants_convert()) {
            chosen_slot = sticky_slot;
        }
        // Nothing near starving, so the slice goes to the emptiest ring.
        if (chosen_slot < 0) {
            int most_free_rows = 0;
            for (int offset = 0; offset < count; ++offset) {
                int slot = (offset + start_slot) % count;
                Display *display = displays[slot];
                if (!display->wants_convert()) {
                    continue;
                }
                // Second threshold: a full ring hands the burst on only once the
                // candidate clears this, so one freed slot cannot bounce it
                // straight back. Negative selects half the ring.
                int clearance_rows = hysteresis_rows < 0
                                     ? display->stage_capacity_rows() / 2
                                     : hysteresis_rows;
                int free_rows = display->stage_free_rows();
                if ((sticky_slot < 0 || free_rows >= clearance_rows)
                        && (chosen_slot < 0 || free_rows > most_free_rows)) {
                    chosen_slot = slot;
                    most_free_rows = free_rows;
                }
            }
        }
        if (chosen_slot >= 0) {
            sticky_slot = chosen_slot;
            progressed |= displays[chosen_slot]->step(slice_rows);
        }

        // Nothing advanced this pass. idle_wait() is an empty hook on a real
        // display, so this costs nothing there.
        if (!progressed) {
            displays[0]->idle_wait();
        }
    }
}

}  // namespace spidisplay
