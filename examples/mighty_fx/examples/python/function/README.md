# Mighty FX Micropython Function Examples <!-- omit in toc -->

These are micropython examples for Mighty FX's onboard functions, being its Boot button, its voltage sense and its sensor connector.

- [Examples](#examples)
  - [Read Button](#read-button)
  - [Count Taps](#count-taps)
  - [Sensor Meter](#sensor-meter)
  - [Voltage Meter](#voltage-meter)


## Examples

### Read Button
[read_button.py](read_button.py)

Show the state of Mighty FX's Boot button on its RGB outputs.

### Count Taps
[count_taps.py](count_taps.py)

Count taps of Mighty FX's Boot button and show the count on its RGB outputs, including the taps made while the board is busy.

### Sensor Meter
[sensor_meter.py](sensor_meter.py)

Use Mighty FX's RGB outputs as a bargraph to show the voltage measured from a sensor attached to the sensor connector.

### Voltage Meter
[voltage_meter.py](voltage_meter.py)

Use Mighty FX's RGB outputs as a bargraph to show the voltage that is powering the board.
