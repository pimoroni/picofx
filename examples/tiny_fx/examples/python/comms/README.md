# Tiny FX Micropython Comms Examples <!-- omit in toc -->

These are micropython examples for controlling other Tiny FX boards from this one over I2C.

- [Examples](#examples)
  - [Dual FX](#dual-fx)
  - [Multi FX](#multi-fx)


## Examples

### Dual FX
[dual_fx.py](dual_fx.py)

Play wave and rainbow animations across the outputs of this TinyFX and a second one connected by Qw/ST, which runs [i2c_target.py](../../../i2c_target.py). Disconnect or cut the cable's red power wire first.

### Multi FX
[multi_fx.py](multi_fx.py)

Play wave and rainbow animations across the outputs of this TinyFX and several more connected by Qw/ST cables and hubs, each running [i2c_target.py](../../../i2c_target.py) at its own address. Disconnect or cut the cables' red power wires first.
