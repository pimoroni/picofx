# spidisplay

A panel-agnostic SPI and DMA transport for SP/CE screens. One `SPIDisplayBus` per SPI port owns the
peripheral, its DMA channel and its rate. Each `SPIDisplay` on a bus owns one panel's chip select
and data/command lines and streams a converted frame to it band by band, so conversion of the next
band overlaps the DMA of the last. Bringup stays in MicroPython, in `st7789.py`, which also holds
the tables a panel is tuned from: the porch, the rows a refresh scans and the rate and pixel-format
codes. Nothing here knows where the pixel format came from: `bitdepth` at construction selects the
packer, and `st7789.py` sends the panel the matching COLMOD.

This file holds what a maintainer would otherwise re-derive from the code. The Python surface is
documented for customers in `docs/screens.md`.

## Files

| file | holds |
| --- | --- |
| `spidisplay.hpp`, `spidisplay.cpp` | the bus, the display, the frame state machine and the MicroPython bindings for both types |
| `spidisplay_bindings.c` | the module table, `buffer()`, `buffer_size()`, `release_buffers()` and `dual_convert()` |
| `scanline.hpp` | the conversion kernels: RGBA8888 or palettised source to RGB444 or RGB565 rows, with rotation, mirror, pixel doubling and tiling |
| `column_cache.hpp` | a cache of source columns for rotated frames, so a rotation-90 row does not read one pixel per PSRAM line |
| `interleaver.hpp` | `update_all()`, driving several displays on different buses through a frame at once |
| `sram_allocator.hpp` | the region of fast SRAM the GC heap does not use, claimed from the top by displays and from the bottom by canvases |

## The frame

`update()` composes four resumable steps, which `update_all()` drives for several displays at once:

1. `prepare()` builds the conversion descriptor, seeds the column cache and converts as far ahead
   as the band ring allows. It sets the bus rate and DMA word width, sends nothing and never
   waits on the bus.
2. `arm()` begins the tearing-effect wait without blocking: the TE line goes to input, the stale
   level is recorded and the timeout starts. `poll_te()` samples the rising-then-falling wait and
   returns true once the frame may start, by edge or by timeout. `step()` may convert ahead
   meanwhile.
3. `start_stream()` sends RAMWR and kicks the first band, timestamped as `write_start_us`.
4. `step()` converts at most a slice of rows into the back band, kicks it when full and the
   channel is free, and raises CS once everything has drained.

Only displays on different buses interleave; displays sharing a bus are driven as a broadcast
group instead, one display carrying every member's CS and DC bits.

### The band ring

The band buffers form a ring of `ceil(stage_lines / band_lines)` slots, at least two. A height that
`band_lines` does not divide ends in a shorter final band, sized where it is converted and kicked. Conversion
may run the whole ring ahead of the wire, which is what lets a slow source convert during the TE
wait and hold a head start against the wire's pace. One slot always stays reserved for the transfer
in flight, whether or not the channel reports busy: reclaiming it on the live busy flag lets a
whole-band conversion slip in at the moment a transfer completes, ahead of the waiting kick, and
the wire starves for that conversion. Measured at 82us per band on an SRAM source, up to a full
band's convert on PSRAM.

Kicks are interrupt driven, from the DMA_IRQ_2 handler. `kick_from_isr()` runs in ISR context,
is gated by the channel owner table and touches no state, stats or MicroPython; it kicks the next
converted band or timestamps the wire starving. `stall_us` in `FrameStats` is therefore the wire
genuinely starving for conversion: near zero means the frame was wire-bound, growth means the
conversion could not keep the ring fed. `stall_row` is where that first happened, the row the wire
was waiting for, and -1 for a frame that never starved; the drain at the end of every frame counts
toward `stall_us` but never sets it. It is always a band boundary, so a starving band and a panel
tearing at a fixed row look alike until it is read: a tear with `stall_row` at -1 is not a
starvation, and the panel's scan direction not following MADCTL, noted under compatibility below,
is the likelier cause.

