# Mighty FX Micropython Comms Examples <!-- omit in toc -->

These are micropython examples for controlling other boards from Mighty FX over I2C.

- [Examples](#examples)
  - [Dual Mighty FX](#dual-mighty-fx)
  - [Mighty and Tiny FX](#mighty-and-tiny-fx)


## Examples

### Dual Mighty FX
[dual_mighty_fx.py](dual_mighty_fx.py)

Play a rainbow wave across the RGB outputs of this MightyFX and of a second MightyFX connected by I2C and running as an I2CTarget.

### Mighty and Tiny FX
[mighty_and_tiny_fx.py](mighty_and_tiny_fx.py)

Play a rainbow wave across MightyFX's RGB outputs and on to the RGB output of a TinyFX connected by I2C and running as an I2CTarget, with a pulse wave on the TinyFX's mono outputs.
