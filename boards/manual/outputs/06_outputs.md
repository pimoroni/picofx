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

<!-- board fade_and_ease -->
