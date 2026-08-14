import cppmem
import gc
import os

# Switch C++ memory allocations to use MicroPython's heap
cppmem.set_mode(cppmem.MICROPYTHON)

# Collect once this much has been allocated, rather than waiting for the heap to fill. An
# effect player allocates a few KB a tick, and on a heap this size the allocator slows as it
# fills, so a tick creeps from 5ms to 12ms and the effects lose time. Beyond the reach of
# TinyFX's smaller heap, which already collects often enough to stay flat.
gc.threshold(200_000)

# Write main.py when it is missing, so a board is never left doing nothing by
# accident and a fresh one starts without shipping a copy in the image. An empty
# main.py is left alone, that being how someone asks for a quiet board. Boards
# without an fx_defaults carry their main.py in the image instead.
try:
    os.stat("main.py")
except OSError:
    try:
        import fx_defaults
        with open("main.py", "w") as f:
            f.write(fx_defaults.MAIN)
    except ImportError:
        pass
