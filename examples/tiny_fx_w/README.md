# Tiny FX W Micropython Examples <!-- omit in toc -->

These are micropython examples for the wireless functionality of the Pimoroni [Tiny FX W](https://shop.pimoroni.com/products/tiny-fx-w), a stamp-sized light and sound effects controller board for model making, construction kits, and dioramas.

For examples that show off the rest of the board's functions, refer to the regular [Tiny FX Micropython Examples](../tiny_fx/README.md).

- [Wireless Examples](#wireless-examples)
  - [Random](#random)
  - [CheerLights](#cheerlights)


## Wireless Examples

These examples require a `secrets.py` file on your board's file system with the credentials of your WiFi network.

### Random
[wireless/random.py](examples/programs/wireless/random.py)

Show random colours and patterns obtained from the internet on Tiny FX W's outputs.


### CheerLights
[wireless/cheerlights.py](examples/programs/wireless/cheerlights.py)

Obtain the current CheerLights colour from the internet and show it on Tiny FX W's RGB output. For more information about CheerLights, visit: https://cheerlights.com/
