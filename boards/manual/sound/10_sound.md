## Sound

The board plays a WAV file through __SOUND_THROUGH__, alongside whatever
else it is doing:

```entry
audio: wav file=chimes.wav
audio: wav file=ambience.wav loop=yes
```

| Plays | Settings |
| --- | --- |
| `wav` | `file` `loop=no` |

The file plays once as the board starts, or over and over with `loop`. The board
plays one sound at a time, so each scene takes one `audio` entry, and one more may
sit before any heading.

A file is looked for on this drive first, then on the board itself. The board
opens it before this drive is shown, so a computer taking the drive does not stop
the sound. While the computer is copying to this drive the sound waits in silence
with the effects, and a file replaced under a playing sound stays silent until
the next reload.

An ordinary uncompressed WAV plays, mono or stereo; MP3 does not. This drive
holds __DRIVE_SIZE__, so a lower sample rate fits more: a minute of 16-bit 22kHz
mono takes about 2.6MB, and the same at 8kHz under 1MB.

An `audio` entry inside a scene plays while that scene shows, and one before any
heading plays whenever the showing scene brings no sound of its own. A sound
put aside by a scene change picks up where it left off when its turn comes back,
and one that had already finished starts again from the top. A scene with
`restart` starts its sound from the top every time, along with everything else
it holds.
