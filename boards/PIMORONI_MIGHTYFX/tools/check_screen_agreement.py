# Checks that a Screen and the SPIDisplay under it agree on the panel.
#
# Dimensions, rate and banding used to be arguments to update(). They are now
# construction state, and it is held twice: once in the Screen, once in the
# SPIDisplay the Screen built. size(), band_rows() and baudrate() are the only
# readings of the second copy, so nothing else can tell the two apart.
#
# That matters most for the keyword overrides. Screen280(port, height=280) has to
# carry 280 all the way into the C constructor, and if it does not, the only symptom
# is a wrong picture on a panel that is already showing an unfamiliar frame. So the
# second screen here is deliberately overridden, and the check and the panel
# corroborate each other: size() says the number arrived, and a frame that stops
# short of the bottom says the transport acted on it.
#
# A diagnostic, not an example, so it is not copied to the board. Copy it across to
# run it.

from mighty_fx import SPCE, MightyFX
from picovector import color, image
from screens import Screen280

# What is wired. SCREEN_B may be None for a single panel, and OVERRIDES_B is what
# the second screen is built with on top of its class. Import Screen154 as well to
# put a 1.54 on either port.
SCREEN_A = Screen280
SCREEN_B = Screen280
OVERRIDES_B = {"height": 280, "framerate": 45}

# Requested rows per DMA band. The driver clamps only to the panel height, which
# band_rows() is what reports, and the rows claim real SRAM per screen.
BAND_LINES = 16

tally = {"PASS": 0, "FAIL": 0}


def check(name, expected, actual):
    verdict = "PASS" if expected == actual else "FAIL"
    tally[verdict] += 1
    print(f"  {verdict} {name}: {actual}" + ("" if verdict == "PASS" else f", expected {expected}"))


def report(label, screen):
    """Compare everything the Screen knows against what its SPIDisplay holds."""
    display = screen.__display
    print(f"\n{label}: {type(screen).__name__}")

    # The one comparison nothing else makes. A mismatch is a fault in Screen's
    # constructor, not in the wiring
    check("size", (screen.width, screen.height), display.size())

    # band_rows() is the request after clamping, so the band count follows from it
    # and the panel height
    expected_rows = min(BAND_LINES, screen.height)
    check("band rows", expected_rows, display.band_rows())
    bands = (screen.height + display.band_rows() - 1) // display.band_rows()
    print(f"       {bands} bands of {display.band_rows()} rows for {screen.height} rows")

    # The workspace claim is band pair plus cache, each rounded to 4 bytes, and
    # sram_bytes() is what buffer_size() dropped by when the screen was built
    row_bytes = screen.width * 3 // 2 if screen.__bitdepth == 12 else screen.width * 2
    band_bytes = (display.band_rows() * row_bytes + 3) & ~3
    print(f"       claims {display.sram_bytes()} bytes of SRAM"
          f" ({2 * band_bytes} band + {display.sram_bytes() - 2 * band_bytes} cache)")

    # The divider only reaches clk_peri/(2*n), so the rate is rounded down. Equal is
    # the happy case, above the request would be a fault
    achieved = display.baudrate()
    requested = screen.requested_baudrate
    check("rate not above the request", True, achieved <= requested)
    if achieved == requested:
        print(f"       {achieved} Hz exactly as asked")
    else:
        print(f"       {achieved} Hz against {requested} requested,"
              f" {100.0 * achieved / requested:.1f}% of it")

    print(f"       {screen.framerate} fps, {screen.__bitdepth}-bit, v_sync={screen.__v_sync}")


def draw_ruler(screen, label):
    """A frame whose content says how tall the panel was told it is.

    A bar every 40 rows from the top, and one hugging the last row. On a screen whose
    height was overridden shorter than the panel, the bottom bar lands short of the
    physical edge, which is the override taking effect.

    A plain image(), not canvas(): nothing here is timed, so the SRAM region is not
    worth spending, and two screens both taking canvas() would share it.
    """
    canvas = image(screen.width, screen.height)
    canvas.pen = color.black
    canvas.clear()

    canvas.pen = color.rgb(60, 60, 60)
    for y in range(0, screen.height, 40):
        canvas.rectangle(0, y, screen.width, 2)

    canvas.pen = color.rgb(255, 80, 80)
    canvas.rectangle(0, screen.height - 4, screen.width, 4)

    canvas.pen = color.white
    canvas.rectangle(0, 0, 8, 8)

    screen.update(canvas)
    print(f"  {label}: drew a {screen.width}x{screen.height} ruler,"
          f" red bar on its last row")


mighty = MightyFX(spce_a=SPCE.SCREEN, spce_b=SPCE.SCREEN if SCREEN_B else None,
                  init_wav=False)

screens = [(SCREEN_A(mighty.spce_a, band_lines=BAND_LINES), "A, class defaults")]
if SCREEN_B:
    screens.append((SCREEN_B(mighty.spce_b, band_lines=BAND_LINES, **OVERRIDES_B),
                    f"B, overridden with {OVERRIDES_B}"))

try:
    print("Screen against SPIDisplay")
    for screen, label in screens:
        report(label, screen)

    print("\nrulers")
    for screen, label in screens:
        draw_ruler(screen, label)

    if SCREEN_B and "height" in OVERRIDES_B:
        print("\n  Compare the two panels: B's red bar should sit"
              f" {SCREEN_B.HEIGHT - OVERRIDES_B['height']} rows above its bottom edge,"
              " which is the override reaching the transform. A bar on the edge means"
              " it did not, whatever size() said.")

    print(f"\n{tally['PASS']} passed, {tally['FAIL']} failed")
    print("Press Boot to finish")
    while not mighty.boot_pressed():
        pass

finally:
    mighty.shutdown()
