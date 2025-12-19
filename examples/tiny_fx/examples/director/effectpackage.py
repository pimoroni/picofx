from effectsettings import EffectSettings
from picofx.mono import StaticFX, BlinkFX, FlashFX, FlickerFX, PulseFX, RandomFX, NoneFX
from picofx.colour import StaticRGBFX, BlinkRGBFX, FlashRGBFX, FlickerRGBFX, PulseRGBFX, RandomRGBFX

class EffectPackage:
    # The EffectPackage class mainly keeps all the methods all together which adjust the effect.
    # It holds a list of EffectSettings objects, one for each channel, and this should
    # initialise to have one member for each output on the device.
    def __init__(self, board, colour, num_outputs):
        # First we load in everything from the settings file.
        self.colour = colour
        loaded_settings = self.load_settings()
        # Then we create a new entry for each output on the board,
        # using the imported settings if they're there and making a
        # fresh new EffectSettings with default values if not.
        self.channel_settings = []
        
        for i in range(num_outputs):
            if len(loaded_settings) > 0:
                new_effect = loaded_settings.pop(0)
                self.channel_settings.append(new_effect)
            else:
                self.channel_settings.append(EffectSettings())

    def load_settings(self):
        new_settings = []
        # To load the settings we first open the file...
        with open("settings.txt", "r") as settingsfile:
            # ...then loop through reading each line in turn.
            while True:
                line = settingsfile.readline()
                # If the line is empty stop reading, it's the end of the file.
                if line == "":
                    break
                # If it begins with a #, then it's a comment, just ignore it.
                if line[0] == "#":
                    continue
                # If the line begins with "Mono" or "RGB" as specified in the colour
                # parameter, then we start a new internal loop to
                # populate values into a new instance of EffectSettings.
                
                if line.split(" ")[0] == self.colour:
                    type = EffectSettings.default_values["type"]
                    brightness = EffectSettings.default_values["brightness"]
                    dimness = EffectSettings.default_values["dimness"]
                    speed = EffectSettings.default_values["speed"]
                    duty = EffectSettings.default_values["duty"]
                    phase = EffectSettings.default_values["phase"]
                    flashes = EffectSettings.default_values["flashes"]
                    window = EffectSettings.default_values["window"]
                    bright_min_time = EffectSettings.default_values["bright_min_time"]
                    bright_max_time = EffectSettings.default_values["bright_max_time"]
                    dim_min_time = EffectSettings.default_values["dim_min_time"]
                    dim_max_time = EffectSettings.default_values["dim_max_time"]
                    interval = EffectSettings.default_values["interval"]
                    red = EffectSettings.default_values["red"]
                    green = EffectSettings.default_values["green"]
                    blue = EffectSettings.default_values["blue"]
                    red2 = EffectSettings.default_values["red2"]
                    green2 = EffectSettings.default_values["green2"]
                    blue2 = EffectSettings.default_values["blue2"]

                    # We loop through again, still reading lines from the settings file,
                    # busting out to the outer loop if we see a comment, which signifies the end of that channel's data.
                    while True:
                        setting = settingsfile.readline()
                        if setting == "":
                            break
                        if setting[0] == "#":
                            break

                        # Split the line into the field and value
                        field, value = setting.split(": ")

                        # Here we're catching any fields that need to be a float or an int,
                        # and converting them. If there's a problem converting them, just
                        # use the default value from the EffectSettings class.
                        if field in ("brightness", "dimness", "speed", "duty", "phase", "window", "bright_min_time", "bright_max_time", "dim_min_time", "dim_max_time", "interval"):
                            try:
                                value = float(value)
                            except:
                                value = EffectSettings.default_values[field]

                        elif field in ("flashes", "red", "green", "blue", "red2", "green2", "blue2"):
                            try:
                                value = int(value)
                            except:
                                value = EffectSettings.default_values[field]

                        # Now we just use a series of checks to assign that value to the right variable created above.
                        if field == "type":
                            type = value
                        elif field == "brightness":
                            brightness = value
                        elif field == "dimness":
                            dimness = value
                        elif field == "speed":
                            speed = value
                        elif field == "duty":
                            duty = value
                        elif field == "phase":
                            phase = value
                        elif field == "flashes":
                            flashes = value
                        elif field == "window":
                            window = value
                        elif field == "bright_min_time":
                            bright_min_time = value
                        elif field == "bright_max_time":
                            bright_max_time = value
                        elif field == "dim_min_time":
                            dim_min_time = value
                        elif field == "dim_max_time":
                            dim_max_time = value
                        elif field == "interval":
                            interval = value
                        elif field == "red":
                            red = value
                        elif field == "green":
                            green = value
                        elif field == "blue":
                            blue = value
                        elif field == "red2":
                            red2 = value
                        elif field == "green2":
                            green2 = value
                        elif field == "blue2":
                            blue2 = value

                    # Then finally we put all those variables into a new EffectSettings
                    # instance, and add it to our list of channels before going on to
                    # look for the next channel's data.
                    new_settings.append(EffectSettings(type, brightness, dimness, speed, duty, phase, flashes, window, bright_min_time, bright_max_time, dim_min_time, dim_max_time, interval, red, green, blue, red2, green2, blue2))
                else:
                    continue
        return new_settings

    def save_settings(self):
        # We just go through every channel in our channel list, asking the
        # EffectSettings instance to spit out the formatted string to add.
        text = ""
        for i in range(len(self.channel_settings)):
            if self.channel_settings[i].type < 7:
                text += "Mono " + str(i + 1) + "\n"
            else:
                text += "RGB " + str(i + 1) + "\n"
            text += self.channel_settings[i].format_settings()
            text += "#\n"
        return text

    def update_effects_list(self, player):
        # Updating the effect list takes all the settings data from our channel list,
        # and creates a new list of effects for the player to use.
        # We can't just update the ones that are already in there because they're held
        # internally as a tuple and so can't be swapped out, we have to provide it
        # with a new full list.

        new_list = []

        # So we loop through each channel, check what type it is, and create the appropriate
        # class with the settings taken from the EffectSettings.
        for effect_settings in self.channel_settings:
            if effect_settings.type == 1:
                new_effect = StaticFX(
                    effect_settings.brightness
                )
            elif effect_settings.type == 2:
                new_effect = BlinkFX(
                    effect_settings.speed,
                    effect_settings.phase,
                    effect_settings.duty,
                    effect_settings.brightness
                )
            elif effect_settings.type == 3:
                new_effect = FlashFX(
                    effect_settings.speed,
                    effect_settings.flashes,
                    effect_settings.window,
                    effect_settings.phase,
                    effect_settings.duty,
                    effect_settings.brightness
                )
            elif effect_settings.type == 4:
                new_effect = FlickerFX(
                    effect_settings.brightness,
                    effect_settings.dimness,
                    effect_settings.bright_min_time,
                    effect_settings.bright_max_time,
                    effect_settings.dim_min_time,
                    effect_settings.dim_max_time
                )
            elif effect_settings.type == 5:
                new_effect = PulseFX(
                    effect_settings.speed,
                    effect_settings.phase,
                    effect_settings.brightness
                )
            elif effect_settings.type == 6:
                new_effect = RandomFX(
                    effect_settings.interval,
                    effect_settings.brightness,
                    effect_settings.dimness
                )
            elif effect_settings.type == 7:
                new_effect = StaticRGBFX(
                    effect_settings.brightness,
                    effect_settings.red,
                    effect_settings.green,
                    effect_settings.blue
                )
            elif effect_settings.type == 8:
                new_effect = BlinkRGBFX(
                    effect_settings.speed,
                    effect_settings.phase,
                    effect_settings.duty,
                    effect_settings.brightness,
                    effect_settings.red,
                    effect_settings.green,
                    effect_settings.blue
                )
            elif effect_settings.type == 9:
                new_effect = FlashRGBFX(
                    effect_settings.speed,
                    effect_settings.flashes,
                    effect_settings.window,
                    effect_settings.phase,
                    effect_settings.duty,
                    effect_settings.brightness,
                    effect_settings.red,
                    effect_settings.green,
                    effect_settings.blue
                )
            elif effect_settings.type == 10:
                new_effect = FlickerRGBFX(
                    effect_settings.brightness,
                    effect_settings.dimness,
                    effect_settings.bright_min_time,
                    effect_settings.bright_max_time,
                    effect_settings.dim_min_time,
                    effect_settings.dim_max_time,
                    effect_settings.red,
                    effect_settings.green,
                    effect_settings.blue,
                    effect_settings.red2,
                    effect_settings.green2,
                    effect_settings.blue2
                )
            elif effect_settings.type == 11:
                new_effect = PulseRGBFX(
                    effect_settings.speed,
                    effect_settings.phase,
                    effect_settings.brightness,
                    effect_settings.red,
                    effect_settings.green,
                    effect_settings.blue
                )
            elif effect_settings.type == 12:
                new_effect = RandomRGBFX(
                    effect_settings.interval,
                    effect_settings.brightness,
                    effect_settings.dimness,
                    effect_settings.red,
                    effect_settings.green,
                    effect_settings.blue
                )
            else:
                new_effect = NoneFX()

            new_list.append(new_effect)

        player.effects = new_list

    def clamp(self, n, smallest, largest):
        # Simple function to clamp a number between two set values.
        return max(smallest, min(n, largest))

    def cycle_fx(self, channel, player):
        # To change effect within a provided channel, we just
        # pull the right EffectSettings from the list, get its current type
        # and add one, looping around to zero if necessary.
        # Then write that new effect type to the EffectSettings.
        if self.colour == "Mono":
            valid_effects = (0, 1, 2, 3, 4, 5, 6)
        elif self.colour == "RGB":
            valid_effects = (0, 7, 8, 9, 10, 11, 12)
        
        effect = self.channel_settings[channel - 1]
        old_effect_type = effect.type
        new_effect_type = (old_effect_type + 1) % 13
        while new_effect_type not in valid_effects:
            new_effect_type = (new_effect_type + 1) % 13
        effect.type = new_effect_type

    def alter_brightness(self, channel, amount, player):
        # Several of these work the same way, just pulling the
        # EffectSettings and altering a value.
        # We could just change it directly, but we're working
        # this way to remain consistent with the times where
        # we're doing more complex things.
        effect = self.channel_settings[channel - 1]

        # This is a just in case thing, but we don't want to change
        # settings on something that's dimmed due to not being the selected channel.
        # If it comes up then something's gone wrong, but it's still good to be safe.
        if effect.dimmed:
            return

        old_brightness = effect.brightness
        new_brightness = self.clamp(old_brightness + amount, 0, 1)
        effect.brightness = new_brightness

    def alter_speed(self, channel, amount, player):
        # Changing the speed is basically the same process as above, but it works differently
        # on different effects.

        effect = self.channel_settings[channel - 1]

        # static and none effects don't have a speed, so we can just return.
        if effect.type in (0, 1, 7):
            return

        # blink, flash and pulse all have a simple speed factor we can change directly.
        if effect.type in (2, 3, 5, 8, 9, 11):
            old_speed = effect.speed
            new_speed = old_speed + amount
            effect.speed = new_speed

        # random instead uses the time between switching to the next random value,
        # so we'll convert the adjustment amount to something sensible and also subtract it
        # rather than add it, as an increased adjustment wants to lead to a shorter interval between changes.
        elif effect.type in (6, 12):
            old_speed = effect.interval
            new_speed = old_speed - (amount / 5)
            new_speed = self.clamp(new_speed, 0, 5)
            effect.interval = new_speed

        # Finally flicker works similarly to random, but there's several different
        # values to change, and we want to slide them all up and down the scale
        # without changing their relationship to each other.
        elif effect.type in (4, 10):
            old_bmin = effect.bright_min_time
            old_bmax = effect.bright_max_time
            old_dmin = effect.dim_min_time
            old_dmax = effect.dim_max_time

            new_bmin = old_bmin - (amount / 5)
            new_bmax = old_bmax - (amount / 5)
            new_dmin = old_dmin - (amount / 5)
            new_dmax = old_dmax - (amount / 5)

            new_bmin = self.clamp(new_bmin, 0, 5)
            new_bmax = self.clamp(new_bmax, 0, 5)
            new_dmin = self.clamp(new_dmin, 0, 5)
            new_dmax = self.clamp(new_dmax, 0, 5)

            effect.bright_min_time = new_bmin
            effect.bright_max_time = new_bmax
            effect.dim_min_time = new_dmin
            effect.dim_max_time = new_dmax

    def alter_duty(self, channel, amount):
        # Duty is like speed, it's different for different effects.

        effect = self.channel_settings[channel - 1]

        if effect.type in (0, 1, 5, 6, 7, 11, 12):
            return

        # If it's blink or flash it's changed simply.
        if effect.type in (2, 3, 8, 9):
            old_duty = effect.duty
            new_duty = self.clamp(old_duty + amount, 0, 1)
            effect.duty = new_duty

        # If it's flicker it's harder, because we want to increase one timing
        # and decrease the other, by a sensible amount, and keep them so that
        # on average a full cycle still takes the same amount of time, just with
        # different proportions of bright and dim.
        elif effect.type in (4, 10):
            # Get the existing values.
            old_bmin = effect.bright_min_time
            old_bmax = effect.bright_max_time
            old_dmin = effect.dim_min_time
            old_dmax = effect.dim_max_time

            # Calculate the average time for the bright and dim cycles.
            old_bright_centre = (old_bmin + old_bmax) / 2
            old_dim_centre = (old_dmin + old_dmax) / 2

            # Work out on average how long a cycle takes...
            duty_total_time = old_bright_centre + old_dim_centre

            # ...scale the amount by this much so that it works out normalised between 0 and 1...
            scaled_duty_change = amount / duty_total_time

            # ...then push the bright and dim values in opposite directions to each other.
            # This means that on average a cycle of on / off still takes the same amount of time,
            # but changing the timings so it has the same effect as on those with a simple duty cycle.
            new_bmin = old_bmin + scaled_duty_change
            new_bmax = old_bmax + scaled_duty_change
            new_dmin = old_dmin - scaled_duty_change
            new_dmax = old_dmax - scaled_duty_change

            new_bmin = self.clamp(new_bmin, 0, 5)
            new_bmax = self.clamp(new_bmax, 0, 5)
            new_dmin = self.clamp(new_dmin, 0, 5)
            new_dmax = self.clamp(new_dmax, 0, 5)

            effect.bright_min_time = new_bmin
            effect.bright_max_time = new_bmax
            effect.dim_min_time = new_dmin
            effect.dim_max_time = new_dmax

    def alter_phase(self, channel, amount):
        # Changing phase is another simple one for those effects that use it.
        effect = self.channel_settings[channel - 1]

        if effect.type in (0, 1, 4, 6, 7, 10, 12):
            return

        old_phase = effect.phase
        new_phase = self.clamp(old_phase + amount, 0, 1)
        effect.phase = new_phase

    def alter_flashes(self, channel, amount):
        # Same with number of flashes...
        effect = self.channel_settings[channel - 1]

        if effect.type in (0, 1, 2, 4, 5, 6, 7, 8, 10, 11, 12):
            return

        old_flashes = effect.flashes
        new_flashes = self.clamp(old_flashes + amount, 1, 99)
        effect.flashes = new_flashes

    def alter_window(self, channel, amount):
        # ...and window...
        effect = self.channel_settings[channel - 1]

        if effect.type in (0, 1, 2, 4, 5, 6, 7, 8, 10, 11, 12):
            return

        old_window = effect.window
        new_window = self.clamp(old_window + amount, 0, 5)
        effect.window = new_window

    def alter_dimness(self, channel, amount):
        # ...and dimness.
        effect = self.channel_settings[channel - 1]

        if effect.type in (0, 1, 2, 3, 5, 7, 8, 9, 11):
            return

        old_dimness = effect.dimness
        new_dimness = self.clamp(old_dimness + amount, 0, 1)
        effect.dimness = new_dimness

    def alter_chaos(self, channel, amount):
        # Chaos level for the flicker effect is adjusted by increasing the gap
        # between the maximum and mininum time it can pick for on and off periods.
        # So we're just adjusting the maxes in one direction and the mins in the other,
        # by the same amount so the average bright or dim period stays the same, just with
        # more variation.
        effect = self.channel_settings[channel - 1]

        if effect.type in (0, 1, 2, 3, 5, 6, 7, 8, 9, 11, 12):
            return

        old_bmin = effect.bright_min_time
        old_bmax = effect.bright_max_time
        old_dmin = effect.dim_min_time
        old_dmax = effect.dim_max_time

        new_bmin = old_bmin - (amount / 5)
        new_bmax = old_bmax + (amount / 5)
        new_dmin = old_dmin - (amount / 5)
        new_dmax = old_dmax + (amount / 5)

        new_bmin = self.clamp(new_bmin, 0, 5)
        new_bmax = self.clamp(new_bmax, 0, 5)
        new_dmin = self.clamp(new_dmin, 0, 5)
        new_dmax = self.clamp(new_dmax, 0, 5)

        effect.bright_min_time = new_bmin
        effect.bright_max_time = new_bmax
        effect.dim_min_time = new_dmin
        effect.dim_max_time = new_dmax
        
    def alter_hue(self, channel, amount):
        effect = self.channel_settings[channel - 1]

        if effect.type in (0, 1, 2, 3, 4, 5, 6):
            return
        
        red = effect.red
        green = effect.green
        blue = effect.blue
        
        if red == 255 and not green == 255 and blue == 0:
            green += amount
        elif not red == 0 and green == 255 and blue == 0:
            red -= amount
        elif red == 0 and green == 255 and not blue == 255:
            blue += amount
        elif red == 0 and not green == 0 and blue == 255:
            green -= amount
        elif not red == 255 and green == 0 and blue == 255:
            red += amount
        elif red == 255 and green == 0 and not blue == 0:
            blue -= amount
            
        effect.red = self.clamp(red, 0, 255)
        effect.green = self.clamp(green, 0, 255)
        effect.blue = self.clamp(blue, 0, 255)
        
        print(effect.red, effect.green, effect.blue)
        
    def alter_hue2(self, channel, amount):
        effect = self.channel_settings[channel - 1]

        if effect.type in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12):
            return
        
        if None in (effect.red2, effect.green2, effect.blue2):
            red = effect.red
            green = effect.green
            blue = effect.blue
        else:
            red = effect.red2
            green = effect.green2
            blue = effect.blue2
        
        if red == 255 and not green == 255 and blue == 0:
            green += amount
        elif not red == 0 and green == 255 and blue == 0:
            red -= amount
        elif red == 0 and green == 255 and not blue == 255:
            blue += amount
        elif red == 0 and not green == 0 and blue == 255:
            green -= amount
        elif not red == 255 and green == 0 and blue == 255:
            red += amount
        elif red == 255 and green == 0 and not blue == 0:
            blue -= amount
            
        effect.red2 = self.clamp(red, 0, 255)
        effect.green2 = self.clamp(green, 0, 255)
        effect.blue2 = self.clamp(blue, 0, 255)
        
        print(effect.red2, effect.green2, effect.blue2)