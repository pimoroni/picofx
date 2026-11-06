## LED strips

<!-- board strips_intro -->

```entry
board: __STRIP__=60
__STRIP__: rainbow_wave speed=0.3
```

| Written | Means |
| --- | --- |
| `__STRIP__` | every LED on the strip |
| `__STRIP__5` | one of them |
| `__STRIP__1-10` | the first ten |
| `__STRIP__60-1` | all sixty in reverse order, for a strip mounted backwards |

<!-- board strips_notes -->

Each LED is one colour light, so `__STRIP__5.r` is not valid. Set `colour` on the
LEDs instead, as __COLOUR_TAKER__ takes it.

Most strips take their colours in the order green, red, blue, and the board
sends them that way. If yours shows a different colour when you ask for red,
it uses another order: write the letters `r`, `g` and `b` after its length in
the order it needs, such as `__STRIP__=60|rgb`.
