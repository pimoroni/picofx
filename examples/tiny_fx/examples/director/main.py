from tiny_fx import TinyFX
from picofx import MonoPlayer, ColourPlayer
from aye_arr.nec import NECReceiver
from aye_arr.nec.remotes import PimoroniRemote
from effectpackage import EffectPackage
from picofx.mono import NoneFX


"""
Press "Boot" to exit the program.
"""

# Variables
tiny = TinyFX()                          # Create a new TinyFX object to interact with the board
monoplayer = MonoPlayer(tiny.outputs)    # Create a new effect player to control TinyFX's mono outputs
rgbplayer = ColourPlayer(tiny.rgb)       # Create a new effect player to control TinyFX's RGB output
mono_effects = EffectPackage("Mono", 6)  # Create a new EffectPackage to take care of all the different effect settings for each mono channel.
rgb_effects = EffectPackage("RGB", 1)    # Create a new EffectPackage to take care of all the different effect settings for the RGB channel.
mono_channel = 1
run_mode = 0


class Mode:
    Running = 0
    Mono = 1
    RGB = 2


def rotate(dir, repeat):
    # If the TinyFX is just running this button doesn't do anything.
    if run_mode == Mode.Running:
        return

    # However, if we're in RGB editing mode then we're altering the hue.
    if run_mode == Mode.RGB:
        rgb_effects.alter_hue(0, dir * 5)
        rgb_effects.update_effects_list(rgbplayer)

    # And if we're in mono editing mode this selects the channel.
    # Selecting a channel just involves incrementing or decrementing the selected_channel variable,
    # looping it round if it goes above the total number of channels or below zero.
    elif run_mode == Mode.Mono and not repeat:
        global mono_channel

        mono_channel += dir
        if mono_channel > len(mono_effects.channel_settings):
            mono_channel = 1
        if mono_channel < 1:
            mono_channel = len(mono_effects.channel_settings)

        # Then we just loop through each channel and undim it if it's the selected
        # channel or dim it if it's not.
        for i in range(len(mono_effects.channel_settings)):
            effect = mono_effects.channel_settings[i]
            if mono_channel == i + 1:
                effect.undim()
            else:
                effect.dim()

        # Calling this is important when any changes are made. It takes the settings data from the
        # channel settings and actually applies them to the player class.
        mono_effects.update_effects_list(monoplayer)


def toggle_mono(channel=0):
    # This controls the quick mute for each channel. It goes straight into the
    # player and sets the brightness to zero, or to whatever's in the
    # settings for that channel if it's already at zero.

    if channel > 0:
        effect = monoplayer.effects[channel - 1]
        old_brightness = mono_effects.channel_settings[channel - 1].brightness

    else:
        effect = rgbplayer.effects[0]
        old_brightness = rgb_effects.channel_settings[channel - 1].brightness

    if isinstance(effect, NoneFX):
        return

    if effect.brightness > 0.0:
        effect.brightness = 0.0
    else:
        brightness = old_brightness
        effect.brightness = brightness


def saving_handler():
    # Saving is simpler than loading, first we put in a bit of text directing the user to the instructions:
    text = "# SETTINGS FILE\n#\n# For instructions, check readme.txt\n#\n"

    # Then add in each channel's settings.
    text += mono_effects.save_settings()
    text += rgb_effects.save_settings()

    # Finally save the file.
    with open("settings.txt", "w") as settingsfile:
        settingsfile.write(text)


def mode_handler():
    # Here we're just switching between the running mode, mono editing mode and
    # RGB editing mode.
    global run_mode

    run_mode += 1
    if run_mode > 2:
        run_mode = 0

    # That's the actual switch done, the rest just dims or brightens LEDs
    # appropriately for the current mode.
    if run_mode == Mode.Running:
        for i in range(len(mono_effects.channel_settings)):
            mono_effects.channel_settings[i].undim()
        rgb_effects.channel_settings[0].undim()
    elif run_mode == Mode.Mono:
        for i in range(len(mono_effects.channel_settings)):
            effect = mono_effects.channel_settings[i]
            if mono_channel == i + 1:
                effect.undim()
            else:
                effect.dim()
        rgb_effects.channel_settings[0].dim()
    elif run_mode == Mode.RGB:
        for i in range(len(mono_effects.channel_settings)):
            mono_effects.channel_settings[i].dim()
        rgb_effects.channel_settings[0].undim()

    mono_effects.update_effects_list(monoplayer)
    rgb_effects.update_effects_list(rgbplayer)


def common_handler(button):
    # This handles presses on the buttons common to all effect types.
    # It gets passed which button was pressed and depending on which it was,
    # alters that channels settings in various ways.

    # We can't do this in the bindings for the remote control buttons below,
    # because once they're set they're set so they'd always apply to whichever channel
    # was selected when they were set up. Instead they call this which can
    # pass up to date data to the methods.

    if run_mode == Mode.Running:
        return

    if run_mode == Mode.Mono:
        player = monoplayer
        effects = mono_effects
        selected_channel = mono_channel

    if run_mode == Mode.RGB:
        player = rgbplayer
        effects = rgb_effects
        selected_channel = 0

    if button == "UP":
        effects.alter_brightness(selected_channel, 0.03, player)
    if button == "DOWN":
        effects.alter_brightness(selected_channel, -0.03, player)
    if button == "OK/STOP":
        effects.cycle_fx(selected_channel, player)
    elif button == "RIGHT":
        effects.alter_speed(selected_channel, 0.03, player)
    elif button == "LEFT":
        effects.alter_speed(selected_channel, -0.03, player)

    effects.update_effects_list(player)


