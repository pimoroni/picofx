import time

from aye_arr.nec.remotes import PimoroniRemote
from mighty_fx import MightyFX
from sensor import IR
from servo import CONTINUOUS

from picofx import ColourPlayer
from picofx.colour import BLUE, CYAN, GREEN, MAGENTA, RED, WHITE, YELLOW
from picofx.mono import PulseFX, StaticFX

"""
Programme a route into a two wheeled robot with the Aye Arr Remote, then watch it drive
what it was told, its wheels turned by a continuous rotation servo on each of the L and
R connectors.

A route is a list of movements, each a direction and how many cycles to hold it for. It
is entered on the remote a movement at a time: press a direction, then the digits of a
number, then the next direction, which ends the one before it.

The outputs say what is happening without anyone watching the console. They pulse red
while a route is being taken down, and flash on every press that was taken. While the
route is driven the movement's length is lit dim, a bright light travels it a cycle at
a time, and what it has been through holds a shade between the two, so a two cycle
movement lights two and a five cycle one lights five. A
movement longer than there are outputs fills them and starts again, so a long one can be
counted in pages. Each movement takes the next colour in turn, so a
route of short movements still shows where one ends and the next begins.

An IR Stick should be connected to the Sensor port, and a continuous rotation servo to
each of the L and R connectors.

Actions:
- RECORD Button = Start or stop taking a route down
- PLAY_PAUSE Button = Drive the route, or stop driving it
- While taking a route down:
    - UP, DOWN, LEFT, RIGHT, OK Buttons = Choose the movement
    - (0)-(9) Buttons = How many cycles to hold it for
    - RETURN Button = Undo the last digit, movement, or whole entry

Press "Boot" to exit the program.
"""

# Constants
SPEED = 0.5             # The speed the wheels drive at
TURN_SPEED = 0.4        # The speed the wheels turn at, slower being easier to aim
CYCLE_TIME = 1.0        # The time, in seconds, one cycle of a movement takes
CHECK_TIME = 0.02       # How often to look at the button and the remote while driving
BLIP_MS = 60            # How long the outputs flash to say a press was taken
BLIP_LEVEL = 0.3        # How brightly they flash, dim enough to read against the pulse
DIM_LEVEL = 0.05        # What a light rests at to show how long a movement is
PASSED_LEVEL = 0.25     # What a light holds once the movement has been through it

# The colour each movement of a route is driven in, taken in turn. A movement of one
# cycle lights one output for a moment, which is the same picture every time, so the
# colour is what says a new movement has begun
ROUTE_COLOURS = (GREEN, CYAN, BLUE, MAGENTA, YELLOW)

# Variables
mighty = MightyFX(servo_l=CONTINUOUS, servo_r=CONTINUOUS, sensor=IR)
player = ColourPlayer(mighty.outputs)
lights = len(mighty.outputs)
route = []              # The movements taken down, each a name and a number of cycles

mighty.enable_rail()    # Power the L and R connectors, which stay off until asked
mighty.servo_l.enable()
mighty.servo_r.enable()

player.effects = PulseFX(speed=1.0)
player.levels = 0.0

showing = (RED, 0.0, False)
blip_until = 0


# Function to hold a set of lights, remembered so a flash can hand them back
def show(colour, levels, steady=False):
    global showing
    showing = (colour, levels, steady)
    player.effects = StaticFX() if steady else PulseFX(speed=1.0)
    player.colours = colour
    player.levels = levels


# Function to say that a press was taken. A remote gives nothing back by itself, so
# without this a button that did nothing and one that did look the same. It ends in the
# main loop rather than here: sleeping inside a remote callback is time decode() is not
# running, and a frame arriving then is lost
def blip():
    global blip_until
    player.effects = StaticFX()
    player.colours = WHITE
    player.levels = BLIP_LEVEL
    blip_until = time.ticks_add(time.ticks_ms(), BLIP_MS)


# The movements a route can be made of. The wheels face opposite ways on a robot, so
# driving asks one for a speed and the other for its negative, and turning on the spot
# asks both for the same
def forwards():
    mighty.servo_l.value(SPEED)
    mighty.servo_r.value(-SPEED)


def backwards():
    mighty.servo_l.value(-SPEED)
    mighty.servo_r.value(SPEED)


def spin_left():
    mighty.servo_l.value(-TURN_SPEED)
    mighty.servo_r.value(-TURN_SPEED)


def spin_right():
    mighty.servo_l.value(TURN_SPEED)
    mighty.servo_r.value(TURN_SPEED)


def halt():
    mighty.servo_l.value(0)
    mighty.servo_r.value(0)


MOVEMENTS = {
    "FORWARDS": forwards,
    "BACKWARDS": backwards,
    "LEFT": spin_left,
    "RIGHT": spin_right,
    "STOP": halt,
}

# What the robot is doing. Taking a route down and driving one are exclusive, the same
# buttons meaning different things in each
recording = False
playing = False
entry = None            # The movement being entered, and its digits so far
digits = ""


# Function to take one movement down, a direction and the cycles it is held for
def record(name, count):
    route.append((name, int(count)))
    print(" cycles")


