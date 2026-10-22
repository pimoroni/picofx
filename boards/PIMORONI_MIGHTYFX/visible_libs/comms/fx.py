from comms.protocol import DEVICE_MIGHTY_FX, FXTarget

# Imported so a board driving the bus finds them beside the target
from comms.protocol import MightyFXControl, TinyFXControl  # noqa: F401


# Device Side (receive)
class MightyFXTarget(FXTarget):
    """A Mighty FX answering on the bus whose outputs a MightyFXControl sets."""

    DEVICE_ID = DEVICE_MIGHTY_FX

    def __init__(self, mighty_fx, address):
        # Every output's three channels, in the order a MightyFXControl sends them
        super().__init__(mighty_fx, address, mighty_fx.monos)
