# PicoFX<!-- omit in toc -->

## A RGB and Mono LED effects system for MicroPython <!-- omit in toc -->

This repository is home to the PicoFX library, as well as MicroPython builds for supported boards like the Pimoroni Tiny FX and Tiny FX W.

[![Build Status](https://img.shields.io/github/actions/workflow/status/pimoroni/picofx/micropython.yml?branch=main&label=MicroPython)](https://github.com/pimoroni/picofx/actions/workflows/micropython.yml)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/pimoroni/picofx)](https://github.com/pimoroni/picofx/releases/latest/)

- [Introduction](#introduction)
- [Get TinyFX](#get-tinyfx)
- [Programming TinyFX](#programming-tinyfx)
- [Download MicroPython for Tiny FX](#download-micropython-for-tiny-fx)
  - [Firmware Only](#firmware-only)
  - [With Libraries and Examples](#with-libraries-and-examples)
- [Flashing the Firmware](#flashing-the-firmware)
- [Examples](#examples)
- [Documentation](#documentation)


## Introduction

PicoFX is a MicroPython library for easily playing effects on mono and RGB leds.

Tiny FX is a programmable, RP2040-based controller board for adding smart light and sound effects to models and dioramas.

## Get TinyFX

* [Tiny FX](https://shop.pimoroni.com/products/tinyfx)
* [Tiny FX W](https://shop.pimoroni.com/products/tiny-fx-w) (with wireless connectivity)

## Programming TinyFX

All Tiny FX boards come pre-flashed with MicroPython and the libraries and examples needed to get you started.

To program Tiny FX you'll need to use an interpreter such as [Thonny](https://thonny.org/), which is available for Windows, Mac and Linux.

* Connect Tiny FX to your computer with a USB-C cable.
* Make sure you have 'MicroPython (Raspberry Pi Pico)' or 'MicroPython (RP2040)' selected as your interpreter in the bottom right of Thonny.
* You'll probably also want the 'Files' window open (View > Files), so you can browse the files on the device.
* Tiny FX runs a example by default so you'll need to press the stop button in Thonny to interrupt it before you can browse files or run code on the board.

If you're new to working with RP2040 boards, this Learn Guide goes into more detail about how to install and use Thonny.

* [Getting Started with Pico](https://learn.pimoroni.com/article/getting-started-with-pico)

## Download MicroPython for Tiny FX

If you wish to update your board to the latest firmware or restore it back to a factory state, you can grab the latest release from [https://github.com/pimoroni/picofx/releases/latest](https://github.com/pimoroni/picofx/releases/latest)

There are two .uf2 files to pick from:

### Firmware Only

* `tiny_fx-vX.X.X-pimoroni-micropython.uf2`
* `tiny_fx_w-vX.X.X-pimoroni-micropython.uf2`

This build includes only the firmware needed for Tiny FX to function. You will need to manually update the `lib/picofx` library afterwards to get the latest features and bug fixes.

### With Libraries and Examples

:warning: **This option will overwrite the entire contents of your Tiny FX! Be sure to back up files to your PC before installing!**

* `tiny_fx-vX.X.X-pimoroni-micropython-with-libs-and-examples.uf2`
* `tiny_fx_w-vX.X.X-pimoroni-micropython-with-libs-and-examples.uf2`

This build contains both the firmware for Tiny FX, library files to easily create effects, and examples to get you going.

## Flashing the Firmware

1. Connect Tiny FX to your computer using a USB C cable.

2. Put your board into bootloader mode by holding the BOOT button whilst tapping the RST button.

3. Drag and drop one of the .uf2 files to the "RPI-RP2" drive that appears.

4. After the copy completes your board should reset and, if you used the `with-libs-and-examples` variant, should start playing a wave sequence on the mono outputs, and a rainbow on the RGB output.

## Examples

There are many examples to get you started with TinyFX (and other boards), located in the examples folder of this repository:

* [Examples: Tiny FX](/examples/tiny_fx/README.md)
* [Examples: Plasma](/examples/plasma/README.md)


## Documentation

To take TinyFX further, the full API documentation for the board can be found at:

* [Library Reference](/docs/reference.md)