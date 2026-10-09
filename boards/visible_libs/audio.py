# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import math
import micropython
import struct
import time

from machine import I2S, Pin

# The USB drive's file type and write controls, on firmware that shows one to a computer.
# Without them a sound never steps aside for a write
try:
    from rp2 import MSCFile as __DriveFile
    from rp2 import hold_msc_writes as __hold_writes
    from rp2 import is_msc_busy as __drive_busy
    from rp2 import msc_write_count as __drive_writes
    from rp2 import release_msc_writes as __release_writes
except ImportError:
    __DriveFile = None

"""
A class for playing Wav files out of an I2S audio amp. It can also play pure tones.
Where the board shows a USB drive to a computer, a sound fades out while the computer
writes to it and returns after, except a Wav read from that drive, which ends.
This code is based heavily on the work of Mike Teachman, at:
https://github.com/miketeachman/micropython-i2s-examples/blob/master/examples/wavplayer.py
"""


@micropython.viper
def __ramp(samples: ptr16, count: int, gain: int, step: int):
    # Scales signed 16-bit samples by a gain in 32768ths that moves by step each sample.
    # Native code, since the callback has to scale a buffer in less time than it plays
    for index in range(count):
        value = int(samples[index])
        if value & 0x8000:
            value -= 0x10000
        samples[index] = (value * gain) >> 15
        gain += step


class WavReader:
    def __init__(self, file):
        # A path is opened here and closed by close(). An already-open file is
        # the caller's to close, so one handle can be played many times
        self.__owns_file = isinstance(file, str)
        if self.__owns_file:
            self.wav_file = open(file, "rb")
        else:
            self.wav_file = file
            self.wav_file.seek(0)
        self._parse(self.wav_file)

    def _parse(self, wav_file):
        chunk_ID = wav_file.read(4)
        if chunk_ID != b"RIFF":
            raise ValueError("WAV chunk ID invalid")
        _ = wav_file.read(4)                            # chunk_size
        if wav_file.read(4) != b"WAVE":
            raise ValueError("WAV format invalid")
        sub_chunk1_ID = wav_file.read(4)
        if sub_chunk1_ID != b"fmt ":
            raise ValueError("WAV sub chunk 1 ID invalid")
        _ = wav_file.read(4)                            # sub_chunk1_size
        _ = struct.unpack("<H", wav_file.read(2))[0]    # audio_format
        num_channels = struct.unpack("<H", wav_file.read(2))[0]

        if num_channels == 1:
            self.format = I2S.MONO
        else:
            self.format = I2S.STEREO

        self.sample_rate = struct.unpack("<I", wav_file.read(4))[0]
        # if sample_rate != 44_100 and sample_rate != 48_000:
        #    raise ValueError(f"WAV sample rate of {sample_rate} invalid. Only 44.1KHz or 48KHz audio are supported")

        _ = struct.unpack("<I", wav_file.read(4))[0]    # byte_rate
        _ = struct.unpack("<H", wav_file.read(2))[0]    # block_align
        self.bits_per_sample = struct.unpack("<H", wav_file.read(2))[0]

        # usually the sub chunk2 ID ("data") comes next, but
        # some online MP3->WAV converters add
        # binary data before "data".  So, read a fairly large
        # block of bytes and search for "data".

        binary_block = wav_file.read(200)
        offset = binary_block.find(b"data")
        if offset == -1:
            raise ValueError("WAV sub chunk 2 ID not found")

        self.offset = offset + 44

        wav_file.seek(offset + 40)
        self.size = struct.unpack("<I", wav_file.read(4))[0]

        wav_file.seek(self.offset)

    def seek(self, pos):
        return self.wav_file.seek(pos + self.offset)

    def tell(self):
        return self.wav_file.tell() - self.offset

    def readinto(self, buf):
        max_bytes = self.size - self.tell()
        max_bytes = max(0, min(len(buf), max_bytes))
        return self.wav_file.readinto(buf[:max_bytes])

    def close(self):
        if self.__owns_file:
            self.wav_file.close()


