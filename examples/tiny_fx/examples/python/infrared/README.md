# Tiny FX Micropython Infrared Examples <!-- omit in toc -->

These are micropython examples for controlling Tiny FX from a Pimoroni Aye Arr Remote, with an IR Stick connected to its sensor connector.

- [Mono Examples](#mono-examples)
  - [Control Channels](#control-channels)
  - [Control Pulse Wave](#control-pulse-wave)
  - [Toggle Effects](#toggle-effects)
- [Colour Examples](#colour-examples)
  - [Control RGB (Direct)](#control-rgb-direct)
  - [Control RGB (FX)](#control-rgb-fx)
  - [Control HSV (Direct)](#control-hsv-direct)
  - [Control HSV (FX)](#control-hsv-fx)
  - [Control Rainbow](#control-rainbow)


## Mono Examples

### Control Channels
[mono/control_channels.py](mono/control_channels.py)

Turn each of Tiny FX's mono outputs on and off by pressing the number buttons on the Pimoroni Aye Arr Remote, and hold to adjust their brightness.

### Control Pulse Wave
[mono/control_pulse_wave.py](mono/control_pulse_wave.py)

Play a wave of pulses on Tiny FX's outputs that is controllable by the directional buttons on a Pimoroni Aye Arr Remote.

### Toggle Effects
[mono/toggle_effects.py](mono/toggle_effects.py)

Play effects for each "postcard" on the Tales Of The Space Age set, and turn them on and off by pressing the number buttons on the Pimoroni Aye Arr Remote.


## Colour Examples

### Control RGB (Direct)
[colour/control_rgb_direct.py](colour/control_rgb_direct.py)

Set the colour of Tiny FX's onboard RGB LED using the number buttons on the Pimoroni Aye Arr Remote. This version interacts with the LED directly.

### Control RGB (FX)
[colour/control_rgb_fx.py](colour/control_rgb_fx.py)

Set the colour of Tiny FX's onboard RGB LED using the number buttons on the Pimoroni Aye Arr Remote. This version uses the effects system to interact with the LED.

### Control HSV (Direct)
[colour/control_hsv_direct.py](colour/control_hsv_direct.py)

Set the colour of Tiny FX's onboard RGB LED using the number buttons on the Pimoroni Aye Arr Remote, and change its hue, saturation, and value using the directional buttons. This version interacts with the LED directly.

### Control HSV (FX)
[colour/control_hsv_fx.py](colour/control_hsv_fx.py)

Set the colour of Tiny FX's onboard RGB LED using the number buttons on the Pimoroni Aye Arr Remote, and change its hue, saturation, and value using the directional buttons. This version uses the effects system to interact with the LED.

### Control Rainbow
[colour/control_rainbow.py](colour/control_rainbow.py)

Play a rainbow effect on Tiny FX's RGB output that is controllable by the directional buttons on a Pimoroni Aye Arr Remote.
