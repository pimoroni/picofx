# Tiny FX Micropython Function Examples <!-- omit in toc -->

These are micropython examples for Tiny FX's onboard functions, being its Boot button, its sensor header and its voltage sense.

- [Examples](#examples)
  - [Read Button](#read-button)
  - [Count Taps](#count-taps)
  - [Sensor Meter](#sensor-meter)
  - [Voltage Meter](#voltage-meter)


## Examples

### Read Button
[read_button.py](read_button.py)

Show the state of TinyFX's Boot button on its RGB output.

### Count Taps
[count_taps.py](count_taps.py)

Count taps of TinyFX's Boot button, including the ones made while the board is busy, and show the count on its mono outputs.

### Sensor Meter
[sensor_meter.py](sensor_meter.py)

Use TinyFX's mono outputs as a bargraph to show the voltage measured from a sensor attached to the sensor connector.

### Voltage Meter
[voltage_meter.py](voltage_meter.py)

Use TinyFX's mono outputs as a bargraph to show the voltage that is powering the board.
