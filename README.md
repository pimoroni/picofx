# PicoFX<!-- omit in toc -->

## A RGB and Mono LED effects system for MicroPython <!-- omit in toc -->

This repository is home to the PicoFX library, as well as MicroPython builds for supported boards like the Pimoroni Mighty FX and Tiny FX (W).

[![Build Status](https://img.shields.io/github/actions/workflow/status/pimoroni/picofx/micropython.yml?branch=main&label=MicroPython)](https://github.com/pimoroni/picofx/actions/workflows/micropython.yml)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/pimoroni/picofx)](https://github.com/pimoroni/picofx/releases/latest/)

- [Introduction](#introduction)
- [Get Mighty and Tiny FX](#get-mighty-and-tiny-fx)
- [Programming Mighty and Tiny FX](#programming-mighty-and-tiny-fx)
- [Download MicroPython for Mighty and Tiny FX](#download-micropython-for-mighty-and-tiny-fx)
  - [Firmware Only](#firmware-only)
  - [With Libraries and Examples](#with-libraries-and-examples)
- [Flashing the Firmware](#flashing-the-firmware)
- [Examples](#examples)
- [Documentation](#documentation)


## Introduction

PicoFX is a MicroPython library for easily playing effects on mono and RGB leds.

Tiny FX is a programmable, RP2040-based controller board for adding smart light and sound effects to models and dioramas.

Mighty FX is a programmable, RP2350-based controller board that goes further with effects by adding motion and screens.

## Get Mighty and Tiny FX

* [Mighty FX](https://shop.pimoroni.com/products/mightyfx)

* [Tiny FX](https://shop.pimoroni.com/products/tinyfx)
* [Tiny FX W](https://shop.pimoroni.com/products/tiny-fx-w) (with wireless connectivity)

## Programming Mighty and Tiny FX

All Mighty and Tiny FX boards come pre-flashed with MicroPython and the libraries and examples needed to get you started.

To program Mighty and Tiny FX you'll need to use an interpreter such as [Thonny](https://thonny.org/), which is available for Windows, Mac and Linux.

* Connect Mighty or Tiny FX to your computer with a USB-C cable.
* Make sure you have 'MicroPython (Raspberry Pi Pico)' or 'MicroPython (RP2040)' selected as your interpreter in the bottom right of Thonny.
* You'll probably also want the 'Files' window open (View > Files), so you can browse the files on the device.
* Mighty and Tiny FX run an example by default so you'll need to press the stop button in Thonny to interrupt it before you can browse files or run code on the board.

If you're new to working with RP2040 boards, this Learn Guide goes into more detail about how to install and use Thonny.

* [Getting Started with Pico](https://learn.pimoroni.com/article/getting-started-with-pico)

## Download MicroPython for Mighty and Tiny FX

If you wish to update your board to the latest firmware or restore it back to a factory state, you can grab the latest release from [https://github.com/pimoroni/picofx/releases/latest](https://github.com/pimoroni/picofx/releases/latest)

There are two types of .uf2 file to pick from:

### Firmware Only

* `mighty_fx-vX.X.X-micropython.uf2`
* `tiny_fx-vX.X.X-micropython.uf2`
* `tiny_fx_w-vX.X.X-micropython.uf2`

This build type includes only the firmware needed for Mighty and Tiny FX to function. You will need to manually update the `lib/picofx` library afterwards to get the latest features and bug fixes.

### With Libraries and Examples

:warning: **This option will overwrite the entire contents of your Mighty and Tiny FX! Be sure to back up files to your PC before installing!**

* `mighty_fx-vX.X.X-micropython-with-libs-and-examples.uf2`
* `tiny_fx-vX.X.X-micropython-with-libs-and-examples.uf2`
* `tiny_fx_w-vX.X.X-micropython-with-libs-and-examples.uf2`

This build type contains both the firmware for Mighty and Tiny FX, library files to easily create effects, and examples to get you going.

## Flashing the Firmware

1. Connect Mighty or Tiny FX to your computer using a USB C cable.

2. Put your board into bootloader mode by holding the BOOT button whilst tapping the RST button.

3. Drag and drop one of the .uf2 files to the "RP2350" or "RPI-RP2" drive that appears.

4. After the copy completes your board should reset and, if you used the `with-libs-and-examples` variant, should start playing a light sequence on the board's RGB and mono outputs.

## Examples

There are many examples to get you started with Mighty and Tiny FX (and other boards), located in the examples folder of this repository:

* [Examples: Mighty FX](/examples/mighty_fx/README.md)
* [Examples: Tiny FX](/examples/tiny_fx/README.md)
* [Examples: Tiny FX W](/examples/tiny_fx_w/README.md)
* [Examples: Plasma](/examples/plasma/README.md)


## Documentation

To take Mighty and Tiny FX further, the full API documentation for the boards can be found at:

* [Library Reference](/docs/reference.md)