# Pimoroni Mighty FX Playback - Library Reference <!-- omit in toc -->

This is the library reference for the `playback` module, which plays animated GIFs and image sequences on an SP/CE screen.


## Table of Content <!-- omit in toc -->
- [Getting Started](#getting-started)
- [Playing an Animated GIF](#playing-an-animated-gif)
- [Playing an Image Sequence](#playing-an-image-sequence)
- [Timing](#timing)
- [Controlling Playback](#controlling-playback)
- [Preparing Images](#preparing-images)
- [Running Out of Memory](#running-out-of-memory)
- [`ImagePlayer` Reference](#imageplayer-reference)
  - [Variables](#variables)
  - [Functions](#functions)
- [`GIFPlayer` Reference](#gifplayer-reference)
  - [Variables](#variables-1)
  - [Functions](#functions-1)
- [`SequencePlayer` Reference](#sequenceplayer-reference)
  - [Variables](#variables-2)
  - [Functions](#functions-2)


## Getting Started

A player turns a numbered sequence of images into an animation. It keeps the clock and reports which frame to draw, and never draws it, so one screen update can carry two players' frames and a player can feed any screen, pair or group:

```python
from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from playback import GIFPlayer

mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = SCREEN_TYPES["2.8"](mighty.spce_a)

player = GIFPlayer("/images/animation.gif")
while True:
    if player.has_advanced():
        screen.update(player.image)
```

`GIFPlayer` plays an animated GIF and `SequencePlayer` plays a folder of image files, one file a frame. Both are an `ImagePlayer`, which holds the timing and the controls below.


## Playing an Animated GIF

```python
GIFPlayer(path, fps=None, loop=True, ping_pong=False, first_as_last=False, hold=0, paused=False)
```

The whole GIF is decoded once at construction, so a frame costs nothing to reach. `fps=None` plays at the delays the file declares. Those are often whatever the exporting tool wrote, and a screen presents a frame only so fast, so a file asking for more than the screen can give gets its speed and not its smoothness: `measured_fps` against `target_fps` says by how much.

A GIF's frames share a size, so the player reports `width` and `height`. Its `palette` is the colour table every frame shares, and is writable: the frames are cells of one image, so rewriting an entry recolours the whole animation at once. A truecolour GIF has no palette.


## Playing an Image Sequence

```python
SequencePlayer(folder, fps=None, timings=None, loop=True, ping_pong=False, first_as_last=False, hold=0, paused=False)
```

Frames are PNG, JPEG or single-frame GIF files, ordered by the numbers in their names, so an export numbering past nine without padding still plays in order. An animated GIF is `GIFPlayer`'s job.

`fps=None` reads the delay each name declares, in the form an ezgif export writes: `frame_3_delay-0.08s.png`. A caller with delays from anywhere else passes `timings`, one delay in milliseconds per frame in play order, and `fps=n` names one rate for every frame.

Every frame decodes into memory at construction, which blocks for seconds and says so on the console as it goes. `path` is the file behind the frame on show, and `path_at(frame)` the file behind any frame, for a gallery listing what it holds or a menu naming a frame to jump to.


## Timing

A frame is one image of the source and a step is one place in the traversal. The frame to show is a pure function of the elapsed time, so pausing, positioning and reversing all just move the clock.

- `fps=None` takes the source's own delays. A number names a rate and ignores them. `fps=False` removes the clock, so `advance()` drives the player instead. Without a clock the figures over the cycle all read `None`, and anything that would consult one raises `ValueError` naming the setting it needs.
- `loop=True` repeats; `loop=False` plays once and comes to rest on the last frame, which `is_done()` reports.
- `ping_pong=True` plays out and back, visiting most frames twice and turning at each end.
- `hold` waits at each turn, in seconds, on top of the frame's own delay. One value waits at both turns; a pair of values is the wait at the far end, then the wait back at the start, which only a looping ping-pong has. An animation that plays straight through has nowhere to hold, so it refuses one.
- `first_as_last=True` plays the first frame again as the last, for an animation drawn to loop, so a ping-pong travels the whole loop in each direction. That frame counts as one more in `frames`. A forward loop has no last frame, so it refuses this.
- `paused=True` starts on the first frame and waits for `play()`.

`cycle_ms` is one full traversal, dwells and both ping-pong legs included. `target_ms` and `target_fps` are the mean interval a frame is meant to show for, dwells excluded, a mean because a GIF's frames may each declare their own delay. `measured_ms` and `measured_fps` are the last interval between frames that actually reached the caller. Read them where `has_advanced()` returns `True`, which is when they change.


## Controlling Playback

`has_advanced()` reports whether the frame has moved since it last reported, the first call firing, so a loop redraws only when there is something new. Two players can share one condition, since the position comes from the clock and not from a count of calls.

`frame` is the frame number to play and `image` the image for it, both readable in every state. Under ping-pong the same frame number is reported on the way out and the way back, and `is_reversed()` says which leg. `image_at(frame)` is the image for any frame number, for a caller drawing a frame the player is not on, such as one player feeding two screens a fixed distance apart.

`pause()` holds the current frame and `play()` carries on; positioning and `reverse()` still work while paused. `is_playing()` is whether the frame is advancing, so `False` when paused and when done.

`to_frame(frame)` positions on a frame by number, negatives counting from the end, with `to_first()` and `to_last()` for the ends. A ping-pong shows a frame twice and this lands on the first of them. Landing on a turn does not spend its dwell, which is earned by arriving.

`reverse()` turns around from where it stands. Under ping-pong it drops the balance of any dwell and carries on the other way; on a plain order the order itself flips. The frame on screen keeps its own delay either way.

`advance()` moves on one frame, for a player built with `fps=False`.


## Preparing Images

Every frame is stored in memory while it plays. Measured on a Mighty FX, 8 truecolour frames of 320x320 cost 410KB each and 2.2 seconds to load, where 160 half-size palettised frames cost 20KB each and 6.1 seconds. Palettised sources are worth roughly twenty times the animation for the same memory, so a long sequence wants exporting half size and indexed, and drawing back with `pixel_double=True`.


## Running Out of Memory

A player that cannot fit its frames raises `MemoryError` naming the file, what it needed and what was free, since MicroPython's own message gives the bytes and nothing else. Where more was free than was asked for, the memory is in pieces smaller than the one piece a frame needs. `out_of_memory(path, error)` is the function that restates the error, for a caller decoding images of its own.


## `ImagePlayer` Reference

Not built directly: construct a `GIFPlayer` or a `SequencePlayer`.

### Variables
```python
frames: int                 # How many frames there are to play
frame: int                  # The frame number to play
image: Image                # The image for it
cycle_ms: int | None        # One full traversal, dwells and both ping-pong legs included
target_ms: float | None     # The mean interval a frame is meant to show for
target_fps: float | None
measured_ms: int            # The last interval between frames reaching the caller
measured_fps: float
```

### Functions
```python
# Frames
has_advanced() -> bool
image_at(frame: int) -> Image
advance() -> None

# Direction
reverse() -> None
is_reversed() -> bool

# Position
to_frame(frame: int) -> None
to_first() -> None
to_last() -> None

# Playing
pause() -> None
play() -> None
is_playing() -> bool
is_done() -> bool
```


## `GIFPlayer` Reference

### Variables
```python
width: int                  # One frame's size in pixels
height: int
palette: Palette | None     # The colour table every frame shares, None for truecolour
palette_size: int           # Entries in that table, 0 for truecolour
```

### Functions
```python
GIFPlayer(path: str,
          fps: float | None | bool=None,
          loop: bool=True,
          ping_pong: bool=False,
          first_as_last: bool=False,
          hold: float | tuple[float, float]=0,
          paused: bool=False)
```


## `SequencePlayer` Reference

### Variables
```python
path: str                   # The file behind the frame on show
```

### Functions
```python
SequencePlayer(folder: str,
               fps: float | None | bool=None,
               timings: tuple[int]=None,
               loop: bool=True,
               ping_pong: bool=False,
               first_as_last: bool=False,
               hold: float | tuple[float, float]=0,
               paused: bool=False)

path_at(frame: int) -> str

# Module function
out_of_memory(path: str, error: MemoryError) -> MemoryError
```
