# Mighty FX Micropython Infrared Examples <!-- omit in toc -->

These are micropython examples for controlling Mighty FX from a Pimoroni Aye Arr Remote, with an IR Stick connected to its sensor connector.

- [Colour Examples](#colour-examples)
  - [Control RGB Direct](#control-rgb-direct)
  - [Control RGB FX](#control-rgb-fx)
  - [Control HSV Direct](#control-hsv-direct)
  - [Control HSV FX](#control-hsv-fx)
  - [Control Rainbow](#control-rainbow)
  - [Control Rainbow Wave](#control-rainbow-wave)
- [Mono Examples](#mono-examples)
  - [Control Channels](#control-channels)
  - [Control Pulse Wave](#control-pulse-wave)
  - [Toggle Effects](#toggle-effects)


## Colour Examples

### Control RGB Direct
[colour/control_rgb_direct.py](colour/control_rgb_direct.py)

Set the colour of MightyFX's seven RGB outputs using the number buttons on the Pimoroni Aye Arr Remote. This version interacts with the outputs directly.

### Control RGB FX
[colour/control_rgb_fx.py](colour/control_rgb_fx.py)

Set the colour of MightyFX's seven RGB outputs using the number buttons on the Pimoroni Aye Arr Remote. This version uses the effects system to interact with them. One effect drives every output, so they change together.

### Control HSV Direct
[colour/control_hsv_direct.py](colour/control_hsv_direct.py)

Set the colour of MightyFX's seven RGB outputs using the number buttons on the Pimoroni Aye Arr Remote, and change their hue, saturation, and value using the directional buttons. This version interacts with the outputs directly.

### Control HSV FX
[colour/control_hsv_fx.py](colour/control_hsv_fx.py)

Set the colour of MightyFX's seven RGB outputs using the number buttons on the Pimoroni Aye Arr Remote, and change their hue, saturation, and value using the directional buttons. This version uses the effects system to interact with them. One effect drives every output, so they change together.

### Control Rainbow
[colour/control_rainbow.py](colour/control_rainbow.py)

Play a rainbow effect on MightyFX's RGB outputs that is controllable by the directional buttons on a Pimoroni Aye Arr Remote. One effect drives every output, so the whole board cycles together.

### Control Rainbow Wave
[colour/control_rainbow_wave.py](colour/control_rainbow_wave.py)

Play a rainbow that travels along MightyFX's outputs, controllable by the directional buttons on a Pimoroni Aye Arr Remote.


## Mono Examples

These play mono effects, which give a brightness rather than a colour, so each output draws its effect in the colour it was given.

### Control Channels
[mono/control_channels.py](mono/control_channels.py)

Turn each of MightyFX's outputs on and off by pressing the number buttons on the Pimoroni Aye Arr Remote, and hold to adjust their brightness.

### Control Pulse Wave
[mono/control_pulse_wave.py](mono/control_pulse_wave.py)

Play a wave of pulses on MightyFX's outputs that is controllable by the directional buttons on a Pimoroni Aye Arr Remote.

### Toggle Effects
[mono/toggle_effects.py](mono/toggle_effects.py)

Play a different effect on each of MightyFX's outputs, and turn them on and off by pressing the number buttons on the Pimoroni Aye Arr Remote.
