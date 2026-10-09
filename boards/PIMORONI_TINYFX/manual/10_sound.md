## Sound

The board plays a WAV file through its speaker, alongside whatever the lights
are doing:

```entry
audio: wav file=chimes.wav
audio: wav file=ambience.wav loop=yes
```

The file plays once as the board starts, or over and over with `loop`. The board
plays one sound at a time, so each scene takes one `audio` entry, and one more may
sit before any heading. Put the file on this drive beside `effects.txt`.

A file is looked for on this drive first, then on the board itself. While the
computer is copying to this drive the sound waits in silence with the effects.

An ordinary uncompressed WAV plays, mono or stereo; MP3 does not.

The drive is small, so a lower sample rate fits more: a minute of 22kHz mono
takes about 2.6MB, which is more than the drive holds, and 8kHz mono takes
under 1MB.
