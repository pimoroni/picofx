class EffectSettings:
    # The EffectSettings class stores all of the variables needed for a single mono LED.
    # First let's set up dome default values that we can fall back to if something goes
    # wrong or if there's missing data.

    default_values = {
        "type": 0,
        "brightness": 1,
        "dimness": 0.5,
        "speed": 1,
        "duty": 0.5,
        "phase": 0,
        "flashes": 2,
        "window": 0.5,
        "bright_min_time": 0.05,
        "bright_max_time": 0.1,
        "dim_min_time": 0.02,
        "dim_max_time": 0.04,
        "interval": 0.05,
        "red": 255,
        "green": 0,
        "blue": 0,
        "red2": None,
        "green2": None,
        "blue2": None
    }

    def __init__(self, type=1, brightness=1, dimness=0.5, speed=1, duty=0.5, phase=0, flashes=2, window=0.5, bright_min_time=0.05, bright_max_time=0.1, dim_min_time=0.02, dim_max_time=0.04, interval=0.05, red=255, green=0, blue=0, red2=None, green2=None, blue2=None):
        # We initialise with the passed in variables, which fall back to the same defaults as above.
        # If the type is a string (as with loading from the settings file),
        # use the lookup method below to convert it to the right int.
        if isinstance(type, str):
            self.type = self.parse_pretty_effect_type(type)
        else:
            self.type = type
        self.brightness = brightness
        self.dimness = dimness
        self.speed = speed
        self.duty = duty
        self.phase = phase
        self.flashes = flashes
        self.window = window
        self.bright_min_time = bright_min_time
        self.bright_max_time = bright_max_time
        self.dim_min_time = dim_min_time
        self.dim_max_time = dim_max_time
        self.interval = interval
        self.red = red
        self.green = green
        self.blue = blue
        self.red2 = red2
        self.green2 = green2
        self.blue2 = blue2
        self.dimmed = False

    def get_pretty_effect_type(self, effect_type):
        # Returns the effect type in words, for writing the settings file.

        if effect_type == 0:
            return "none"
        elif effect_type == 1:
            return "static"
        elif effect_type == 2:
            return "blink"
        elif effect_type == 3:
            return "flash"
        elif effect_type == 4:
            return "flicker"
        elif effect_type == 5:
            return "pulse"
        elif effect_type == 6:
            return "random"
        elif effect_type == 7:
            return "staticRGB"
        elif effect_type == 8:
            return "blinkRGB"
        elif effect_type == 9:
            return "flashRGB"
        elif effect_type == 10:
            return "flickerRGB"
        elif effect_type == 11:
            return "pulseRGB"
        elif effect_type == 12:
            return "randomRGB"

    def parse_pretty_effect_type(self, effect_type):
        # Returns an integer representing the effect type, for reading
        # the settings file. We're using ints rather than strings internally
        # since then we can easily cycle through them and loop around
        # just by incrementing.

        effect_type = effect_type.strip()
        if effect_type == "none":
            return 0
        elif effect_type == "static":
            return 1
        elif effect_type == "blink":
            return 2
        elif effect_type == "flash":
            return 3
        elif effect_type == "flicker":
            return 4
        elif effect_type == "pulse":
            return 5
        elif effect_type == "random":
            return 6
        elif effect_type == "staticRGB":
            return 7
        elif effect_type == "blinkRGB":
            return 8
        elif effect_type == "flashRGB":
            return 9
        elif effect_type == "flickerRGB":
            return 10
        elif effect_type == "pulseRGB":
            return 11
        elif effect_type == "randomRGB":
            return 12

    def dim(self):
        # If this channel's not already dimmed, divide all brightnesses by 5.
        # For dimming all the other channels when you're editing one.

        if not self.dimmed:
            self.brightness /= 5
            self.dimness /= 5
            self.dimmed = True

    def undim(self):
        # Same, but in reverse.

        if self.dimmed:
            self.brightness *= 5
            self.dimness *= 5
            self.dimmed = False

    def format_settings(self):
        # This returns a string containing all of the variables in field: value format,
        # with line breaks in between so we get a nice human-readable settings file.
        # It only adds variables relevant to the current effect type.
        # We're rolling our own settings format here rather than using json,
        # because micropython currently doesn't have functionality to write pretty
        # human-readable json.

        text = "type: " + self.get_pretty_effect_type(self.type) + "\n"
        # Before we do the brightness and dimness, we're also just checking to see if
        # we're dimmed, and compensating if we are.
        if self.type in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
            base_brightness = self.brightness
            if self.dimmed:
                base_brightness *= 5
            text += "brightness: " + str(base_brightness) + "\n"
        if self.type in (3, 5, 9, 11):
            base_dimness = self.dimness
            if self.dimmed:
                base_dimness *= 5
            text += "dimness: " + str(base_dimness) + "\n"
        if self.type in (2, 3, 5, 8, 9, 11):
            text += "speed: " + str(self.speed) + "\n"
        if self.type in (2, 3, 8, 9):
            text += "duty: " + str(self.duty) + "\n"
        if self.type in (2, 3, 5, 8, 9, 11):
            text += "phase: " + str(self.phase) + "\n"
        if self.type in (3, 9):
            text += "flashes: " + str(self.flashes) + "\n"
            text += "window: " + str(self.window) + "\n"
        if self.type in (4, 10):
            text += "bright_min_time: " + str(self.bright_min_time) + "\n"
            text += "bright_max_time: " + str(self.bright_max_time) + "\n"
            text += "dim_min_time: " + str(self.dim_min_time) + "\n"
            text += "dim_max_time: " + str(self.dim_max_time) + "\n"
        if self.type in (6, 12):
            text += "interval: " + str(self.interval) + "\n"
        if self.type in (7, 8, 9, 10, 11, 12):
            text += "red: " + str(self.red) + "\n"
            text += "green: " + str(self.green) + "\n"
            text += "blue: " + str(self.blue) + "\n"
        if self.type == 10:
            text += "red2: " + str(self.red2) + "\n"
            text += "green2: " + str(self.green2) + "\n"
            text += "blue2: " + str(self.blue2) + "\n"
        return text
