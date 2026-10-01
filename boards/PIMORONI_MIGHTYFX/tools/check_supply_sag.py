# Measures how far the board's supply falls as the outputs are lit, which is the
# figure a brown-out derate works from. Reports volts against PWM duty, duty being
# what the supply sees where the outputs are gamma corrected, and then against the
# number of outputs lit, which says whether the fall is linear in the load.
#
# Run it on USB and again on battery. Nothing regulates the supply, so the two start
# from different voltages and need not fall alike.
#
# The outputs are the only load it applies. The connector rail, the amplifier and a
# screen's backlight all draw from the same supply, so a real scene falls further
# than this.
#
# A diagnostic, not an example, so it is not copied to the board. Run it with
# mpremote.

import time

from machine import ADC, Pin
from mighty_fx import MightyFX
from picofx import PWMLED

# Readings per measurement. The outputs are driven by PWM, so this has to cover
# several periods or the average carries wherever in the ripple it happened to start.
SAMPLES = 2000

# After a change, before measuring. The supply's bulk capacitance takes time to reach
# its new level.
SETTLE_MS = 200

# After a load comes off, before taking an idle. A battery recovers over seconds, far
# longer than the capacitance does, and a sweep measured too soon reads the recovery
# as load.
RECOVER_MS = 5000

# Whether the outputs are walked. Off measures a connector's load against a rested
# pack, the output walks otherwise leaving it partway through recovering.
WALK_OUTPUTS = True

# The fractions of full current the outputs are walked through
DUTIES = (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0)

# Above this the supply can only be USB, no battery pack the board takes reaching it
USB_VOLTS = 4.7

# LEDs per connector for the strip walk, 0 to skip it and measure the outputs alone
STRIP_LEDS = 64

# Lit at full white, the one value a strip's gamma table passes through unchanged. The
# table is applied inside the driver with no way to decline it, and it sends everything
# below 22 to zero, so a walk at a low value measures dark panels. Full panels at full
# white draw far more than the connector is rated for, so only the few below are lit.
STRIP_VALUE = 255

# LEDs per panel to walk. Eight at full white across the two is inside half an amp even
# if every LED is a 60mA part, which is the worst case the connector has to survive.
STRIP_LIT = (0, 1, 2, 3, 4)

# Blank everything and stop, whatever a walk has left to do. The board has been seen
# running at 3.29V, so this sits below that and not at the regulator's nominal.
ABORT_VOLTS = 3.1

# Nothing beyond the outputs and the strips is built, so the load measured is theirs
mighty = MightyFX(init_i2c=False, init_wav=False,
                  strip_l=STRIP_LEDS or None, strip_r=STRIP_LEDS or None)
strips = (mighty.strip_l, mighty.strip_r) if STRIP_LEDS else ()

# The divider is read here instead of through the board, so the figures are the pin's
# and do not carry whatever correction a library generation applies on top
v_sense = ADC(Pin(MightyFX.V_SENSE_PIN))


def light(duty):
    """Drive every channel to a known duty, undoing the gamma the outputs apply."""
    level = duty ** (1 / mighty.RGB_GAMMA)
    for led in mighty.monos:
        led.brightness(level)


def supply():
    """The supply at the sense divider, in volts, averaged over SAMPLES readings."""
    total = 0
    for _ in range(SAMPLES):
        total += v_sense.read_u16()

    return (total / SAMPLES) * 3.3 * MightyFX.V_SENSE_GAIN / 65535


def light_strips(lit):
    """Light the first `lit` LEDs of both panels to STRIP_VALUE, and the rest not at all."""
    for strip in strips:
        for index in range(STRIP_LEDS):
            value = STRIP_VALUE if index < lit else 0
            strip.set_rgb(index, value, value, value)
        strip.update()


def settled():
    """The supply once the load has had time to show, in volts."""
    time.sleep_ms(SETTLE_MS)
    return supply()


