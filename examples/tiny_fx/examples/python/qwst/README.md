# Tiny FX Micropython Qw/ST Examples <!-- omit in toc -->

These are micropython examples for driving Tiny FX from a sensor plugged into its Qw/ST connector.

- [Examples](#examples)
  - [Light Level](#light-level)
  - [Weather Reading](#weather-reading)
  - [Spirit Level](#spirit-level)


## Examples

### Light Level
[light_level.py](light_level.py)

Bring Tiny FX's lights up when the room gets dark, read from an LTR559 light sensor on Qw/ST.

### Weather Reading
[weather_reading.py](weather_reading.py)

Show the temperature on Tiny FX's RGB output, read from a BME280 weather sensor on Qw/ST.

### Spirit Level
[spirit_level.py](spirit_level.py)

Use Tiny FX's mono outputs as a spirit level, read from a multi sensor stick or another LSM6DS3 accelerometer on Qw/ST.
