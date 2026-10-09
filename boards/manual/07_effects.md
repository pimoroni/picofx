## Effects

Every setting can be left out, and the board fills in the value shown against it
below. The few with none shown have nothing to fall back on, and each is covered
where its effect is.

### For __MONO_EFFECTS_FOR__

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

### For __COLOUR_EFFECTS_FOR__ only, since these bring their own colour

| Effect | Settings |
| --- | --- |
| `rgb` | `red=255` `green=255` `blue=255` |
| `hsv` | `hue=0` `sat=1` `val=1` |
| `rainbow` | `speed=1` `sat=1` `val=1` |
| `rainbow_wave` | `speed=1` `length=1` `sat=1` `val=1` |
| `hue_step` | `interval=1` `hue=0` `sat=1` `val=1` `steps=6` |
| `rgb_blink` | `colour` `speed=1` `phase=0` `duty=0.5` |

### Which ones travel

The ones ending `_wave`, `_sequence` and `_counter`, and `sweep`, travel across
the outputs you name; the rest do the same thing on every one.

The ones ending `_each` give every output its own: `flicker_each` dips each at
its own moments, as flames do, and `random_each` gives each its own brightness.
`flicker` and `random` do the same to all of them at once, as one light would:

```entry
__FLAME_OUTPUTS__: flicker_each dimness=0.6
```

An effect that drives several outputs takes them in the order given in its own
section below, so naming fewer than it drives lights the first of them and
leaves the rest out. Naming more than it drives is a mistake, and `errors.txt`
says so.

### Traffic lights and crossings

`traffic_light` wants three outputs, and lights them red, amber and green in
that order. It switches instantly, so add `ease` for the lamps of a real signal:

```entry
out1-3 ease=0.3: traffic_light
```

`pelican_crossing` wants five outputs: the same three, then the two figures a
pedestrian reads, stop and walk. In place of red and amber it flashes the amber
and the walking figure together, as a pelican does while a crossing ends. It
comes round on its own clock, there being no button to press:

```entry
out1-5 ease=0.3: pelican_crossing green_interval=20 red_interval=8
```

Three outputs on `pelican_crossing` is its traffic lights on their own:

```entry
out1-3: pelican_crossing
```

### Sweep

`sweep` is a light that crosses the outputs and turns back at each end, the back
and forth a scanner does. Its `extent` is how far it reaches from itself, in
outputs, and its `speed` counts one crossing as the travelling effects count one
pass. Its `hold` waits at each end, in seconds, giving a trail time to clear
before the light comes back over it:

```entry
__ALL_OUTPUTS__ ease=0.4: sweep speed=1 length=__OUTPUT_COUNT__ extent=1 hold=1
```

Give `extent` a whole number of outputs, such as 1 or 2. In between it dims as
the light passes between two outputs and brightens as it lands on one, which
reads as stepping. 1 is the tightest that travels smoothly.

### Blinking through colours

`rgb_blink` takes one colour, or several to blink through in turn, divided by
`|` since a comma would mean one colour for each output. It has no colour of its
own, so give it at least one:

```entry
__COLOUR_OUTPUT__: rgb_blink colour=red|warm|ff8040 speed=0.5
```

### What the settings mean

`speed` is cycles a second: 1 goes round once a second, 0.5 once every two, 2
twice a second. A negative speed runs the cycle backwards.

The settings measured in seconds are `interval`, `hold`, flicker's `bright_min`,
`bright_max`, `dim_min` and `dim_max`, and the four intervals `traffic_light`
and `pelican_crossing` each take. `length`, `flashes`, `steps`, `count` and
`step` are plain counts, and a negative `step` counts down.

The rest run from 0 to 1, written 0.5 or 50% as you prefer. `window` is one of
them, being the share of a cycle the flashes happen in. `hue` takes degrees as
well, written 180deg, which is what a colour picker gives you.

**If you write Python**, an effect of your own can join this list and be written
here like any other. The library reference on
[GitHub](https://github.com/pimoroni/picofx/blob/main/picofx/README.md) says how,
under Effects System.