try:
    light(0.0)
    time.sleep_ms(SETTLE_MS)

    started = time.ticks_us()
    idle = supply()
    reading_us = time.ticks_diff(time.ticks_us(), started)

    print("idle {:.3f}V, on {}".format(idle, "USB" if idle > USB_VOLTS else "battery"))
    print("a reading is {} samples over {}us, {:.1f} PWM periods".format(
        SAMPLES, reading_us, reading_us * PWMLED.FREQUENCY / 1_000_000))
    print()

    if WALK_OUTPUTS:
        print("every output, walked by duty")
        print(" duty   volts      fall")
        for duty in DUTIES:
            light(duty)
            volts = settled()
            print("{:5.3f}  {:6.3f}  {:6.0f}mV".format(duty, volts, (idle - volts) * 1000))

        # A battery is lower for having been loaded and comes back slowly, so the second
        # sweep is measured against its own idle. Against the first it would read the
        # recovery as load.
        light(0.0)
        time.sleep_ms(RECOVER_MS)
        rested = settled()
        full = None

        print()
        print("outputs at full white, one at a time, against an idle of {:.3f}V".format(rested))
        print("  lit   volts      fall")
        for count in range(len(mighty.outputs) + 1):
            for index, output in enumerate(mighty.outputs):
                if index < count:
                    output.on()
                else:
                    output.off()

            volts = settled()
            if count == len(mighty.outputs):
                full = volts
            print("{:5d}  {:6.3f}  {:6.0f}mV".format(count, volts, (rested - volts) * 1000))

        for output in mighty.outputs:
            output.off()

        print()
        print("fall at full white {:.0f}mV, {:.0f}mV per output".format(
            (rested - full) * 1000, (rested - full) * 1000 / len(mighty.outputs)))

    if STRIP_LEDS:
        # Powering the panels is measured on its own. A pack loaded a moment ago is
        # still climbing back, and read too soon that recovery counts as the panels.
        light_strips(0)
        time.sleep_ms(RECOVER_MS)
        rail_off = settled()

        mighty.enable_rail()
        time.sleep_ms(RECOVER_MS)
        strip_idle = settled()
        lit = 0
        volts = strip_idle

        print()
        print("powering both panels dark costs {:.0f}mV, {:.3f}V down to {:.3f}V".format(
            (rail_off - strip_idle) * 1000, rail_off, strip_idle))

        print()
        print("both panels at {} of 255, against an idle of {:.3f}V".format(
            STRIP_VALUE, strip_idle))
        print("  each   volts      fall   per LED added")
        previous, added = strip_idle, 0.0
        for count in STRIP_LIT:
            light_strips(count)
            volts = settled()
            step = count - lit
            added = (previous - volts) * 1000 / (step * 2) if step else 0.0
            lit, previous = count, volts
            print("{:6d}  {:6.3f}  {:6.0f}mV  {:9.0f}mV".format(
                count, volts, (strip_idle - volts) * 1000, added))

            if volts < ABORT_VOLTS:
                print("stopped at the {:.1f}V floor".format(ABORT_VOLTS))
                break

        light_strips(0)
        mighty.disable_rail()

        # The last column is what a walk is really for. Where it holds steady the fall
        # is linear in the LEDs lit and can be projected; where it collapses the supply
        # has found a floor of its own and no figure past that step means anything.
        if lit:
            print()
            print("{:.0f}mV per LED over the last step, from an idle of {:.3f}V".format(
                added, strip_idle))
            print("the supply reached {:.3f}V with {} lit across the two".format(
                volts, lit * 2))

    # Everything is dark by here, so this is the pack itself over the run and not a load
    time.sleep_ms(RECOVER_MS)
    recovered = settled()

    print()
    print("idle {:.3f}V at the start, {:.3f}V at the end, {:.0f}mV of drift".format(
        idle, recovered, (idle - recovered) * 1000))

finally:
    mighty.shutdown()