# Function to drive one movement, watching for the button and the remote as it goes
def perform(name, cycles, index):
    colour = ROUTE_COLOURS[index % len(ROUTE_COLOURS)]
    print(f"[{index + 1}/{len(route)}] {name} for {cycles} cycles")

    # The colour and the effect are set once for the movement, and only the levels move
    # from here: an effect assigned every pass builds a new one and rebuilds the
    # player's channels each time, which is fifty of each a second for nothing
    show(colour, 0.0, steady=True)

    MOVEMENTS[name]()
    held = 0.0
    while held < cycles * CYCLE_TIME:
        receiver.decode()
        if mighty.boot_pressed() or not playing:
            return False

        # The movement's own length is lit dim and a bright light travels it a cycle
        # at a time, so the bar is as long as this movement rather than the last one.
        # A movement longer than there are outputs fills them and starts again, the
        # final page being as long as what is left of it
        cycle = int(held / CYCLE_TIME)
        position = cycle % lights
        page_length = min(lights, cycles - (cycle // lights) * lights)
        levels = []
        for i in range(lights):
            if i == position:
                levels.append(1.0)
            elif i < position:
                levels.append(PASSED_LEVEL)
            elif i < page_length:
                levels.append(DIM_LEVEL)
            else:
                levels.append(0.0)

        player.levels = levels

        time.sleep(CHECK_TIME)
        held += CHECK_TIME

    return True


# Function called when a direction button is pressed while taking a route down
def on_movement(name):
    global entry, digits

    # A direction outside a recording is nobody's, and taking it would put it at the
    # front of whatever route is taken down next
    if not recording:
        return

    # A new direction ends the one before it, which is what its digits belonged to
    if entry is not None and digits:
        record(entry, digits)

    entry = name
    digits = ""
    blip()
    print(f" + {name} for:", end=" ")


# Function called for any button the remote knows, to catch the digits
def on_known(command):
    global digits

    if not recording or entry is None:
        return False

    number = PimoroniRemote.NUMBERS.get(command)
    if number is None:
        return False

    digits += str(number)
    blip()
    print(number, end="")
    return True


# Function called to start or stop taking a route down
def on_record():
    global recording, entry, digits, route

    if playing:
        print(" - press PLAY to stop driving before taking a route down")
        return

    if recording:
        if entry is not None and digits:
            record(entry, digits)

        recording = False
        entry = None
        print(f"--- {len(route)} movements taken down ---" if route else "--- nothing taken down ---")
        show(RED, 0.0)
        return

    route = []
    recording = True
    entry = None
    digits = ""
    print("--- taking a route down ---")
    show(RED, 1.0)


# Function called to drive the route, or to stop driving it. Pressing it while a route
# is being taken down finishes taking it down first, that being what was meant by it
def on_play():
    global playing

    if recording:
        on_record()

    was_driving = playing
    playing = not playing and bool(route)
    if not playing:
        halt()
        show(GREEN, 0.0)
        if was_driving:
            print("--- stopped driving ---")


# Function called to undo the last digit, movement, or whole entry
def on_undo():
    global entry, digits

    if not recording:
        return

    blip()
    if digits:
        digits = digits[:-1]
        print("\n - undid a digit")
    elif entry is not None:
        entry = None
        print(" - undid a movement")
    elif route:
        name, cycles = route.pop()
        print(f" - undid {name} for {cycles} cycles")
    else:
        print(" - nothing to undo")


# Create the remote and setup up what each of the buttons will do
remote = PimoroniRemote()
remote.on_known = on_known
remote.bind("UP", (on_movement, "FORWARDS"), on_repeat=None)
remote.bind("DOWN", (on_movement, "BACKWARDS"), on_repeat=None)
remote.bind("LEFT", (on_movement, "LEFT"), on_repeat=None)
remote.bind("RIGHT", (on_movement, "RIGHT"), on_repeat=None)
remote.bind("OK_STOP", (on_movement, "STOP"), on_repeat=None)
remote.bind("RECORD", on_record, on_repeat=None)
remote.bind("PLAY_PAUSE", on_play, on_repeat=None)
remote.bind("RETURN_UNDO", on_undo, on_repeat=None)

# Take the receiver the board set up, and bind the remote to it.
receiver = mighty.sensor
receiver.bind(remote)

print("Press RECORD to take a route down, then PLAY to drive it")


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    player.start()

    while not mighty.boot_pressed():
        receiver.decode()

        # Put a flash out once it has been seen, which is the main loop's job
        if blip_until and time.ticks_diff(time.ticks_ms(), blip_until) >= 0:
            blip_until = 0
            show(*showing)

        if playing:
            for index, (name, cycles) in enumerate(route):
                if not perform(name, cycles, index):
                    break
            else:
                print("--- route driven ---")

            playing = False
            halt()
            show(GREEN, 0.0)

        time.sleep(CHECK_TIME)

# Stop the wheels, drop the connectors' power and turn off all the outputs
finally:
    player.stop()
    mighty.shutdown()
