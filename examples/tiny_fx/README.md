# TinyFX Micropython Examples <!-- omit in toc -->

These are micropython examples for the Pimoroni [TinyFX](https://shop.pimoroni.com/products/tiny_fx), a stamp-sized light and sound effects controller board for model making, construction kits, and dioramas.

- [Function Examples](#function-examples)
- [Mono Effect Examples](#mono-effect-examples)
  - [Single Blink](#single-blink)
  - [Single Flashing](#single-flashing)
  - [Single Flicker](#single-flicker)
  - [Single Pulse](#single-pulse)
  - [Single Random](#single-random)
  - [Blink Wave](#blink-wave)
  - [Flashing Sequence](#flashing-sequence)
  - [Pulse Wave](#pulse-wave)
  - [Binary Counter](#binary-counter)
  - [Traffic Light](#traffic-light)
- [Colour Effect Examples](#colour-effect-examples)
  - [Rainbow](#rainbow)
  - [Random](#random)
  - [Hue Step](#hue-step)
- [Audio Examples](#audio-examples)
  - [Read Button](#read-button)
  - [Sensor Meter](#sensor-meter)
  - [Voltage Meter](#voltage-meter)
- [Showcase Examples](#showcase-examples)
  - [Rescue Vehicle](#rescue-vehicle)
  - [Sensor Wave](#sensor-wave)
  - [Ship Thrusters](#ship-thrusters)
  - [Space Tales](#space-tales)
  - [Space Tales with PIR Sensor](#space-tales-with-pir-sensor)


## Function Examples



## Mono Effect Examples

### Single Blink
[effects/mono/single_blink.py](effects/mono/single_blink.py)

Play a blinking effect on one of TinyFX's outputs.


### Single Flashing
[effects/mono/single_flashing.py](effects/mono/single_flashing.py)

Play a flashing effect on one of TinyFX's outputs.


### Single Flicker
[effects/mono/single_flicker.py](effects/mono/single_flicker.py)

Play a flickering effect on one of TinyFX's outputs.


### Single Pulse
[effects/mono/single_pulse.py](effects/mono/single_pulse.py)

Play a pulsing effect on one of TinyFX's outputs.


### Single Random
[effects/mono/single_random.py](effects/mono/single_random.py)

Play a randomly changing brightness effect on one of TinyFX's outputs.


### Blink Wave
[effects/mono/blink_wave.py](effects/mono/blink_wave.py)

Play a wave of blinks on TinyFX's outputs.


### Flashing Sequence
[effects/mono/flashing_sequence.py](effects/mono/flashing_sequence.py)

Play a flashing sequence across TinyFX's outputs.


### Pulse Wave
[effects/mono/pulse_wave.py](effects/mono/pulse_wave.py)

Play a wave of pulses on TinyFX's outputs.


### Binary Counter
[effects/binary_counter.py](effects/binary_counter.py)

Play an incrementing binary counter on TinyFX's outputs.


### Traffic Light
[effects/mono/traffic_light.py](effects/mono/traffic_light.py)

Play a traffic light sequence on TinyFX's outputs.


## Colour Effect Examples

### Rainbow
[effects/colour/rainbow.py](effects/colour/rainbow.py)

Play a rainbow effect on TinyFX's RGB output.


### Random
[effects/colour/random.py](effects/colour/random.py)

Play a randomly changing brightness and colour effect on TinyFX's RGB output.


### Hue Step
[effects/colour/hue_step.py](effects/colour/hue_step.py)

Play a stepped hue effect on TinyFX's RGB output.


## Audio Examples

### Read Button
[function/read_button.py](function/read_button.py)

Show the state of TinyFX's Boot button on its RGB output.


### Sensor Meter
[function/sensor_meter.py](function/sensor_meter.py)

Use TinyFX's mono outputs as a bargraph to show the voltage measured from a sensor attached to the sensor connector.


### Voltage Meter
[function/voltage_meter.py](function/voltage_meter.py)

Use TinyFX's mono outputs as a bargraph to show the voltage that is powering the board.


## Showcase Examples

### Rescue Vehicle
[showcase/rescue_vehicle.py](showcase/rescue_vehicle.py)

Play an alternating flashing sequence on two of TinyFX's outputs, recreating the effect of rescue vehicle beacons. The other outputs are static for illuminated head and tail lights.


### Sensor Wave
[showcase/sensor_wave.py](showcase/sensor_wave.py)

Play a wave of pulses on TinyFX's outputs, who's speed is controlled by a sensor.


### Ship Thrusters
[showcase/ship_thrusters.py](showcase/ship_thrusters.py)

Play a set of flickering thruster effects on a model spaceship, with an RGB light used for planetshine underglow.


### Space Tales
[showcase/space_tales.py](showcase/space_tales.py)

Play effects for each space themed "postcard".


### Space Tales with PIR Sensor
[showcase/space_tales_pir.py](showcase/space_tales_with_pir.py)

Play effects for each space themed "postcard" when someone walks past. A PIR sensor is used to activate the effect, which will turn off after a certain time.
