# Mighty FX Micropython Function Examples <!-- omit in toc -->

These are micropython examples for Mighty FX's onboard functions, being its Boot button, its voltage sense and its sensor connector.

- [Examples](#examples)
  - [Count Taps](#count-taps)
  - [Read Button](#read-button)
  - [Sensor Meter](#sensor-meter)
  - [Voltage Meter](#voltage-meter)


## Examples

### Count Taps
[count_taps.py](count_taps.py)

Count taps of MightyFX's Boot button, including the ones that happen while the board is busy, and show the count on its RGB outputs.

### Read Button
[read_button.py](read_button.py)

Show the state of MightyFX's Boot button on its RGB outputs.

### Sensor Meter
[sensor_meter.py](sensor_meter.py)

Use MightyFX's RGB outputs as a bargraph to show the voltage measured from a sensor attached to the sensor connector.

### Voltage Meter
[voltage_meter.py](voltage_meter.py)

Use MightyFX's RGB outputs as a bargraph to show the voltage that is powering the board.
