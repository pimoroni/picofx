import cppmem
import gc

# Switch C++ memory allocations to use MicroPython's heap
cppmem.set_mode(cppmem.MICROPYTHON)

# Collect once this much has been allocated, rather than waiting for the heap to fill. An
# effect player allocates a few KB a tick, and on a heap this size the allocator slows as it
# fills, so a tick creeps from 5ms to 12ms and the effects lose time. Beyond the reach of
# TinyFX's smaller heap, which already collects often enough to stay flat.
gc.threshold(200_000)
