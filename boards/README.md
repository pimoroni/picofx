# PicoFX-compatible Boards

The MicroPython builds for each board, made by CI from the folders here.

## Pimoroni TinyFX

A tiny stamp-sized LED driver for model making and construction kit projects. Built from `PIMORONI_TINYFX`:

* The standard build: MicroPython with the PicoFX library and examples. Tiny FX ships with this build.
* The `w` variant: the same for Tiny FX W, adding WiFi and Bluetooth.
* The `drive` variant: adds the FX drive, which plays `effects.txt` with no code needed and carries the picker, editor and manual.
* The `w_drive` variant: the FX drive on Tiny FX W.

## Pimoroni MightyFX

A programmable, RP2350-based controller board that goes further with effects by adding motion and screens. Built from `PIMORONI_MIGHTYFX`:

* The standard build: MicroPython with the PicoFX library and examples, for writing your own programs.
* The `drive` variant: adds the FX drive, as on Tiny FX. MightyFX ships with this build.

## Pimoroni Plasma 2350

`PIMORONI_PLASMA2350` holds the picker page for Plasma 2350's FX drive. Its standard firmware comes from the [plasma repository](https://github.com/pimoroni/plasma).

## Shared Between the Boards

* `fx_libs`: the FX drive, frozen into each `drive` variant beside the board's own pages, manual and defaults.
* `visible_libs`: libraries copied to each board's `/lib`, beside the board's own, and the effects player that reads `effects.txt`, which only the `drive` variants carry, frozen in.
* `frozen_libs`: modules frozen into every build.
* `editor`: the picker and editor pages, assembled for each board by `tools/build_editor.py`.
* `manual`: the parts of the FX drive's manual, assembled for each board by `tools/build_manual.py`.
