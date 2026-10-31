import cppmem
import gc

# Switch C++ memory allocations to use MicroPython's heap
cppmem.set_mode(cppmem.MICROPYTHON)

# Collect after this much allocation, not when the heap fills, since on a large heap the
# allocator slows as it fills and an effect player allocates every tick. A smaller heap fills first
gc.threshold(200_000)
