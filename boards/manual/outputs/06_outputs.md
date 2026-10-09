## Outputs

### Naming outputs

<!-- board naming_outputs -->

Order matters for the effects that travel: they move in the order you write the
outputs, so list them in the order they appear in your model, which need not be
number order.

### Setting an output

Before the colon, and separate from the effect:

| Setting | What it does | If omitted |
| --- | --- | --- |
| `level` | how bright, 0 to 1, such as 0.5 or 50% | 1 |
| `colour` | a name or six-digit hex, for __COLOUR_SETTING_FOR__ | white |
| `fade` | seconds to follow the effect, at a steady rate | follows at once |
| `ease` | seconds to follow it, settling in as a bulb does | follows at once |

<!-- board setting_examples -->

Colours by name: red, orange, yellow, green, cyan, blue, purple, magenta, pink,
warm, white, cool, black. Or the hex a colour picker gives you, with its `#`
left off, such as ff8040 for an orange paler than the named one. A `#` always
starts a comment, so one left on a colour hides the rest of the line.

### Fade and ease

`fade` and `ease` take the seconds a change takes to get there. `fade` crosses
evenly, which is what a stage light does; `ease` goes quickly at first and slows
as it arrives, which is how a bulb warms and is the one that looks natural on a
light switching on and off.

An output follows one way or the other, so a line takes one of them and not
both. Two numbers divided by `|` give the rise and the fall their own lengths,
a light that comes on quickly and fades out slowly being the usual reason:

```entry
__ALL_OUTPUTS__ fade=0.8: blink speed=0.5
out1-3 ease=0.05|1.2: blink speed=1
```

Softening belongs to the output, not to the effect, so it works on any effect.
