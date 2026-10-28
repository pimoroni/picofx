from picovector import color, image

"""
Drawing: Skyline
Drift past a city while the sky turns from noon to midnight and the windows come on.
Section: Animation
"""

# Entry: screenA rotation=90 pixel_double=true: graphics file=skyline.py

# Constants
ART = "/examples/assets/skyline.png"
STEP = 1
DAY_FRAMES = 2400
GREY_SPREAD = 15
NIGHT_FALL = 40
NIGHT_TINT = color.rgb(16, 16, 34)
GLOW = 40
DUSK = 96
SKY_STEPS = 64

LAMPS = (color.rgb(255, 198, 96), color.rgb(255, 176, 72),
         color.rgb(250, 214, 140), color.rgb(255, 158, 60))

SKIES = ((0.0, color.rgb(124, 184, 242)), (0.2, color.rgb(180, 204, 234)),
         (0.4, color.rgb(236, 188, 136)), (0.55, color.rgb(226, 140, 96)),
         (0.7, color.rgb(176, 84, 88)), (0.85, color.rgb(60, 36, 84)),
         (1.0, color.rgb(10, 10, 34)))

try:
    city = image.load(ART)
except (ValueError, OSError):
    raise RuntimeError(f"'{ART}' is missing or corrupt! Check it is on the drive") from None

palette = city.palette
sky_shades = color.ramp(SKIES, SKY_STEPS)

walls = []
lamps = []
seen = set()
for index in range(city.palette_size):
    daylight = palette[index]
    brightest = max(daylight.r, daylight.g, daylight.b)
    if daylight.a == 0 or brightest == 0:
        continue
    if brightest - min(daylight.r, daylight.g, daylight.b) <= GREY_SPREAD:
        nightfall = color.mix(NIGHT_TINT, daylight, NIGHT_FALL)
    else:
        nightfall = color.lighten(daylight, GLOW)
    shade = (daylight.r, daylight.g, daylight.b)
    if shade in seen:
        lamps.append((index, daylight, nightfall, LAMPS[len(lamps) % len(LAMPS)]))
    else:
        walls.append((index, daylight, nightfall))
    seen.add(shade)

SPAN = (255 - DUSK) // (len(lamps) + 1)
lit_at = [DUSK + turn * SPAN for turn in range(len(lamps))]

frames = 0
lit_to = None
HALF = DAY_FRAMES // 2


def draw(canvas, _elapsed):
    global frames, lit_to
    place = frames % DAY_FRAMES
    darkness = place * 255 // HALF if place < HALF else (DAY_FRAMES - place) * 255 // HALF

    if darkness != lit_to:
        for index, daylight, nightfall in walls:
            palette[index] = color.mix(daylight, nightfall, darkness)
        for turn, (index, daylight, nightfall, lamp) in enumerate(lamps):
            unlit = color.mix(daylight, nightfall, darkness)
            since = darkness - lit_at[turn]
            palette[index] = unlit if since < 0 else color.mix(unlit, lamp,
                                                               min(255, since * 255 // SPAN))
        lit_to = darkness

    # The entry's offset and background are fixed, so the sky is filled and the city tiled
    # sideways by hand, two copies covering the wrap
    canvas.pen = sky_shades[darkness * (SKY_STEPS - 1) // 255]
    canvas.clear()
    across = -(frames * STEP % city.width)
    down = canvas.height - city.height
    while across < canvas.width:
        canvas.blit(city, across, down)
        across += city.width

    frames += 1
