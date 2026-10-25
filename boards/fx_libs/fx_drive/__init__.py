"""
The FX drive is a small FAT partition holding effects.txt, editable from a connected
computer over USB mass storage, and room for the assets a program reads. The mount
is read-write whenever the board holds the drive, and released while the computer
does, so the two writers can never meet. While the computer holds it, the mount
point is a read-only view read straight from the flash, so a program still finds
its files there.

The drive is shown at boot and controlled from then on by the button passed to
service(). A double press shows or hides it, and hiding it, or ejecting it on the
computer, re-reads the file. An eject does not show it again.
"""

from .fat import Stream, stream
from .heal import FILE_PATH, MOUNT_POINT, mount, unhealed
from .handover import (BUSY, EJECTED, HIDDEN, IDLE, RELOADED, SHOWN, busy, enumerating, expose,
                       exposed, on_bus_reset, reset_on_save, service, watch, withdraw)
