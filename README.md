# PicoFX - A RGB and Mono LED effects system for MicroPython <!-- omit in toc -->

This repository is home to the PicoFX library, as well as MicroPython builds for supported boards like the Pimoroni TinyFX.

[![Build Status](https://img.shields.io/github/actions/workflow/status/pimoroni/picofx/micropython.yml?branch=main&label=MicroPython)](https://github.com/pimoroni/picofx/actions/workflows/micropython.yml)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/pimoroni/picofx)](https://github.com/pimoroni/picofx/releases/latest/)

- [Introduction](#introduction)
- [Download MicroPython for TinyFX](#download-micropython-for-tinyfx)
  - [Firmware Only](#firmware-only)
  - [With Libraries and Examples](#with-libraries-and-examples)
- [Flashing the Firmware](#flashing-the-firmware)
- [TinyFX Examples](#tinyfx-examples)


## Introduction

PicoFX is a MicroPython library for easily playing effects on mono and RGB leds.

## Download MicroPython for TinyFX

All TinyFX boards come pre-flashed with MicroPython and the libraries and examples needed to get you started. The instructions below are for if you wish to update your board to the latest firmware or restore it back to a factory state.

Grab the latest release from [https://github.com/pimoroni/picofx/releases/latest](https://github.com/pimoroni/picofx/releases/latest)

There are two .uf2 files to pick from:

### Firmware Only

* `tinyfx-vX.X.X-pimoroni-micropython.uf2`

This build includes only the firmware needed for TinyFX to function. You will need to manually update the `lib/picofx` library afterwards to get the latest features and bug fixes.


### With Libraries and Examples

:warning: **This option will overwrite the entire contents of your TinyFX! Be sure to back up files to your PC before installing!**

* `tinyfx-vX.X.X-pimoroni-micropython-with-libs-and-examples.uf2 `

This build contains both the firmware for TinyFX, library files to easily create effects, and examples to get you going.

## Flashing the Firmware

1. Connect TinyFX to your computer using a USB A to C cable.

2. Put your board into bootloader mode by holding the BOOT button whilst tapping the RST button.

3. Drag and drop one of the `tinyfx-vX.X.X...` .uf2 files to the "RPI-RP2" drive that appears.

5. After the copy completes your board should reset and, if you used the `with-libs-and-examples` variant, should start playing a wave sequence on the mono outputs, and a rainbow on the RGB output.


## TinyFX Examples

There are many examples to get you started with TinyFX, located in the examples folder of this repository:

* [Examples](/examples/tiny_fx/README.md)
