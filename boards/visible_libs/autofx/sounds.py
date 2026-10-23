# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# The sounds. Each audio entry is built into a WAV that plays beside the effects, and the
# board plays one at a time. A scene change gives the speaker to the sound that scene wants.

import io
import time

from .vocabulary import AUDIO_EFFECTS, EFFECTS, MOUNT_DIR, SCREEN_EFFECTS
from .parser import Channel
from .checks import check_settings, find_image


class Sound:
    """
    One WAV playing beside the effects: the player it runs on, the file it reads,
    and whether it starts again when it ends. A file on the drive is read straight
    from the flash, so it plays through a handover, and the player stands it aside
    while the computer writes. One the computer rewrites goes silent until the next
    reload, since what it reads is no longer that sound.

    The board plays one sound at a time, so the sounds share the player and `live`
    says which of them has it. One put aside by a scene switch remembers where it
    reached and picks up from there on its next turn; one that had already ended
    starts again from the top.
    """

    # The longest a sound paused for the board joining the bus is given to fade out of
    # the player's ring before the player shuts down, which a board may make a few
    # hundred milliseconds long
    FADE_MS = 400

    def __init__(self, wav, handle, loop, scene=None):
        self.wav = wav
        self.handle = handle
        self.loop = loop
        self.scene = scene
        self.live = False
        self.__at = None
        self.__moved = None
        self.__from = 0         # Where the next start picks up, 0 being the top
        self.__gone = False     # Whether the computer changed the file since load
        self.__held = False     # Whether joining the bus stopped it part way through

    def start(self):
        if self.__gone:
            return
        try:
            self.wav.play_wav(self.handle, loop=self.loop, position=self.__from)
        except (OSError, ValueError) as e:
            # Unreadable as a WAV, however it came to be: nothing plays until a
            # reload brings a readable one
            print("the sound could not start, and waits for the next reload:", e)
        self.__from = 0
        self.live = True

    def service(self):
        """
        Watch a playing sound for progress, and start it again where it stalls.
        The player feeds its buffers over a chain of I2S callbacks, and a lost
        callback ends the chain: the state stays playing while nothing sounds.
        A restart from the held position rebuilds the player, and the chain
        with it. Half a second of stillness says stalled; a sound that ended
        reports no position and is left alone.
        """
        if not self.live:
            self.__at = None
            return
        at = self.wav.position()
        now = time.ticks_ms()
        # Check if it has just ended because the computer replaced its file, which the
        # player found as the writes finished
        if at is None and self.__at is not None and self.__file_changed():
            return
        if at is None or at != self.__at:
            self.__at = at
            self.__moved = now
            return
        if time.ticks_diff(now, self.__moved) < 500:
            return
        self.__from = at
        self.__moved = now
        print("the sound stalled, and starts again from where it stopped")
        self.start()

    def set_aside(self):
        """Put aside by a scene switch: silenced, remembering where it reached."""
        if not self.live:
            return
        self.wav.pause()
        # None where the sound had already ended, which is a start from the top
        self.__from = self.wav.position() or 0
        self.live = False

    # The player is shared, so a sound standing aside while the board joins the bus only
    # touches it while the speaker is its own. It stops outright, as the effects do, and
    # resume() picks up where it was
    def pause(self):
        if not self.live:
            return
        # None is a sound that had already ended, which joining the bus leaves ended
        if self.wav.position() is None:
            return
        # Faded out before it stops, a cut mid-waveform clicking
        self.wav.pause()
        deadline = time.ticks_add(time.ticks_ms(), self.FADE_MS)
        while not self.wav.is_paused() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            time.sleep_ms(5)
        at = self.wav.position()
        self.wav.deinit()
        # None again is a sound that ended during the fade
        if at is not None:
            self.__from = at
            self.__held = True

    def resume(self):
        # The watch starts afresh: the position stood still through the pause
        self.__at = None
        if self.__file_changed():
            return
        if self.__held:
            self.__held = False
            self.start()

    def __file_changed(self):
        # Check if the computer has replaced the file, which leaves the sound silent until
        # the next reload
        changed = getattr(self.handle, "changed", None)
        if self.__gone or changed is None or not changed():
            return False
        self.__gone = True
        if self.live:
            self.wav.stop()
        self.live = False
        self.__held = False
        print("a sound's file changed on the drive, and it waits for the next reload")
        return True

    def restart(self):
        """Back to the top, for a scene that begins again on every entry."""
        self.__from = 0
        if self.live:
            self.start()

    def close(self):
        # Neither half may stop the other, nor whatever is tidying up after this: a
        # player mid-transfer and a handle on a volume the computer has taken are both
        # reached here, and there is nothing left to save either way
        try:
            self.wav.deinit()
        except Exception as e:      # noqa: BLE001
            print("the sound would not stop:", e)
        try:
            self.handle.close()
        except OSError:
            pass