def number_handler(number_button, repeat):
    # This is very similar to the handler above, but for the number buttons.
    # It's a series of checks which looks at both which button was pressed, as well as
    # what the effect type is on the current channel, and then takes action accordingly.
    # It also checks whether it's a press or a hold (which just repeats a press over and
    # over), so that we can respond differently to it.

    if run_mode == Mode.Running:
        if not repeat:
            toggle_mono(number_button)
            return

    else:
        if run_mode == Mode.Mono:
            player = monoplayer
            selected_channel = mono_channel
            effects = mono_effects
            effect = effects.channel_settings[selected_channel - 1]

        elif run_mode == Mode.RGB:
            player = rgbplayer
            selected_channel = 0
            effects = rgb_effects
            effect = effects.channel_settings[0]

        if effect.type in (0, 1, 7):
            return

        elif number_button == 1:
            if effect.type in (2, 3, 5, 8, 9, 11):
                effects.alter_phase(selected_channel, 0.03)
            elif effect.type in (4, 10):
                effects.alter_chaos(selected_channel, 0.03)
            elif effect.type in (6, 12):
                effects.alter_dimness(selected_channel, 0.03)

        elif number_button == 2:
            if effect.type in (2, 3, 4, 8, 9, 10):
                effects.alter_duty(selected_channel, 0.03)

        elif number_button == 3:
            if effect.type in (3, 9):
                effects.alter_window(selected_channel, 0.03)
            elif effect.type in (4, 10):
                effects.alter_dimness(selected_channel, 0.03)

        elif number_button == 4:
            if effect.type in (2, 3, 5, 8, 9, 11):
                effects.alter_phase(selected_channel, -0.03)
            elif effect.type in (4, 10):
                effects.alter_chaos(selected_channel, -0.03)
            elif effect.type in (5, 11):
                effects.alter_dimness(selected_channel, -0.03)

        elif number_button == 5:
            if effect.type in (2, 3, 4, 8, 9, 10):
                effects.alter_duty(selected_channel, -0.03)

        elif number_button == 6:
            if effect.type in (3, 9):
                effects.alter_window(selected_channel, -0.03)
            elif effect.type in (4, 10):
                effects.alter_dimness(selected_channel, -0.03)

        elif number_button == 7:
            if effect.type in (3, 9) and not repeat:
                effects.alter_flashes(selected_channel, -1)

        elif number_button == 9:
            if effect.type in (3, 9) and not repeat:
                effects.alter_flashes(selected_channel, 1)

        elif number_button == 0:
            if effect.type == 10:
                effects.alter_hue2(0, 5)

        effects.update_effects_list(player)


# Now we've defined all of the methods we're passing all our settings to the player for the first time.
mono_effects.update_effects_list(monoplayer)
rgb_effects.update_effects_list(rgbplayer)

# Set up the IR receiver on GP26, using PIO 1 and SM 0
receiver = NECReceiver(TinyFX.SENSOR_PIN, 1, 0)

# This binds functions to each of the Pimoroni remote's buttons for what happens when they're pressed, and when they're held.
# For the most part they're set to pass to a handler for the reasons mentioned above.
remote = PimoroniRemote()
remote.bind("CLOCKWISE", (rotate, 1, False), on_repeat=(rotate, 1, True))
remote.bind("ANTICLOCK", (rotate, -1, False), on_repeat=(rotate, -1, True))
remote.bind("MENU/ACTION", (mode_handler), on_repeat=None)
remote.bind("1/RED", (number_handler, 1, False), on_repeat=(number_handler, 1, True))
remote.bind("2/GREEN", (number_handler, 2, False), on_repeat=(number_handler, 2, True))
remote.bind("3/BLUE", (number_handler, 3, False), on_repeat=(number_handler, 3, True))
remote.bind("4/CYAN", (number_handler, 4, False), on_repeat=(number_handler, 4, True))
remote.bind("5/MAGENTA", (number_handler, 5, False), on_repeat=(number_handler, 5, True))
remote.bind("6/YELLOW", (number_handler, 6, False), on_repeat=(number_handler, 6, True))
remote.bind("7/WARM", (number_handler, 7, False), on_repeat=(number_handler, 7, True))
remote.bind("9/COOL", (number_handler, 9, False), on_repeat=(number_handler, 9, True))
remote.bind("0/RAINBOW", (number_handler, 0, False), on_repeat=(number_handler, 0, True))
remote.bind("UP", (common_handler, "UP"), on_repeat=(common_handler, "UP"))
remote.bind("DOWN", (common_handler, "DOWN"), on_repeat=(common_handler, "DOWN"))
remote.bind("OK/STOP", (common_handler, "OK/STOP"), on_repeat=None)
remote.bind("RIGHT", (common_handler, "RIGHT"), on_repeat=(common_handler, "RIGHT"))
remote.bind("LEFT", (common_handler, "LEFT"), on_repeat=(common_handler, "LEFT"))
remote.bind("RECORD", (saving_handler), on_repeat=None)

receiver.bind(remote)

# Finally we start the whole thing going.
# We wrap the code in a try block, to catch any exceptions.
try:
    # We start the IR receiver going, and the effects running...
    receiver.start()
    monoplayer.start()
    rgbplayer.start()

    # ...and then loop until the effect stops or the "Boot" button is pressed.
    while not tiny.boot_pressed():
        receiver.decode()

# Stop any running effects and turn off all the outputs
finally:
    receiver.stop()
    monoplayer.stop()
    rgbplayer.stop()
    tiny.shutdown()
