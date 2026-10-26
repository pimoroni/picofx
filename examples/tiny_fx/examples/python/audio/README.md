# Tiny FX Micropython Audio Examples <!-- omit in toc -->

These are micropython examples for the audio Tiny FX can play through its onboard amplifier.

- [Examples](#examples)
  - [Race Start](#race-start)
  - [Encounters](#encounters)
  - [Photon Sword](#photon-sword)
  - [WAV Player](#wav-player)


## Examples

### Race Start
[race_start.py](race_start.py)

Plays a simple boop, boop, boop, beeep countdown sound effect when you press Boot on TinyFX. Great for counting down to a race start.

### Encounters
[fair_use_encounters.py](fair_use_encounters.py)

Play an evocative musical melody with accompanying lights on TinyFX. Any resemblance to music you might have heard elsewhere is purely coincidental.

### Photon Sword
[photon_sword.py](photon_sword.py)

Play sounds that react to motion with a TinyFX. Grab yourself an MSA301 and attach it to the Qw/ST connector.

This example needs the directory `photon_sword` copied over to your TinyFX.

### WAV Player
[wav_player.py](wav_player.py)

Play a WAV file saved to your TinyFX each time Boot is pressed, with the RGB output showing when it is ready and when it is playing.