def __open_sound(path, stream):
    # A handle the player can read for the whole run. The drive's mount ends whenever
    # a computer takes the drive, so a file there is read from the flash, or held in
    # memory where the drive cannot find it that way. The board never gives up its
    # own filesystem, so a file there is read as it plays
    if path.startswith(MOUNT_DIR + "/"):
        handle = stream(path[len(MOUNT_DIR) + 1:]) if stream is not None else None
        if handle is not None:
            return handle
        with open(path, "rb") as source:
            return io.BytesIO(source.read())
    return open(path, "rb")


def build_sounds(entries, fx, problems, volume=None):
    """
    A sound per audio entry: one before any heading playing throughout, and one per
    scene taking the speaker while its scene shows. The file is found here, while
    the board holds the drive, which is what lets it stream on after a computer
    takes the volume.
    """
    sounds = []
    stream = volume.stream if volume is not None else None
    taken = set()
    # A board without audio raises from the property, naming the setting to change
    try:
        wav = fx.wav
    except (AttributeError, RuntimeError):
        wav = None

    for entry in entries:
        if wav is None:
            problems.append("line {}: this board has no audio".format(entry.line))
            continue

        if entry.effect not in AUDIO_EFFECTS:
            if entry.effect in EFFECTS or entry.effect in SCREEN_EFFECTS:
                problems.append("line {}: {} does not make a sound, audio plays "
                                "{}".format(entry.line, entry.effect,
                                            ", ".join(sorted(AUDIO_EFFECTS))))
            elif entry.effect is not None:
                problems.append("line {}: '{}' is not something audio plays, expected "
                                "{}".format(entry.line, entry.effect,
                                            ", ".join(sorted(AUDIO_EFFECTS))))
            continue

        channel = entry.channels[0]
        for setting in Channel.SETTINGS:
            if getattr(channel, setting) is not None:
                problems.append("line {}: {} says nothing about a sound, so it was "
                                "ignored".format(entry.line, setting))

        settings = check_settings(entry, AUDIO_EFFECTS[entry.effect], problems)

        target = settings.get("file")
        if target is None:
            if "file" not in entry.settings:
                problems.append("line {}: {} needs a file to play, such as "
                                "file=sound.wav".format(entry.line, entry.effect))
            continue

        # One sound at a time is the hardware, so a scene carries one and so does the
        # part before any heading. A second in the same place has already been
        # answered by the parser as a repeated selector, so it only skips here
        if entry.scene in taken:
            continue

        at = entry.lines.get("file", entry.line)
        path = find_image(target, at, problems)
        if path is None:
            continue

        try:
            handle = __open_sound(path, stream)
        except OSError as e:
            problems.append("line {}: {} could not be opened: {}".format(at, target, e))
            continue
        except MemoryError:
            problems.append("line {}: {} is too large to load. A sound has to fit "
                            "in memory beside everything else that is "
                            "playing.".format(at, target))
            continue

        taken.add(entry.scene)
        sounds.append(Sound(wav, handle, bool(settings.get("loop", False)), entry.scene))

    return sounds


def cue_sound(sounds, scene):
    """
    Give the speaker to the sound this scene wants: its own, or the one from before
    any heading where it brings none. The one giving it up remembers where it
    reached, so a long sound picks up where it left off on its next turn, and one
    that had ended starts again from the top.
    """
    wanted = None
    for sound in sounds:
        if sound.scene is None and wanted is None:
            wanted = sound
        if scene is not None and sound.scene == scene.key:
            wanted = sound

    for sound in sounds:
        if sound is not wanted:
            sound.set_aside()

    # One already playing carries on: the scene it also serves has come round again,
    # or it is the always-on sound outlasting a scene with none of its own
    if wanted is not None and not wanted.live:
        wanted.start()
