# Reference implementations

Code kept for reference rather than for the board. Nothing here is copied to the
device by `uf2-copyfiles.sh` or the filesystem workflow, and nothing in
`visible_libs/` imports it, so it costs no flash and cannot affect a build.

MightyFX drives its panels through the `spidisplay` C module, which converts in
C++ and overlaps conversion with DMA. These drivers convert in pure MicroPython
with `@micropython.viper`, and are kept for two reasons:

- They are a worked example of `@micropython.viper`, including the plain-Python
  form each kernel replaced and the timings that justified the rewrite.
- They are the starting point for a board with an ST7789 panel and no
  `spidisplay` module built in. They depend on nothing outside the standard
  MicroPython library: `machine.SPI`, three GPIOs, and a source object exposing
  the buffer protocol plus `width` and `height`.

## The shared module

`st7789_viper_common.py` holds the register map and `setup()`, the bringup sequence. The
two drivers differ only in how they convert pixels, so a panel is brought up
identically for both and that is described once.

`setup(display, colmod, framerate)` takes either driver, using its `command()`
method plus `width` and `height`. It validates the frame rate, so a driver imports
three names and nothing else:

```python
from st7789_viper_common import COLMOD_RGB444, REG_RAMWR, setup
```

The registers use `micropython.const()`, which is worthwhile because `setup()` is
in the same module and the compiler inlines each address at its point of use. The
three names a driver imports become ordinary globals on the far side of the import,
which costs one lookup per frame at most.

Registers are in address order, with each register's parameter values beneath it:
the MADCTL bits under `REG_MADCTL`, the COLMOD formats under `REG_COLMOD`, and the
frame rate table under `REG_FRCTRL2`.

## The two drivers

| | `st7789_viper_rgb444.py` | `st7789_viper_rgb565.py` |
| --- | --- | --- |
| colour | 12-bit, two pixels per three bytes | 16-bit, one pixel per two bytes |
| rotation | 0, 90, 180, 270 | 0, 180 |
| mirror | yes | yes |
| pixel doubling | yes | no |
| source smaller than the panel | yes, centred or placed | no, sizes must match |
| background fill | yes | no |
| odd source width | yes | no |
| kernels | 8 | 4 |

**Start from the RGB444 driver.** It is the complete one, and it is what MightyFX
shipped. The RGB565 kernels are the earlier, narrower set, kept because they are
the clearest reading of the technique: one packing expression, no placement
arithmetic. Read those first if you want to understand the approach, then the
RGB444 set to see what handling every case costs.

Bringing the RGB565 set up to parity is not planned. The C module already does
16-bit properly, so the effort would buy nothing.

Both share the same limit: conversion and transfer are strictly sequential, so a
frame costs convert plus transfer. The C module overlaps them and is roughly twice
as fast for the same panel.

## The examples

`color_wheel_rgb444.py` and `color_wheel_rgb565.py` are the same effect as
`examples/mighty_fx/examples/screens/color_wheel.py`, built on these drivers
instead of `MightyFX`. They construct the SPI peripheral and pins directly, so
they show everything a driver needs and nothing else.

Each cycles every mode its driver supports, sixteen for RGB444 and four for
RGB565, holding each for `MODE_FRAMES` frames and printing it:

```
mode 6/16: rotation=90, mirror=True, pixel_double=False
```

Both draw the wheel over four off-black quadrants, because the wheel on its own is
symmetrical enough that a flip is hard to spot, whereas the quadrant tints move
somewhere different under every operation. The RGB444 example also sets a brighter
background through the driver, so the area a rotated or doubled canvas does not
cover reads as outside the image.

To run one, copy it, its driver and `st7789_viper_common.py` into `lib/` on the device
and import it. Both default to MightyFX SP/CE port A driving a 240x320 panel; the
pin block at the top of each is the only thing to change for another board.

## Notes for reuse

`update()` takes the background as a packed `0xAABBGGRR` integer rather than a
picovector colour, which is what keeps the dependency list empty. From picovector,
pass a colour's `.p` attribute.

Tearing effect is read on the DC line, as MightyFX wires it. A panel with a
dedicated TE pin needs `v_sync` changing to poll that pin instead.
