# TinyFX W Micropython Examples <!-- omit in toc -->

These are micropython examples for the wireless functionality of the Pimoroni [TinyFX W](https://shop.pimoroni.com/products/tiny_fx_w), a stamp-sized light and sound effects controller board for model making, construction kits, and dioramas.

For examples that show off the rest of the board's functions, refer to the regular [TinyFX Micropython Examples](../tiny_fx/README.md)

- [Wireless Examples](#wireless-examples)
  - [Random](#random)
  - [CheerLights](#cheerlights)


## Wireless Examples

These examples requires a `secrets.py` file to be on your board's file system with the credentials of your WiFi network.

### Random
[wireless/random.py](examples/wireless/random.py)

Show the state of TinyFX's Boot button on its RGB output.
Show random colours and patterns obtained from the internet on TinyFX's outputs.


### CheerLights
[wireless/cheerlights.py](examples/wireless/cheerlights.py)

Obtain the current CheerLights colour from the internet and show it on TinyFX's RGB output.
For more information about CheerLights, visit: [https://cheerlights.com/](https://cheerlights.com/)
