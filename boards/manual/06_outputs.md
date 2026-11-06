## __OUTPUTS_HEADING__

<!-- board naming_outputs -->

<!-- if outputs -->
Order matters for effects that travel: they move through the outputs in the
order you write them, so list them in the order they appear in your build,
which need not be number order.
<!-- end -->

### Setting an __OUTPUT__

These go before the colon, separate from the effect:

| Setting | What it does | If omitted |
| --- | --- | --- |
| `level` | brightness, 0 to 1, such as 0.5 or 50% | 1 |
| `colour` | a colour name or six-digit hex code, for __COLOUR_SETTING_FOR__ | white |
| `fade` | seconds to fade between changes, at a steady rate | changes instantly |
| `ease` | seconds to ease between changes, slowing at the end like a bulb | changes instantly |

<!-- board setting_examples -->

Colour names: red, orange, yellow, green, cyan, blue, purple, magenta, pink,
warm, white, cool, black. Or a hex code from a colour picker, without its `#`,
such as ff8040 for a paler orange. A `#` always starts a comment, so leaving it
on a colour hides the rest of the line.

### Fade and ease

`fade` and `ease` set how many seconds a change takes. `fade` changes at a
steady rate, like a stage light. `ease` changes quickly at first and slows
towards the end, like a warming bulb, and looks more natural on a light
switching on and off.

An __OUTPUT__ uses one or the other, so a line takes `fade` or `ease`, not
both. Two numbers separated by `|` set the rise and fall separately, for
example a light that comes on quickly and fades out slowly:

```entry
__ALL_OUTPUTS__ fade=0.8: blink speed=0.5
__THREE_OUTPUTS__ ease=0.05|1.2: blink speed=1
```

`fade` and `ease` belong to the __OUTPUT__, not the effect, so they work with any
effect, except effects that set their own colours.
