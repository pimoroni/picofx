<!-- block entry_examples -->

```entry
out1-6: pulse_wave speed=0.3
rgb: rainbow speed=0.5
out3 level=50%: pulse speed=0.6
```

<!-- block naming_outputs -->

| Written | Means |
| --- | --- |
| `out1` | one output |
| `out1,3,5` | three of them |
| `out1-6` | all six |
| `out6-1` | all six, the other way round |
| `out2,1,5-6` | mixed, and in the order you write them |
| `rgb` | the RGB output |

The RGB output shows colour. Its red, green and blue can be driven separately as
three plain lights instead, and named alongside the others:

| Written | Means |
| --- | --- |
| `rgb.r` | just the red |
| `rgb.*` | all three of them, red, green then blue |
| `out1-6,rgb.*` | all nine plain lights |

<!-- block setting_examples -->

```entry
out1-6 level=50%: pulse
rgb colour=warm: flicker
out1-6 ease=0.4: blink speed=0.5
```

Colours by name: red, orange, yellow, green, cyan, blue, purple, magenta, pink,
warm, white, cool, black. Or the hex a colour picker gives you, with its `#`
left off. A `#` always starts a comment, so one left on a colour hides the rest
of the line.

<!-- block fade_and_ease -->

### Fade and ease

`fade` and `ease` take the seconds a change takes to get there. `fade` crosses
evenly, which is what a stage light does; `ease` goes quickly at first and slows
as it arrives, which is how a bulb warms. Two numbers divided by `|` give the
rise and the fall their own lengths:

```entry
out1-3 ease=0.05|1.2: blink speed=1
```
