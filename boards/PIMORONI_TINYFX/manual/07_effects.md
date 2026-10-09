## Effects

Every setting can be left out, and the board fills in the value shown against it
below.

### For any output

| Effect | Settings |
| --- | --- |
| `none` | |
| `static` | `brightness=1` |
| `blink` | `speed=1` `phase=0` `duty=0.5` |
| `blink_wave` | `speed=1` `length=1` `phase=0` `duty=0.5` |
| `flash` | `speed=1` `flashes=2` `window=0.5` `phase=0` `duty=0.5` |
| `flash_sequence` | `speed=1` `length=1` `flashes=1` `window=1` `phase=0` `duty=0.5` |
| `flicker` | `brightness=1` `dimness=0.5` `bright_min=0.05` `bright_max=0.1` `dim_min=0.02` `dim_max=0.04` |
| `flicker_each` | as `flicker` |
| `pulse` | `speed=1` `phase=0` |
| `pulse_wave` | `speed=1` `length=1` `phase=0` |
| `sweep` | `speed=1` `length=1` `extent=1` `hold=0` |
| `random` | `interval=0.05` `brightness_min=0` `brightness_max=1` |
| `random_each` | as `random` |
| `binary_counter` | `interval=0.1` `count=0` `step=1` |
| `traffic_light` | `red_interval=10` `red_amber_interval=5` `green_interval=10` `amber_interval=5` |
| `pelican_crossing` | `red_interval=8` `flashing_interval=6` `green_interval=20` `amber_interval=3` |

### For the RGB output only, since these bring their own colour

| Effect | Settings |
| --- | --- |
| `rgb` | `red=255` `green=255` `blue=255` |
| `hsv` | `hue=0` `sat=1` `val=1` |
| `rainbow` | `speed=1` `sat=1` `val=1` |
| `hue_step` | `interval=1` `hue=0` `sat=1` `val=1` `steps=6` |
| `rgb_blink` | `colour` `speed=1` `phase=0` `duty=0.5` |

### Which ones travel

The ones ending `_wave`, `_sequence` and `_counter`, and `sweep`, travel across
the outputs you name; the rest do the same thing on every one. The ones ending
`_each` give every output its own: `flicker_each` dips each at its own moments,
as flames do.

`traffic_light` wants three outputs, lit red, amber and green in that order, and
`pelican_crossing` five, the same three then the stop and walk figures:

```entry
out1-3 ease=0.3: traffic_light
out1-5 ease=0.3: pelican_crossing
```

`sweep` is a light that crosses the outputs and turns back at each end. Its
`extent` is how far it reaches from itself, in outputs, and `hold` waits at each
end, in seconds:

```entry
out1-6 ease=0.4: sweep speed=1 extent=1 hold=1
```

`rgb_blink` takes one colour, or several to blink through in turn, divided by
`|`:

```entry
rgb: rgb_blink colour=red|warm|ff8040 speed=0.5
```

### What the settings mean

`speed` is cycles a second: 1 goes round once a second, 0.5 once every two. A
negative speed runs the cycle backwards. `interval`, `hold` and the flicker and
signal timings are seconds. `length`, `flashes`, `steps`, `count` and `step` are
plain counts. The rest run from 0 to 1, written 0.5 or 50% as you prefer, and
`hue` takes degrees as well, written 180deg.
