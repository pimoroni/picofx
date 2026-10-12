from comms.protocol import DEVICE_TINY_FX, FXTarget

# Imported so a board driving the bus finds them beside the target
from comms.protocol import MightyFXControl, TinyFXControl  # noqa: F401


# Device Side (receive)
class TinyFXTarget(FXTarget):
    DEVICE_ID = DEVICE_TINY_FX

    def __init__(self, tiny_fx, address):
        # Six outputs, then the RGB's three channels, in the order a TinyFXControl sends them
        super().__init__(tiny_fx, address,
                         tiny_fx.outputs + [tiny_fx.rgb.led_r, tiny_fx.rgb.led_g, tiny_fx.rgb.led_b])
