# TinyFX Micropython Examples <!-- omit in toc -->

These are micropython examples for the Pimoroni [TinyFX](https://shop.pimoroni.com/products/tiny_fx), a stamp-sized light and sound effects controller board for model making, construction kits, and dioramas.

- [Function Examples](#function-examples)
- [Effect Examples](#effect-examples)
  - [Traffic Light](#traffic-light)
  - [Wave Sequence](#wave-sequence)
- [Audio Examples](#audio-examples)
- [Showcase Examples](#showcase-examples)
  - [Ship Thrusters](#ship-thrusters)
  - [Space Tales](#space-tales)
  - [Space Tales with PIR Sensor](#space-tales-with-pir-sensor)


## Function Examples



## Effect Examples

### Traffic Light
[effects/traffic_light.py](effects/traffic_light.py)

Play a traffic light sequence on TinyFX's outputs.


### Wave Sequence
[effects/wave.py](effects/wave.py)

Read Yukon's onboard Buttons.


## Audio Examples



## Showcase Examples

### Ship Thrusters
[showcase/ship_thrusters.py](showcase/ship_thrusters.py)

Play a set of flickering thruster effects on a model spaceship, with an RGB light used for planetshine underglow.


### Space Tales
[showcase/space_tales.py](showcase/space_tales.py)

Play effects for each space themed "postcard".


### Space Tales with PIR Sensor
[showcase/space_tales_pir.py](showcase/space_tales_with_pir.py)

Play effects for each space themed "postcard" when someone walks past.
A PIR sensor is used to activate the effect, which will turn off after a certain time.
