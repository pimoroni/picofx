# Mighty FX Micropython Screen Examples <!-- omit in toc -->

These are micropython examples for the screens Mighty FX can drive from its SP/CE ports, one panel at a time, as a pair, or across a hub.

- [Single Screen Examples](#single-screen-examples)
  - [Detect Screens](#detect-screens)
  - [Backlight Fade](#backlight-fade)
  - [Screen Sizes](#screen-sizes)
- [Graphics Examples](#graphics-examples)
  - [Colour Wheel](#colour-wheel)
  - [Starfield](#starfield)
  - [Pixel Fonts](#pixel-fonts)
  - [LED Matrix](#led-matrix)
  - [Shapes](#shapes)
  - [Paths](#paths)
  - [Pens](#pens)
  - [Filters](#filters)
  - [Colours](#colours)
  - [Text Layout](#text-layout)
  - [Vector Fonts](#vector-fonts)
  - [Sprites](#sprites)
  - [Easing Curves](#easing-curves)
- [Image Examples](#image-examples)
  - [Alternating Images](#alternating-images)
  - [Poster Ticker](#poster-ticker)
- [Layout Examples](#layout-examples)
  - [Bouncing Logo](#bouncing-logo)
  - [Orientations](#orientations)
  - [Pixel Doubled](#pixel-doubled)
  - [Kaleidoscope](#kaleidoscope)
  - [Tiled Bricks](#tiled-bricks)
  - [Tiled Arrows](#tiled-arrows)
- [Screen Pair Examples](#screen-pair-examples)
  - [Colour Wheel (Paired)](#colour-wheel-paired)
  - [Colour Wheel (Unpaired)](#colour-wheel-unpaired)
  - [Colour Wheel (Facing)](#colour-wheel-facing)
  - [Drifting Carpets](#drifting-carpets)
  - [Test Cards Paired](#test-cards-paired)
- [Screen Hub Examples](#screen-hub-examples)
  - [Detect Hub](#detect-hub)
  - [Chevron Banks](#chevron-banks)
  - [Starfield (Wall)](#starfield-wall)
- [Playback Examples](#playback-examples)
  - [Animated GIF](#animated-gif)
  - [Animated GIF (Paired)](#animated-gif-paired)
  - [Animated GIF (Ping Pong)](#animated-gif-ping-pong)
  - [Body Scanner](#body-scanner)
  - [Street Billboard](#street-billboard)
  - [Billboard (Folders)](#billboard-folders)
  - [Billboard (Paired)](#billboard-paired)
  - [Billboard (Slideshow)](#billboard-slideshow)
  - [Billboard (Wall)](#billboard-wall)
  - [Animated GIF (Dual)](#animated-gif-dual)
  - [Neon Rosie](#neon-rosie)
  - [Circuit Traces](#circuit-traces)
  - [Circuit Traces (Wall)](#circuit-traces-wall)


## Single Screen Examples

### Detect Screens
<img src="single/detect_screens.png" align="left" alt="Detect Screens">
<img src="single/detect_screens-2.png" align="left" alt="Detect Screens, second screen">

[single/detect_screens.py](single/detect_screens.py)

Show which screen sits on each SP/CE port. Every screen is painted its port's colour, with its letter in the top left over one bar for A or two for B.

<br clear="left">


### Backlight Fade
<img src="single/backlight_fade.png" align="left" alt="Backlight Fade">

[single/backlight_fade.py](single/backlight_fade.py)

Fade a screen's backlight up and down over a still frame.

<br clear="left">


### Screen Sizes
<img src="single/screen_sizes.png" align="left" alt="Screen Sizes">
<img src="single/screen_sizes-2.png" align="left" alt="Screen Sizes, second screen">

[single/screen_sizes.py](single/screen_sizes.py)

Build both screen types explicitly, one on each SP/CE port, and let each panel say which it is.

<br clear="left">


## Graphics Examples

### Colour Wheel
<img src="graphics/color_wheel.png" align="left" alt="Colour Wheel">

[graphics/color_wheel.py](graphics/color_wheel.py)

Spin a rainbow wheel on a screen.

<br clear="left">


### Starfield
<img src="graphics/starfield.png" align="left" alt="Starfield">

[graphics/starfield.py](graphics/starfield.py)

Travel through a star field.

<br clear="left">


### Pixel Fonts
<img src="graphics/pixel_fonts.png" align="left" alt="Pixel Fonts">

[graphics/pixel_fonts.py](graphics/pixel_fonts.py)

Scroll a line of text in each built-in pixel font from smallest to largest.

<br clear="left">


### LED Matrix
<img src="graphics/led_matrix.png" align="left" alt="LED Matrix">

[graphics/led_matrix.py](graphics/led_matrix.py)

Show a rainbow on an LED matrix sign made of round lamps.

<br clear="left">


### Shapes
<img src="graphics/shapes.png" align="left" alt="Shapes">

[graphics/shapes.py](graphics/shapes.py)

Spin every built-in shape both filled and outlined.

<br clear="left">


### Paths
<img src="graphics/paths.png" align="left" alt="Paths">

[graphics/paths.py](graphics/paths.py)

Compare the settings that change how a path is drawn.

<br clear="left">


### Pens
<img src="graphics/pens.png" align="left" alt="Pens">

[graphics/pens.py](graphics/pens.py)

Fill a circle with six pens ranging from a plain colour to a picture.

<br clear="left">


### Filters
<img src="graphics/filters.png" align="left" alt="Filters">

[graphics/filters.py](graphics/filters.py)

Compare eleven filters on the same picture.

<br clear="left">


### Colours
<img src="graphics/colours.png" align="left" alt="Colours">

[graphics/colours.py](graphics/colours.py)

Mix evenly spaced hues and pick text colours that stay readable on any background.

<br clear="left">


### Text Layout
<img src="graphics/text_layout.png" align="left" alt="Text Layout">

[graphics/text_layout.py](graphics/text_layout.py)

Wrap and align text inside a box.

<br clear="left">


### Vector Fonts
<img src="graphics/vector_fonts.png" align="left" alt="Vector Fonts">

[graphics/vector_fonts.py](graphics/vector_fonts.py)

Write each built-in vector font's name in that font at several sizes.

<br clear="left">


### Sprites
<img src="graphics/sprites.png" align="left" alt="Sprites">

[graphics/sprites.py](graphics/sprites.py)

Draw a sprite with blit() and with an image pen that can also rotate it.

<br clear="left">


### Easing Curves
<img src="graphics/easing_curves.png" align="left" alt="Easing Curves">

[graphics/easing_curves.py](graphics/easing_curves.py)

Plot every easing curve with a marker moving along each one.

<br clear="left">


## Image Examples

### Alternating Images
<img src="images/alternating_images.png" align="left" alt="Alternating Images">

[images/alternating_images.py](images/alternating_images.py)

Switch between two PNG pictures shown for different lengths of time.

<br clear="left">


### Poster Ticker
<img src="images/poster_ticker.png" align="left" alt="Poster Ticker">

[images/poster_ticker.py](images/poster_ticker.py)

Scroll a message across a poster in lettering that matches it.

<br clear="left">


## Layout Examples

### Bouncing Logo
<img src="layout/bouncing_logo.png" align="left" alt="Bouncing Logo">

[layout/bouncing_logo.py](layout/bouncing_logo.py)

Bounce a logo around the screen and change its colour at each edge.

<br clear="left">


### Orientations
<img src="layout/orientations.png" align="left" alt="Orientations">

[layout/orientations.py](layout/orientations.py)

Show the eight ways a picture can be rotated and mirrored on a screen.

<br clear="left">


### Pixel Doubled
<img src="layout/pixel_doubled.png" align="left" alt="Pixel Doubled">

[layout/pixel_doubled.py](layout/pixel_doubled.py)

Fill the screen by doubling every pixel of a picture half its width and height.

<br clear="left">


### Kaleidoscope
<img src="layout/kaleidoscope.png" align="left" alt="Kaleidoscope">

[layout/kaleidoscope.py](layout/kaleidoscope.py)

Turn a kaleidoscope of coloured beads.

<br clear="left">


### Tiled Bricks
<img src="layout/tiled_bricks.png" align="left" alt="Tiled Bricks">

[layout/tiled_bricks.py](layout/tiled_bricks.py)

Fill the whole panel with a brick wall drawn from a tile of 32 by 32 pixels.

<br clear="left">


### Tiled Arrows
<img src="layout/tiled_arrows.png" align="left" alt="Tiled Arrows">

[layout/tiled_arrows.py](layout/tiled_arrows.py)

Fill the screen with a tile mirrored on every other copy to make its edges line up.

<br clear="left">


## Screen Pair Examples

### Colour Wheel (Paired)
<img src="pair/color_wheel_paired.png" align="left" alt="Colour Wheel (Paired)">
<img src="pair/color_wheel_paired-2.png" align="left" alt="Colour Wheel (Paired), second screen">

[pair/color_wheel_paired.py](pair/color_wheel_paired.py)

Spin a rainbow wheel on two screens that are redrawn together.

<br clear="left">


### Colour Wheel (Unpaired)
<img src="pair/color_wheel_unpaired.png" align="left" alt="Colour Wheel (Unpaired)">
<img src="pair/color_wheel_unpaired-2.png" align="left" alt="Colour Wheel (Unpaired), second screen">

[pair/color_wheel_unpaired.py](pair/color_wheel_unpaired.py)

Spin a rainbow wheel on two screens that are redrawn one after the other. Run color_wheel_paired.py to see what a pair does differently.

<br clear="left">


### Colour Wheel (Facing)
<img src="pair/color_wheel_facing.png" align="left" alt="Colour Wheel (Facing)">
<img src="pair/color_wheel_facing-2.png" align="left" alt="Colour Wheel (Facing), second screen">

[pair/color_wheel_facing.py](pair/color_wheel_facing.py)

Spin a rainbow wheel on two facing screens with one of them mirrored.

<br clear="left">


### Drifting Carpets
<img src="pair/drifting_carpets.png" align="left" alt="Drifting Carpets">
<img src="pair/drifting_carpets-2.png" align="left" alt="Drifting Carpets, second screen">

[pair/drifting_carpets.py](pair/drifting_carpets.py)

Drift a different patterned carpet across each of two screens.

<br clear="left">


### Test Cards Paired
<img src="pair/test_cards_paired.png" align="left" alt="Test Cards Paired">
<img src="pair/test_cards_paired-2.png" align="left" alt="Test Cards Paired, second screen">

[pair/test_cards_paired.py](pair/test_cards_paired.py)

Step a test card through each rotation on two screens that mirror each other.

<br clear="left">


## Screen Hub Examples

### Detect Hub
<img src="hub/detect_hub.png" align="left" alt="Detect Hub">

[hub/detect_hub.py](hub/detect_hub.py)

Show which screen is in each position on a Screen Hub. Every panel is painted its position's colour, with its letter in the top left over one bar for A up to six for F.

<br clear="left">


### Chevron Banks
<img src="hub/chevron_banks.png" align="left" alt="Chevron Banks">

[hub/chevron_banks.py](hub/chevron_banks.py)

Flash runway chevrons on alternating sets of screens across a Screen Hub.

<br clear="left">


### Starfield (Wall)
<img src="hub/starfield_wall.png" align="left" alt="Starfield (Wall)">

[hub/starfield_wall.py](hub/starfield_wall.py)

Travel through a star field across every screen on a Screen Hub.

<br clear="left">


## Playback Examples

### Animated GIF
<img src="playback/animated_gif.png" align="left" alt="Animated GIF">

[playback/animated_gif.py](playback/animated_gif.py)

Play an animated GIF on a screen with the timing saved in the file.

<br clear="left">


### Animated GIF (Paired)
<img src="playback/animated_gif_paired.png" align="left" alt="Animated GIF (Paired)">
<img src="playback/animated_gif_paired-2.png" align="left" alt="Animated GIF (Paired), second screen">

[playback/animated_gif_paired.py](playback/animated_gif_paired.py)

Play the same animated GIF in step on two screens.

<br clear="left">


### Animated GIF (Ping Pong)
<img src="playback/animated_gif_ping_pong.png" align="left" alt="Animated GIF (Ping Pong)">

[playback/animated_gif_ping_pong.py](playback/animated_gif_ping_pong.py)

Play an animated GIF forwards then backwards with a pause at each end.

<br clear="left">


### Body Scanner
<img src="playback/animated_gif_recoloured.png" align="left" alt="Body Scanner">

[playback/animated_gif_recoloured.py](playback/animated_gif_recoloured.py)

Change the colours of an animated GIF as it plays.

<br clear="left">


### Street Billboard
<img src="playback/street_billboard.png" align="left" alt="Street Billboard">

[playback/street_billboard.py](playback/street_billboard.py)

Show a folder of posters as if each stood in a case behind glass.

<br clear="left">


### Billboard (Folders)
<img src="playback/billboard_folders.png" align="left" alt="Billboard (Folders)">

[playback/billboard_folders.py](playback/billboard_folders.py)

Show posters from several folders and skip to the next poster or folder with Boot.

<br clear="left">


### Billboard (Paired)
<img src="playback/billboard_paired.png" align="left" alt="Billboard (Paired)">
<img src="playback/billboard_paired-2.png" align="left" alt="Billboard (Paired), second screen">

[playback/billboard_paired.py](playback/billboard_paired.py)

Show a different poster on each of two screens and change them together.

<br clear="left">


### Billboard (Slideshow)
<img src="playback/billboard_slideshow.png" align="left" alt="Billboard (Slideshow)">

[playback/billboard_slideshow.py](playback/billboard_slideshow.py)

Show a folder of posters one at a time.

<br clear="left">


### Billboard (Wall)
<img src="playback/billboard_wall.png" align="left" alt="Billboard (Wall)">

[playback/billboard_wall.py](playback/billboard_wall.py)

Show a different poster on every screen of a Screen Hub and change them all together.

<br clear="left">


### Animated GIF (Dual)
<img src="playback/dual_animated_gifs.png" align="left" alt="Animated GIF (Dual)">
<img src="playback/dual_animated_gifs-2.png" align="left" alt="Animated GIF (Dual), second screen">

[playback/dual_animated_gifs.py](playback/dual_animated_gifs.py)

Play two animated GIFs of different sizes, lengths and speeds on two screens.

<br clear="left">


### Neon Rosie
<img src="playback/neon_ping_pong.png" align="left" alt="Neon Rosie">

[playback/neon_ping_pong.py](playback/neon_ping_pong.py)

Play a folder of picture frames forwards then backwards.

<br clear="left">


### Circuit Traces
<img src="playback/traces_scroll.png" align="left" alt="Circuit Traces">

[playback/traces_scroll.py](playback/traces_scroll.py)

Scroll an animated pattern that curves between horizontal and vertical.

<br clear="left">


### Circuit Traces (Wall)
<img src="playback/traces_wall.png" align="left" alt="Circuit Traces (Wall)">

[playback/traces_wall.py](playback/traces_wall.py)

Play the same animation on every screen of a Screen Hub.

<br clear="left">
