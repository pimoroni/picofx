# PicoFX-compatible Boards

The MicroPython builds for each board, made by CI from the folders here.

## Pimoroni Tiny FX

A tiny stamp-sized LED driver for model making and construction kit projects. Built from `PIMORONI_TINYFX`:

* The standard build: MicroPython with the PicoFX library and examples. Tiny FX ships with this build.
* The `w` variant: the same for Tiny FX W, adding WiFi and Bluetooth.

## Pimoroni Mighty FX

A programmable, RP2350-based controller board that goes further with effects by adding motion and screens. Built from `PIMORONI_MIGHTYFX`:

* The standard build: MicroPython with the PicoFX library and examples, for writing your own programs.

## Shared Between the Boards

* `visible_libs`: libraries copied to each board's `/lib`, beside the board's own.
* `frozen_libs`: modules frozen into every build.
