## LED strips

A strip of WS2812 LEDs plugs into the connector marked **L** or **R**, and its
LEDs take the same effects, colours and levels the outputs do. Tell the board
how long it is first, since that is the one thing it cannot work out for itself:

```entry
board: stripL=60
stripL: rainbow_wave speed=0.3
```

| Written | Means |
| --- | --- |
| `stripL` | every LED on the strip |
| `stripL5` | one of them |
| `stripL1-10` | the first ten |
| `stripL60-1` | all sixty, the other way round, for a strip mounted backwards |

`stripR` is the same for the other connector. Both share one power supply, so a
strip on either lights the small LED between them, and anything plugged into the
one you are not using is powered too.

Each LED shows a colour of its own, so `stripL5.r` is not a thing to write; set
`colour` on the LEDs instead, as an output takes it.

Most strips take their colours as green, red, then blue, and the board sends
them that way. If yours shows another colour where you asked for red, it takes
them in another order: write the letters `r`, `g` and `b` after its length in
the order it wants them, such as `stripL=60|rgb`.
