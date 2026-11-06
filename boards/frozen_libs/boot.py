import cppmem
import gc
import os

# Switch C++ memory allocations to use MicroPython's heap
cppmem.set_mode(cppmem.MICROPYTHON)

# Collect after this much allocation, not when the heap fills, since on a large heap the
# allocator slows as it fills and an effect player allocates every tick. A smaller heap fills first
gc.threshold(200_000)

# Write main.py where it is missing, so a fresh board runs its default program without one
# shipping in the image. An empty main.py is left alone, as the way to ask for a quiet board
try:
    os.stat("main.py")
except OSError:
    try:
        import fx_defaults
        with open("main.py", "w") as f:
            f.write(fx_defaults.MAIN)
    except ImportError:
        # A build without fx_defaults ships its main.py in the image
        pass
    except OSError:
        # A full filesystem. The empty main.py a failed write leaves would ask for a quiet board
        try:
            os.remove("main.py")
        except OSError:
            pass
