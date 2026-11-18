# Mighty FX Micropython Comms Examples <!-- omit in toc -->

These are micropython examples for controlling other boards from Mighty FX over I2C.

- [Examples](#examples)
  - [Dual Mighty FX](#dual-mighty-fx)
  - [Mighty and Tiny FX](#mighty-and-tiny-fx)


## Examples

### Dual Mighty FX
[dual_mighty_fx.py](dual_mighty_fx.py)

Play a rainbow wave across the RGB outputs of this Mighty FX and a second one connected by Qw/ST, which runs [i2c_target.py](../../../i2c_target.py). Disconnect or cut the cable's red power wire first.

### Mighty and Tiny FX
[mighty_and_tiny_fx.py](mighty_and_tiny_fx.py)

Play a rainbow wave across Mighty FX's RGB outputs and on to the RGB output of a Tiny FX connected by Qw/ST, with a pulse wave on its mono outputs. The Tiny FX runs [i2c_target.py](../../../../tiny_fx/i2c_target.py). Disconnect or cut the cable's red power wire first.
