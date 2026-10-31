import sys

from mighty_fx import MightyFX, SPCE
from screens import SCREEN_TYPES
from picovector import color, image

"""
Drift past a city while the sky turns from noon to midnight and the windows come on.

Nothing is drawn after the load. A 160x120 city is doubled over the panel and tiled sideways, and
its transparent sky shows bg_color. The light is its colour table, so changing it is a few writes.

Each entry's role is read off the table. A colour seen twice is a window lit in its own turn after
dark, a grey is fading concrete, and colour is glass or signage that brightens.

Press "Boot" to exit the program.
"""

# Constants
ART = "/examples/assets/skyline.png"    # The city, palettised and tiling sideways
ROTATION = 90            # Quarter turn, to suit how the screen is mounted
STEP = 1                 # Pixels the city drifts each frame
DAY_FRAMES = 2400        # Frames a whole day and night takes
GREY_SPREAD = 15         # How near red, green and blue sit for an entry to be concrete
NIGHT_FALL = 40          # How much of its own brightness a wall keeps, out of 255
NIGHT_TINT = color.rgb(16, 16, 34)    # And what it settles towards
GLOW = 40                # How much brighter glass and signage get by night
DUSK = 96                # How dark it is before the first window comes on, out of 255
SKY_STEPS = 64           # Shades the sky ramp is asked for

# What a lit window is, taken in turn, so the city is not one flat amber
LAMPS = (color.rgb(255, 198, 96), color.rgb(255, 176, 72),
         color.rgb(250, 214, 140), color.rgb(255, 158, 60))

# Noon down to midnight, the ramp filling in between
SKIES = ((0.0, color.rgb(124, 184, 242)), (0.2, color.rgb(180, 204, 234)),
         (0.4, color.rgb(236, 188, 136)), (0.55, color.rgb(226, 140, 96)),
         (0.7, color.rgb(176, 84, 88)), (0.85, color.rgb(60, 36, 84)),
         (1.0, color.rgb(10, 10, 34)))

# Which screen is on the port, "2.8" or "1.54", or what the effects file passes in args
SCREEN_SIZE = "2.8" if not sys.argv[1:] else sys.argv[1]
ScreenType = SCREEN_TYPES[SCREEN_SIZE]

# Create a MightyFX object with SP/CE port A set up for screens, and the screen on it
mighty = MightyFX(spce_a=SPCE.SCREEN)
screen = ScreenType(mighty.spce_a, rotation=ROTATION)

try:
    city = image.load(ART)
except (ValueError, OSError):
    mighty.shutdown()
    raise RuntimeError(f"'{ART}' is missing or corrupt! Check it is on the board") from None

palette = city.palette

sky_shades = color.ramp(SKIES, SKY_STEPS)

# Each entry paired once with its night colour, except the transparent sky and the black padding
walls = []
lamps = []
seen = set()
for index in range(city.palette_size):
    daylight = palette[index]
    brightest = max(daylight.r, daylight.g, daylight.b)
    if daylight.a == 0 or brightest == 0:
        continue

    # Is it a grey, and so concrete that fades towards the night tint?
    if brightest - min(daylight.r, daylight.g, daylight.b) <= GREY_SPREAD:
        nightfall = color.mix(NIGHT_TINT, daylight, NIGHT_FALL)
    else:
        nightfall = color.lighten(daylight, GLOW)

    # A window falls dark with the concrete around it and is lit from there, so it is not a
    # bright speck on a dark wall while it waits its turn
    shade = (daylight.r, daylight.g, daylight.b)
    if shade in seen:
        lamps.append((index, daylight, nightfall, LAMPS[len(lamps) % len(LAMPS)]))
    else:
        walls.append((index, daylight, nightfall))

    seen.add(shade)

# When each group of windows comes on, spread over what is left of the light after dusk
SPAN = (255 - DUSK) // (len(lamps) + 1)
lit_at = [DUSK + turn * SPAN for turn in range(len(lamps))]

print(f"a {city.width}x{city.height} city doubled over {screen.height}x{screen.width}, {len(walls)} colours"
      f" it is built from and {len(lamps)} groups of windows, coming on from {lit_at[0]} of 255")

frames = 0
lit_to = None       # The darkness the table is currently written for
HALF = DAY_FRAMES // 2

# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while not mighty.boot_pressed():
        # Out to midnight and back, so the day turns rather than jumping from night to noon
        place = frames % DAY_FRAMES
        darkness = place * 255 // HALF if place < HALF else (DAY_FRAMES - place) * 255 // HALF

        # Has the light moved since the table was written?
        if darkness != lit_to:
            for index, daylight, nightfall in walls:
                palette[index] = color.mix(daylight, nightfall, darkness)

            # A window darkens with the walls until its turn comes,
            # then takes the rest of the dusk to reach full
            for turn, (index, daylight, nightfall, lamp) in enumerate(lamps):
                unlit = color.mix(daylight, nightfall, darkness)
                since = darkness - lit_at[turn]
                palette[index] = unlit if since < 0 else color.mix(unlit, lamp,
                                                                   min(255, since * 255 // SPAN))

            lit_to = darkness

        # Doubled and tiled sideways, with the sky filling what the city leaves
        screen.update(city, pixel_double=True, tile=(True, False),
                      bg_color=sky_shades[darkness * (SKY_STEPS - 1) // 255],
                      offset=(-frames * STEP, 0))
        frames += 1

# Stop any running effects and turn off all the outputs
finally:
    mighty.shutdown()
