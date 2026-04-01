# Settings file for the TinyFX Controller.
#
#	~~~SETTINGS PARAMETERS~~~
#
# In the settings.txt file you can manually set parameters for each LED channel.
# There are six effects by default:
#
# static: Constantly lit.
# blink: Switches between lit and off regularly.
# flash: Flashes a set number of times, with a pause inbetween series of flashes.
# flicker: Jumps back and forth between a dim value and a bright value, with a random time interval in between.
# pulse: Pulses smoothly between zero and a set brightness.
# random: Jumps between random values between two set brightnesses.
# none: LED is off.
#
# If you're writing settings for the RGB LED, then you'll need to use the RGB versions of these -
# called staticRGB, blinkRGB etcetera.
#
# Not all of the effects use all of the parameters -
# if you specify a parameter that's not used for that effect,
# it will just be ignored. If you don't specify a parameter,
# a default value is used.
#
# Parameters (and which effects they're used in):
# All times are in seconds.
#
# type: 				As explained above.
# brightness: 			The overall maximum brightness. (static, blink, flash, flicker, pulse, random)
# dimness: 				The overall minimum brightness. (flicker, random)
# speed: 				The time for one loop of the effect. (blink, flash, pulse)
# duty: 				What proportion of the time is spent on vs. off. (blink, flash)
# phase: 				How 'in sync' the effect is with the others (blink, flash, pulse)
# flashes: 				How many times to flash (flash only)
# window: 				The time between groups of flashes. (flash only)
# bright_min_time: 		The minimum time to stay bright (flicker only)
# bright_max_time: 		The maximum time to stay bright (flicker only)
# dim_min_time: 		The minimum time to stay dim (flicker only)
# dim_max_time: 		The maximum time to stay dim (flicker only)
# interval: 			The time before jumping to a new value (random only)
# red, green, blue:		The colour of the LED, as 1-255 values (RGB only)
# red2, green2, blue2:	The colour of the LED during the dim periods of flicker, as 1-255 values (flickerRGB only)
#
# ~~~REMOTE CONTROLS~~~
#
# In its normal state, the remote simply allows you to mute each channel
# by pressing its corresponding number button. Pressing 0 will mute the RGB LED.
#
# By pressing the Action button (the one with the three dots), you can cycle between normal running,
# Mono Edit mode and RGB Edit mode. The other LEDs will dim to make it easier to work.
#
# In Mono Edit mode, if you press the top left and top right "rainbow" buttons you can switch between
# changing the settings for each channel. The other channels will dim to show you
# which one's selected.
#
# There are some controls which are common to all of the effects:
#
# Stop / OK: Cycles therough the available effects for that channel.
# Up & Down: Controls the brightness. In effects that jump between a range of brightnesses, this is the highest one.
# Left & Right: Controls the overall speed of the effect.
# Clockwise & Anticlockwise (rainbow buttons): Cycles the colour of the LED. RGB Edit mode only.
#
# The number buttons are used for different things depending on the selected effect:
#
# static:
#	None
# blink:
#	1 & 4 adjust the phase of the effect.
#	2 & 5 adjust the duty cycle of the effect.
# flash:
#	1 & 4 adjust the phase of the effect.
#	2 & 5 adjust the duty cycle of the flashes.
#	3 & 6 adjust the window for the flashes.
#	7 & 9 adjust the number of flashes.
# flicker:
#	1 & 4 adjust the chaos of the effect - how much variation the on and off periods can have.
#	2 & 5 adjust the duty cycle of the effect.
#	3 & 6 adjust the brightness of the dim periods of the flicker.
#	0 cycles through a second colour which you can set for the dim periods.
# pulse:
#	1 & 4 adjust the phase of the effect.
# random:
#	1 & 4 adjust the minimum brightness for the random value.
#
# At any point you can press the Record button on the remote to save your configuration.