class WavPlayer:
    # Internal states
    PLAY = 0
    PAUSE = 1
    FLUSH = 2
    STOP = 3
    NONE = 4

    MODE_WAV = 0
    MODE_TONE = 1

    TONE_SINE = 0
    TONE_SQUARE = 1
    TONE_TRIANGLE = 2

    # Default buffer length
    SILENCE_BUFFER_LENGTH = 1024
    WAV_BUFFER_LENGTH = 1024
    INTERNAL_BUFFER_LENGTH = WAV_BUFFER_LENGTH * 2

    TONE_SAMPLE_RATE = 44_100
    TONE_BITS_PER_SAMPLE = 16
    TONE_FULL_WAVES = 2

    # How long a tone or 16-bit WAV takes to rise from silence or fall to it, where starting
    # or stopping mid-waveform would click
    FADE_MS = 40

    # How long the computer's first write to the USB drive waits while a sound fades out,
    # each flash write stalling the audio beneath it
    WRITE_HOLD_MS = 500

    # ibuf_ms, where given, grows the I2S ring to hold at least that much of whatever plays,
    # sized from its byte rate as it starts, for a board whose refills can be held up
    def __init__(self, id, sck_pin, ws_pin, sd_pin, amp_enable=None, ibuf_len=INTERNAL_BUFFER_LENGTH, root="/", ibuf_ms=None):
        self.__id = id
        self.__sck_pin = sck_pin
        self.__ws_pin = ws_pin
        self.__sd_pin = sd_pin
        self.__ibuf_len = ibuf_len
        self.__ibuf_ms = ibuf_ms
        self.__ring_ms = 0              # How long the ring takes to play out at the current rate
        self.__silent_at = 0            # When a pause's faded audio has played out of the ring
        self.__enable = None

        # Manually tweak the tone amplitude for equal loudness of sine/square/triangle
        self.__amplitude_scale = [1.0, 0.2, 0.5]

        if amp_enable is not None:
            self.__enable = Pin(amp_enable, Pin.OUT)

        # Set the directory to search for files in
        self.set_root(root)

        self.__state = WavPlayer.NONE
        self.__mode = WavPlayer.MODE_WAV
        self.__wav_file = None
        self.__loop_wav = False
        self.__fade_length = 0          # The samples a fade takes at the current sound's rate
        self.__fade = 0                 # Samples still to rise from silence
        self.__fading_out = 0           # Samples still to fall to silence, the player pausing after
        self.__holding = None           # The write hold replaced while a sound plays
        self.__was_busy = False         # Whether the computer was writing at the last refill
        self.__writes_seen = 0          # The computer's write count at the last refill
        self.__from_drive = False       # Whether the WAV is read from the USB drive, so a write ends it
        self.__stopping = False         # Whether the sound ends once its fade has played out
        self.__standing_aside = False   # Whether the sound is paused while the computer writes
        self.__aside_silent = False     # Whether that pause has gone quiet and let the write go
        self.__amp_on = False
        self.__flush_count = 0
        self.__audio_out = None

        # Allocate a small array of blank audio samples used for silence
        self.__silence_samples = bytearray(self.SILENCE_BUFFER_LENGTH)

        # Allocate a larger array for WAV audio samples, using a memoryview for more efficient access
        self.__wav_samples_mv = memoryview(bytearray(self.WAV_BUFFER_LENGTH))

        # Reserve a variable for audio samples used for tones
        self.__tone_samples = None
        self.__tone_scaled = None       # Room for a faded copy of the tone's buffer
        self.__queued_samples = None
        self.__queued_scaled = None

    def set_root(self, root):
        self.__root = root.rstrip("/") + "/"

    # Where the file object has a changed() method, the WAV calls it before returning after
    # the computer's writes to the USB drive, and ends instead if it answers True
    def play_wav(self, wav_file, loop=False, position=0):
        self.__stop_i2s()                                       # Stop any active playback and terminate the I2S instance

        # Parse the WAV file, returning the necessary parameters to initialise I2S communication.
        # A string names a file under root; anything else is an already-open WAV file
        if isinstance(wav_file, str):
            try:
                self.__wav_file = WavReader(self.__root + wav_file)
            except OSError:
                raise ValueError(f"'{wav_file}' not found") from None
        else:
            self.__wav_file = WavReader(wav_file)
        self.__loop_wav = loop                                  # Record if the user wants the file to loop
        self._loop_count = 0                                    # Count loops for debugging purposes

        # Pick up part way through, from a position() a caller kept. Sought here,
        # before the I2S callback starts reading, so nothing races the seek
        channels = 1 if self.__wav_file.format == I2S.MONO else 2
        self.__fade_length = max(1, self.__wav_file.sample_rate * channels * self.FADE_MS // 1000)
        self.__fade = 0
        self.__fading_out = 0
        self.__arm_hold(__DriveFile is not None and isinstance(self.__wav_file.wav_file, __DriveFile))
        if position:
            self.__wav_file.seek(position)
            # Mid-waveform, so it fades in or it clicks. The fade reads 16-bit samples
            if self.__wav_file.bits_per_sample == 16:
                self.__fade = self.__fade_length

        self.__start_i2s(bits=self.__wav_file.bits_per_sample,
                         format=self.__wav_file.format,
                         rate=self.__wav_file.sample_rate,
                         state=WavPlayer.PLAY,
                         mode=WavPlayer.MODE_WAV)

    def play_tone(self, frequency, amplitude, shape=TONE_SINE):
        if frequency < 20.0 or frequency > 20_000:
            raise ValueError("frequency out of range. Expected between 20Hz and 20KHz")

        if amplitude < 0.0 or amplitude > 1.0:
            raise ValueError("amplitude out of range. Expected 0.0 to 1.0")

        if not isinstance(shape, (list, tuple)):
            shape = (shape, )

        # Create a buffer containing the pure tone samples
        samples_per_cycle = self.TONE_SAMPLE_RATE // frequency
        sample_size_in_bytes = self.TONE_BITS_PER_SAMPLE // 8
        samples = bytearray(self.TONE_FULL_WAVES * samples_per_cycle * sample_size_in_bytes)
        maximum = (pow(2, self.TONE_BITS_PER_SAMPLE) // 2 - 1) * amplitude

        format = "<h" if self.TONE_BITS_PER_SAMPLE == 16 else "<l"

        # Populate the buffer with multiple cycles to avoid it completing too quickly and causing drop outs
        for i in range(samples_per_cycle * self.TONE_FULL_WAVES):
            sample = 0
            if self.TONE_TRIANGLE in shape:
                triangle = (i % samples_per_cycle) - (samples_per_cycle // 2)
                triangle /= samples_per_cycle
                triangle *= self.__amplitude_scale[self.TONE_TRIANGLE]
                sample += triangle
            if self.TONE_SINE in shape:
                sine = math.sin(2 * math.pi * i / samples_per_cycle)
                sine *= self.__amplitude_scale[self.TONE_SINE]
                sample += sine
            if self.TONE_SQUARE in shape:
                square = 1 if (i % samples_per_cycle ) < (samples_per_cycle // 2) else -1
                square *= self.__amplitude_scale[self.TONE_SQUARE]
                sample += square
            sample = max(-1, min(1, sample))
            struct.pack_into(format, samples, i * sample_size_in_bytes, int(sample * maximum))

        # Are we not already playing tones?
        if not (self.__mode == WavPlayer.MODE_TONE and (self.__state == WavPlayer.PLAY or self.__state == WavPlayer.PAUSE)):
            self.__stop_i2s()                                       # Stop any active playback and terminate the I2S instance
            self.__tone_samples = samples
            self.__tone_scaled = bytearray(len(samples))
            self.__fade_length = self.TONE_SAMPLE_RATE * self.FADE_MS // 1000
            self.__fade = self.__fade_length    # A tone has no attack of its own, so it rises
            self.__fading_out = 0
            self.__arm_hold(False)
            self.__start_i2s(bits=self.TONE_BITS_PER_SAMPLE,
                             format=I2S.MONO,
                             rate=self.TONE_SAMPLE_RATE,
                             state=WavPlayer.PLAY,
                             mode=WavPlayer.MODE_TONE)
        else:
            self.__queued_scaled = bytearray(len(samples))
            self.__queued_samples = samples
            # Standing aside for the computer's writes, the new tone waits for them too
            if not self.__standing_aside:
                self.__state = WavPlayer.PLAY

    def pause(self):
        if self.__state == WavPlayer.PLAY:
            # A cut mid-waveform clicks, so a tone or 16-bit WAV fades out before pausing.
            # is_paused() turns true once it has
            if self.__fades():
                if not self.__fading_out:
                    self.__fading_out = self.__fade_length
            else:
                self.__state = WavPlayer.PAUSE      # Enter the pause state on the next callback
                self.__silent_at = time.ticks_add(time.ticks_ms(), self.__ring_ms)
        # The caller's pause from here, which the end of the computer's writes leaves alone
        self.__standing_aside = False

    def resume(self):
        self.__fading_out = 0
        self.__standing_aside = False
        self.__aside_silent = False
        if self.__state == WavPlayer.PAUSE:
            self.__amplify(True)
            if self.__fades():
                self.__fade = self.__fade_length    # Back from silence, so it fades in
            self.__state = WavPlayer.PLAY           # Enter the play state on the next callback

    def stop(self):
        # A playing tone or 16-bit WAV fades out first, and ends once the fade has played out
        if self.__state == WavPlayer.PLAY and self.__fades():
            self.__stopping = True
            if not self.__fading_out:
                self.__fading_out = self.__fade_length
            return
        self.__stop_now()

    def __stop_now(self):
        self.__end_hold()
        if self.__state == WavPlayer.PLAY or self.__state == WavPlayer.PAUSE:
            if self.__mode == WavPlayer.MODE_WAV:
                # Enter the flush state on the next callback and close the file
                # It is done in this order to prevent the callback entering the play
                # state after we close the file but before we change the state)
                self.__state = WavPlayer.FLUSH
                self.__wav_file.close()
            else:
                self.__state = WavPlayer.STOP

    def deinit(self):
        self.__stop_i2s()

    def is_playing(self):
        return self.__state != WavPlayer.NONE and self.__state != WavPlayer.STOP

    def position(self):
        """
        How far into the current WAV's data playback has reached, in bytes, for
        play_wav() to pick up from later. None where no WAV is under way: paused
        counts, ended or flushing does not.
        """
        if self.__mode != WavPlayer.MODE_WAV or self.__wav_file is None:
            return None
        if self.__state != WavPlayer.PLAY and self.__state != WavPlayer.PAUSE:
            return None
        return self.__wav_file.tell()

    def is_paused(self):
        # Paused, and the audio queued ahead of the pause has played out
        return self.__state == WavPlayer.PAUSE and time.ticks_diff(time.ticks_ms(), self.__silent_at) >= 0

    def __start_i2s(self, bits=16, format=I2S.MONO, rate=44_100, state=STOP, mode=MODE_WAV):
        import gc
        gc.collect()
        byte_rate = rate * bits // 8 * (1 if format == I2S.MONO else 2)
        ibuf = self.__ibuf_len
        if self.__ibuf_ms is not None:
            # Rounded up to whole refills, and never below the fixed length
            wanted = byte_rate * self.__ibuf_ms // 1000
            ibuf = max(ibuf, -(-wanted // self.WAV_BUFFER_LENGTH) * self.WAV_BUFFER_LENGTH)
        self.__ring_ms = ibuf * 1000 // byte_rate
        self.__audio_out = I2S(
            self.__id,
            sck=self.__sck_pin,
            ws=self.__ws_pin,
            sd=self.__sd_pin,
            mode=I2S.TX,
            bits=bits,
            format=format,
            rate=rate,
            ibuf=ibuf,
        )

        self.__state = state
        self.__mode = mode
        self.__flush_count = ibuf // self.SILENCE_BUFFER_LENGTH + 1
        self.__audio_out.irq(self.__i2s_callback)
        self.__audio_out.write(self.__silence_samples)
        self.__amplify(True)

    def __stop_i2s(self):
        # A pause still fading lets its fade play out of the ring, and one that has played
        # out has nothing left to flush
        if self.__fading_out or self.__state == WavPlayer.PAUSE:
            deadline = time.ticks_add(time.ticks_ms(), self.__ring_ms + 100)
            while not self.is_paused() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
                pass
        drained = self.is_paused()
        self.stop()                     # Stop any active playback
        # Wait for the flush, but not forever: each step needs the I2S callback, and
        # a callback is lost when the scheduler queue is full, after which the state
        # can never advance
        deadline = time.ticks_add(time.ticks_ms(), 250 + self.__ring_ms)
        while not drained and self.is_playing() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            pass
        if self.is_playing():
            # The flush never finished, so playback is torn down instead. The next
            # play builds the peripheral afresh, which restores its callback chain
            self.__audio_out.deinit()
            self.__state = WavPlayer.NONE

        self.__amplify(False)

        if self.__audio_out is not None:
            self.__audio_out.deinit()   # Deinit any active I2S comms

        self.__state = WavPlayer.NONE   # Return to the none state

    def __fade_in(self, samples, length):
        # Each sample still to rise is scaled by how far into the fade it falls
        step = 32768 // self.__fade_length
        count = min(length // 2, self.__fade)
        __ramp(samples, count, (self.__fade_length - self.__fade) * step, step)
        self.__fade -= count

    def __fade_out(self, samples, length):
        # The fall can span buffers. The one it ends in is silent after it, and the player
        # is paused from there
        step = 32768 // self.__fade_length
        count = min(length // 2, self.__fading_out)
        __ramp(samples, count, self.__fading_out * step, -step)
        self.__fading_out -= count
        if self.__fading_out:
            return
        __ramp(memoryview(samples)[count * 2:length], length // 2 - count, 0, 0)    # Zeroed, any length
        self.__state = WavPlayer.PAUSE
        # Heard once the ring ahead of it has played
        self.__silent_at = time.ticks_add(time.ticks_ms(), self.__ring_ms)

    def __fades(self):
        # Whether the sound can fade, which reads it as 16-bit samples
        return self.__mode == WavPlayer.MODE_TONE or self.__wav_file.bits_per_sample == 16

    def __arm_hold(self, from_drive):
        # The computer's first write waits while the sound goes quiet
        self.__from_drive = from_drive
        self.__stopping = False
        self.__standing_aside = False
        self.__aside_silent = False
        if __DriveFile is not None:
            self.__holding = __hold_writes(self.WRITE_HOLD_MS)
            self.__was_busy = __drive_busy()
            self.__writes_seen = __drive_writes()

    def __end_hold(self):
        # Puts back the hold the sound replaced and lets any write it held go
        if self.__holding is not None:
            __hold_writes(self.__holding)
            __release_writes()
            self.__holding = None

    def __write_arrived(self):
        # Whether the computer began writing since the last refill. Busy turns true as its
        # first write is held, before the flash changes, and stays true a second after the
        # last, so while busy only a write landing counts, such as a copy already under way
        busy = __drive_busy()
        writes = __drive_writes()
        arrived = busy and (not self.__was_busy or writes != self.__writes_seen)
        self.__was_busy = busy
        self.__writes_seen = writes
        return arrived

    def __wait_out_writes(self):
        # Quiet with the amplifier off, so the held write goes. The sound fades back in once the
        # computer has finished, which busy turning false marks a second after its last write
        if not self.__aside_silent:
            self.__aside_silent = True
            __release_writes()
        elif not __drive_busy():
            self.__was_busy = False
            # A WAV whose file can say the computer rewrote it ends where it did
            changed = getattr(self.__wav_file.wav_file, "changed", None) \
                if self.__mode == WavPlayer.MODE_WAV else None
            if changed is not None and changed():
                self.__end_sound()
            else:
                self.resume()

    def __end_sound(self):
        self.__stopping = False
        self.__standing_aside = False
        self.__aside_silent = False
        if self.__mode == WavPlayer.MODE_WAV:
            self.__wav_file.close()
            self.__state = WavPlayer.FLUSH
        else:
            self.__state = WavPlayer.STOP
        # Off before any held write goes
        self.__amplify(False)
        self.__end_hold()

    def __amplify(self, on):
        # The amplifier sounds at every flash write's stall even in silence, so it is on only
        # while there is something to hear. Switching it in silence is silent
        if self.__enable is not None and on != self.__amp_on:
            self.__amp_on = on
            if on:
                self.__enable.on()
            else:
                self.__enable.off()

    def __write(self, samples):
        self.__written = True
        self.__audio_out.write(samples)

    def __i2s_callback(self, _):
        # Each callback's write is what brings the next callback, so one that raises before
        # writing, such as a Ctrl-C landing here, would end playback for good. It writes
        # silence first. A second write would replace the first, so only where none was made
        self.__written = False
        try:
            self.__refill()
        except BaseException:
            if not self.__written:
                self.__audio_out.write(self.__silence_samples)
            raise

    def __refill(self):
        # PLAY
        if self.__state == WavPlayer.PLAY:
            if self.__mode == WavPlayer.MODE_WAV:
                # The computer's first write is held until the WAV is quiet, fading out where it
                # can. One from the USB drive then ends, its reads safe only while the write is
                # held, and any other stands aside until the computer has finished
                if self.__holding is not None and not self.__stopping and not self.__standing_aside \
                        and self.__write_arrived():
                    self.__stopping = self.__from_drive
                    self.__standing_aside = not self.__from_drive
                    if self.__wav_file.bits_per_sample == 16:
                        if not self.__fading_out:
                            self.__fading_out = self.__fade_length
                    else:
                        if self.__stopping:
                            self.__end_sound()
                        else:
                            self.__state = WavPlayer.PAUSE
                            self.__silent_at = time.ticks_add(time.ticks_ms(), self.__ring_ms)
                        self.__write(self.__silence_samples)
                        return
                try:
                    if self.__loop_wav:  # Looped playback
                        loop_read = 0
                        while loop_read < self.WAV_BUFFER_LENGTH:
                            num_read = self.__wav_file.readinto(self.__wav_samples_mv[loop_read:])      # Read the next section of the WAV file
                            loop_read += num_read
                            if num_read == 0:
                                _ = self.__wav_file.seek(0)    # Play again, so advance to first byte of sample data
                                self._loop_count += 1
                        if self.__fade:
                            self.__fade_in(self.__wav_samples_mv, loop_read)
                        if self.__fading_out:
                            self.__fade_out(self.__wav_samples_mv, loop_read)
                        self.__write(self.__wav_samples_mv)
                        return

                    num_read = self.__wav_file.readinto(self.__wav_samples_mv)  # Single shot playback
                except OSError:
                    # The file went away beneath the player, a drive file replaced by
                    # the computer being the way that happens. The sound ends cleanly
                    # rather than raising out of the callback
                    self.__end_sound()
                    self.__write(self.__silence_samples)
                    return

                if num_read:
                    if self.__fade:
                        self.__fade_in(self.__wav_samples_mv, num_read)
                    if self.__fading_out:
                        self.__fade_out(self.__wav_samples_mv, num_read)
                    self.__write(self.__wav_samples_mv[: num_read])   # We are within the file, so write out the next audio samples
                else:
                    self.__write(self.__silence_samples)              # Play silence to end this callback

                # Have we reached the end of the file? (num_read is either 0 or a short read)
                if num_read < self.WAV_BUFFER_LENGTH:
                    self.__wav_file.close()                                 # Stop playing, so close the file
                    self.__state = WavPlayer.FLUSH                          # and enter the flush state on the next callback
                    self.__end_hold()

            else:
                if self.__queued_samples is not None:
                    self.__tone_samples = self.__queued_samples
                    self.__tone_scaled = self.__queued_scaled
                    self.__queued_samples = None
                # A tone stands aside for the computer's writes, fading out before the held one goes
                if self.__holding is not None and not self.__stopping and not self.__standing_aside \
                        and self.__write_arrived():
                    self.__standing_aside = True
                    if not self.__fading_out:
                        self.__fading_out = self.__fade_length
                if self.__fade or self.__fading_out:
                    # The tone's buffer repeats, so a fade scales a copy of it
                    scaled = self.__tone_scaled
                    scaled[:] = self.__tone_samples
                    if self.__fade:
                        self.__fade_in(scaled, len(scaled))
                    if self.__fading_out:
                        self.__fade_out(scaled, len(scaled))
                    self.__write(scaled)
                else:
                    self.__write(self.__tone_samples)

        # PAUSE or STOP
        elif self.__state == WavPlayer.PAUSE or self.__state == WavPlayer.STOP:
            # Check if the sound has ended, or a pause's fade has played out of the ring
            if self.__state == WavPlayer.STOP or time.ticks_diff(time.ticks_ms(), self.__silent_at) >= 0:
                self.__amplify(False)
                if self.__state == WavPlayer.PAUSE:
                    if self.__stopping:
                        self.__end_sound()
                    elif self.__standing_aside:
                        self.__wait_out_writes()
            self.__write(self.__silence_samples)                  # Play silence

        # FLUSH
        elif self.__state == WavPlayer.FLUSH:
            # Flush is used to allow the residual audio samples in the internal buffer to be written
            # to the I2S peripheral. This step avoids part of the sound file from being cut off
            if self.__flush_count > 0:
                self.__flush_count -= 1
            else:
                self.__state = WavPlayer.STOP                               # Enter the stop state on the next callback
            self.__write(self.__silence_samples)                  # Play silence

        # NONE
        elif self.__state == WavPlayer.NONE:
            pass
