## The board

One entry sets the board rather than the lights, and names no output:

```entry
board: reload=auto
```

| Setting | What it does | If omitted |
| --- | --- | --- |
| `drive` | `manual` keeps the drive hidden until you ask for it | shown at boot |
| `reload` | `auto` plays the file the moment it is saved | wait for an eject or **Boot** |
| `program` | a Python file to run instead of the effects | the effects run |
| `args` | what to pass that program, divided by `\|` | it is given none |

With `reload=auto`, saving `effects.txt` is enough on its own: the board notices
the save, takes the drive back for a moment, and plays the new effects, exactly
as a single press of **Boot** would. Only a save to `effects.txt` counts, so
copying sounds on never interrupts anything.

### Running your own program

A program can sit on this drive or on the board's own filesystem, and its name
may include folders: it is looked for here first, then on the board, so
`program=examples/effects/mono/sweep_trail.py` reaches one of the examples the
board ships with. Where the name is in both, this drive's copy runs. If it is
missing, or stops with an error, the effects run instead and `errors.txt` says
what happened.

Saving a file that names a program, while the effects play, restarts the board,
which then runs the program as it would from power on.

The effects stop while a program runs, and **Boot** and ejecting do nothing. The
drive is shown anyway, even with `drive` set to `manual`, so you can still edit
`effects.txt`. With `reload=auto`, saving it restarts the board, which then plays
whatever it now says; without, press **Reset** for the change to take.

### What is already on the board

| Folder | What is in it |
| --- | --- |
| `examples/effects/mono` | one output at a time, and the effects that travel across several |
| `examples/effects/colour` | the RGB output |
| `examples/function` | the button, the sensor connector and the supply voltage |
| `examples/infrared` | effects chosen with an infrared remote |
| `examples/qwst` | light, tilt and weather from Qw/ST breakouts |
| `examples/comms` | several boards working together |
| `examples/showcase` | larger builds that put several of these together |

The audio examples' sounds are not on the board, to leave this drive its room.