### The SRAM claim

Each display claims its band ring, its column cache storage and the palette an indexed source is
drawn through as one block from the top of the SRAM region, at construction. The palette is per
display because interleaving drives several through frames concurrently, and in SRAM because a
per-pixel indirection into PSRAM would reintroduce the XIP miss the column cache exists to remove.
A broadcast copy shares its first member's claim and releases nothing, so the wrapper roots the
member for the group's lifetime.

`buffer()` claims canvases from the bottom of the same region. The views have no owner to
finalise them, so `release_buffers()` belongs with releasing the screens that drew to them.

## The tearing-effect wait

`te < 0` at construction reads the signal from the DC line, which is how the MightyFX wires a
single panel: the DC line is flipped to an input for the wait. Otherwise `te` is a dedicated input
GPIO.

**Wiring.** `cs` must be unique per panel, being the only signal selecting one. `dc` may be shared,
but not by panels using TE without a diode: each breakout ties TE to that line through a series
resistor, so panels sharing it divide the line and the asserted level is lost. Behind a
multiplexer a DC line carrying TE needs an analog mux to pass both directions; a demux or buffer
fails quietly, the wait timing out, `te_timeouts()` counting it, while the frame still streams.

**The transient discipline.** A shared line may carry one panel's signal at a time. A non-zero
`sync_cs` on `prepare()` names the member whose TE the frame waits on, and the display sends that
member TEON as the wait begins and TEOFF as the frame goes idle. The sync and target masks belong
to the frame and clear with it, so no TEON outlives the frame that asked for it and no narrowed
write leaves a mask behind for the next one.

**The counters.** Three cumulative counts say how the waits went, none of which is part of the
frame snapshot:

- `te_timeouts()`: frames that began without their TE edge. A frame still goes out, so this is the
  only sign `v_sync` did not hold.
- `te_short_waits()`: frames whose wait ended on a pulse it watched rise and that fell inside
  `SHORT_WAIT_US`, 700us, which is above TE mode 2's 500us H-sync pulses and below the shortest
  measured blanking, 1,277us on the 1.54" and 1,536us on the 2.8". A pulse train defeats it: TE
  mode 2 rises within 17us of the release, inside `JOINED_HIGH_US`, so those waits book as joined
  and `te_probe()`'s period is what names that fault.
- `te_joined_waits()`: frames whose wait began with the line already high, so the pulse it ended
  on started unobserved. One a frame means a line released from a high and decaying through the
  pull-down. The occasional one is a held frame arming inside a blanking, which reaches a real fall
  late and is no fault.

`JOINED_HIGH_US` is 50us: over the 14us an arm and its two settled samples cost, far under the
thousands an arm during the active scan waits for a blanking.

**Phase measurement.** `te_phase()` captures falling edges on two displays' lines from one loop and
folds them onto a period, so a pair's skew is measured without writing a frame; it copes with the
roughly 47us TESCAN-narrowed pulse, which a Python capture cannot. `te_capture()` keeps one line's
raw edges instead, which is what a shared DC line needs: a hub is swept member by member and each
fall aged by that panel's period onto a common instant. Neither may run while a frame is staged or
streaming, a staged frame owning the DC line TE is read from.

## Rates

`baudrate` is per panel and asserted against the bus before every transfer, so mixed panel types
can share a port. The divider only reaches `clk_peri / (2 * n)`, so a request is rounded down,
sometimes a long way; `baudrate()` reports what was reached and the Python wrapper refuses a
request the clock cannot meet.

`sync_delay_us` on `update()` starts the stream that long after the TE wait releases, which places
a broadcast write inside every member's tearing margin instead of at the synced member's own top
edge. `write_start_us` moves with it.

`compatible_with()` requires the same bus and agreement on everything the stream depends on.
Register state bringup put in the panel is not compared, MADCTL included, which is not licence to
vary it: the scan direction does not follow MADCTL, so a flipped panel tears.
