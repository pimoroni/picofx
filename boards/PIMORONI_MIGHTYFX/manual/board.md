<!-- block entry_examples -->

```entry
out1-7: rainbow_wave speed=0.3
out3 level=50%: pulse speed=0.6
```

<!-- block naming_outputs -->

| Written | Means |
| --- | --- |
| `out1` | one output |
| `out1,3,5` | three of them |
| `out1-7` | all seven |
| `out7-1` | all seven, the other way round |
| `out2,1,5-7` | mixed, and in the order you write them |

An output shows colour. Its red, green and blue can be driven separately as
three plain lights instead:

| Written | Means |
| --- | --- |
| `out3.r` | just the red |
| `out3.*` | all three of them, red, green then blue |
| `out1-7.*` | all 21, from 1's red to 7's blue |
| `out7-1.*` | all 21 the other way round, from 7's blue to 1's red |

<!-- block setting_examples -->

```entry
out1-7 level=50%: pulse
out1-3 colour=warm: flicker
out4 colour=ff8040: static
out1 level=0.5, 2 level=0.8, 3-7: pulse_wave
out1-7 ease=0.4: blink speed=0.5
```

Colours by name: red, orange, yellow, green, cyan, blue, purple, magenta, pink,
warm, white, cool, black. Or the hex a colour picker gives you, with its `#`
left off, as `out4` above uses for an orange paler than the named one. A `#`
always starts a comment, so one left on a colour hides the rest of the line.

<!-- block fade_and_ease -->

### Fade and ease

`fade` and `ease` take the seconds a change takes to get there. `fade` crosses
evenly, which is what a stage light does; `ease` goes quickly at first and slows
as it arrives, which is how a bulb warms and is the one that looks natural on a
light switching on and off.

An output follows one way or the other, so a line takes one of them and not
both. Two numbers divided by `|` give the rise and the fall their own lengths,
a light that comes on quickly and fades out slowly being the usual reason:

```entry
out1-7 fade=0.8: blink speed=0.5
out1-3 ease=0.05|1.2: blink speed=1
```

Softening belongs to the output, not to the effect, so it works on any effect.
