# Mighty FX Micropython Effect Examples <!-- omit in toc -->

These are micropython examples for the effects Mighty FX can play on its seven RGB outputs, either as whole colours or as separate mono channels.

- [Mono Effect Examples](#mono-effect-examples)
  - [Static Brightness](#static-brightness)
  - [Single Blink](#single-blink)
  - [Single Flashing](#single-flashing)
  - [Single Flicker](#single-flicker)
  - [Single Pulse](#single-pulse)
  - [Single Random](#single-random)
  - [Random](#random)
  - [Blink Wave](#blink-wave)
  - [Flashing Sequence](#flashing-sequence)
  - [Pulse Wave](#pulse-wave)
  - [Sweep](#sweep)
  - [Binary Counter](#binary-counter)
  - [Traffic Light](#traffic-light)
- [Colour Effect Examples](#colour-effect-examples)
  - [Static RGB](#static-rgb)
  - [Static HSV](#static-hsv)
  - [Blink](#blink)
  - [Rainbow](#rainbow)
  - [Rainbow Wave](#rainbow-wave)
  - [Hue Step](#hue-step)
  - [Sweep Trail](#sweep-trail)
  - [Traffic Light](#traffic-light-1)
  - [Pelican Crossing](#pelican-crossing)


## Mono Effect Examples

These treat the red, green and blue of each output as a separate mono channel, 21 in all.

### Static Brightness
[mono/static_brightness.py](mono/static_brightness.py)

Show a static brightness on a single colour of a MightyFX output.


### Single Blink
[mono/single_blink.py](mono/single_blink.py)

Play a blinking effect on a single colour of a MightyFX output.


### Single Flashing
[mono/single_flashing.py](mono/single_flashing.py)

Play a flashing effect on a single colour of a MightyFX output.


### Single Flicker
[mono/single_flicker.py](mono/single_flicker.py)

Play a flickering effect on a single colour of a MightyFX output.


### Single Pulse
[mono/single_pulse.py](mono/single_pulse.py)

Play a pulsing effect on a single colour of a MightyFX output.


### Single Random
[mono/single_random.py](mono/single_random.py)

Play a randomly changing brightness effect on a single colour of a MightyFX output.


### Random
[mono/random.py](mono/random.py)

Play a randomly changing brightness on every colour of MightyFX's outputs.


### Blink Wave
[mono/blink_wave.py](mono/blink_wave.py)

Play a wave of blinks across every colour of MightyFX's outputs.


### Flashing Sequence
[mono/flashing_sequence.py](mono/flashing_sequence.py)

Play a flashing sequence across every colour of MightyFX's outputs.


### Pulse Wave
[mono/pulse_wave.py](mono/pulse_wave.py)

Play a wave of pulses across every colour of MightyFX's outputs.


### Sweep
[mono/sweep.py](mono/sweep.py)

Sweep a light back and forth across every colour of MightyFX's outputs.


### Binary Counter
[mono/binary_counter.py](mono/binary_counter.py)

Play an incrementing binary counter across every colour of MightyFX's outputs.


### Traffic Light
[mono/traffic_light.py](mono/traffic_light.py)

Play a traffic light sequence on three of MightyFX's colours.


## Colour Effect Examples

These play on each of MightyFX's outputs as a whole colour.

### Static RGB
[colour/static_rgb.py](colour/static_rgb.py)

Show a static colour on all of MightyFX's RGB outputs.


### Static HSV
[colour/static_hsv.py](colour/static_hsv.py)

Show a static colour on all of MightyFX's RGB outputs, using HSV.


### Blink
[colour/blink.py](colour/blink.py)

Chase a blink around MightyFX's seven RGB outputs, each blink a different colour in turn.


### Rainbow
[colour/rainbow.py](colour/rainbow.py)

Play a rainbow effect on all of MightyFX's RGB outputs.


### Rainbow Wave
[colour/rainbow_wave.py](colour/rainbow_wave.py)

Play a rainbow wave animation on MightyFX's RGB outputs.


### Hue Step
[colour/hue_step.py](colour/hue_step.py)

Step MightyFX's seven RGB outputs around the colour wheel together, each one holding its own place in it.


### Sweep Trail
[colour/sweep_trail.py](colour/sweep_trail.py)

Sweep a red light back and forth across MightyFX's outputs, leaving a trail behind it, which is the scanner a certain talking car wears across its nose.


### Traffic Light
[colour/traffic_light.py](colour/traffic_light.py)

Play a traffic light sequence on three of MightyFX's RGB outputs.


### Pelican Crossing
[colour/pelican_crossing.py](colour/pelican_crossing.py)

Play a pelican crossing on five of MightyFX's RGB outputs.
