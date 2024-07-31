# SPDX-FileCopyrightText: 2024 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

import os
import math
import struct
from machine import I2S, Pin

"""
A class for playing Wav files out of an I2S audio amp. It can also play pure tones.
This code is based heavily on the work of Mike Teachman, at:
https://github.com/miketeachman/micropython-i2s-examples/blob/master/examples/wavplayer.py
"""


class WavReader:
    def __init__(self, file):
        self.wav_file = open(file, "rb")
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
        self.size = int(self.sample_rate * self.bits_per_sample / 8)

        wav_file.seek(40)
        self.sub_chunk2_size = struct.unpack("<I", wav_file.read(4))[0]

        wav_file.seek(self.offset)

    def seek(self, pos):
        self.wav_file.seek(pos + self.offset)

    def tell(self):
        return self.wav_file.tell()

    def readinto(self, buf):
        max_bytes = self.size - (self.wav_file.tell() - self.offset)
        max_bytes = min(len(buf), max_bytes)
        return self.wav_file.readinto(buf[:max_bytes])

    def close(self):
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

    def __init__(self, id, sck_pin, ws_pin, sd_pin, amp_enable=None, ibuf_len=INTERNAL_BUFFER_LENGTH, root="/"):
        self.__id = id
        self.__sck_pin = sck_pin
        self.__ws_pin = ws_pin
        self.__sd_pin = sd_pin
        self.__ibuf_len = ibuf_len
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
        self.__flush_count = 0
        self.__audio_out = None

        # Allocate a small array of blank audio samples used for silence
        self.__silence_samples = bytearray(self.SILENCE_BUFFER_LENGTH)

        # Allocate a larger array for WAV audio samples, using a memoryview for more efficient access
        self.__wav_samples_mv = memoryview(bytearray(self.WAV_BUFFER_LENGTH))

        # Reserve a variable for audio samples used for tones
        self.__tone_samples = None
        self.__queued_samples = None

    def set_root(self, root):
        self.__root = root.rstrip("/") + "/"

    def play_wav(self, wav_file, loop=False):
        if os.listdir(self.__root).count(wav_file) == 0:
            raise ValueError(f"'{wav_file}' not found")

        self.__stop_i2s()                                       # Stop any active playback and terminate the I2S instance

        self.__wav_file = open(self.__root + wav_file, "rb")    # Open the chosen WAV file in read-only, binary mode
        self.__loop_wav = loop                                  # Record if the user wants the file to loop
        self._loop_count = 0                                    # Count loops for debugging purposes

        # Parse the WAV file, returning the necessary parameters to initialise I2S communication
        self.__wav_file = WavReader(self.__root + wav_file)

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
            self.__start_i2s(bits=self.TONE_BITS_PER_SAMPLE,
                             format=I2S.MONO,
                             rate=self.TONE_SAMPLE_RATE,
                             state=WavPlayer.PLAY,
                             mode=WavPlayer.MODE_TONE)
        else:
            self.__queued_samples = samples
            self.__state = WavPlayer.PLAY

    def pause(self):
        if self.__state == WavPlayer.PLAY:
            self.__state = WavPlayer.PAUSE          # Enter the pause state on the next callback

    def resume(self):
        if self.__state == WavPlayer.PAUSE:
            self.__state = WavPlayer.PLAY           # Enter the play state on the next callback

    def stop(self):
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

    def is_paused(self):
        return self.__state == WavPlayer.PAUSE

    def __start_i2s(self, bits=16, format=I2S.MONO, rate=44_100, state=STOP, mode=MODE_WAV):
        import gc
        gc.collect()
        self.__audio_out = I2S(
            self.__id,
            sck=self.__sck_pin,
            ws=self.__ws_pin,
            sd=self.__sd_pin,
            mode=I2S.TX,
            bits=bits,
            format=format,
            rate=rate,
            ibuf=self.__ibuf_len,
        )

        self.__state = state
        self.__mode = mode
        self.__flush_count = self.__ibuf_len // self.SILENCE_BUFFER_LENGTH + 1
        self.__audio_out.irq(self.__i2s_callback)
        self.__audio_out.write(self.__silence_samples)

        if self.__enable is not None:
            self.__enable.on()

    def __stop_i2s(self):
        self.stop()                     # Stop any active playback
        while self.is_playing():        # and wait for it to complete
            pass

        if self.__enable is not None:
            self.__enable.off()

        if self.__audio_out is not None:
            self.__audio_out.deinit()   # Deinit any active I2S comms

        self.__state == WavPlayer.NONE  # Return to the none state

    def __i2s_callback(self, arg):
        # PLAY
        if self.__state == WavPlayer.PLAY:
            if self.__mode == WavPlayer.MODE_WAV:
                if self.__loop_wav:  # Looped playback
                    loop_read = 0
                    while loop_read < self.WAV_BUFFER_LENGTH:
                        num_read = self.__wav_file.readinto(self.__wav_samples_mv[loop_read:])      # Read the next section of the WAV file
                        loop_read += num_read
                        if num_read == 0:
                            _ = self.__wav_file.seek(0)    # Play again, so advance to first byte of sample data
                            self._loop_count += 1
                    self.__audio_out.write(self.__wav_samples_mv)

                else:  # Single shot playback
                    num_read = self.__wav_file.readinto(self.__wav_samples_mv)

                    if num_read:
                        self.__audio_out.write(self.__wav_samples_mv[: num_read])   # We are within the file, so write out the next audio samples
                    else:
                        self.__audio_out.write(self.__silence_samples)              # In both cases play silence to end this callback

                    # Have we reached the end of the file? (num_read is either 0 or a short read)
                    if num_read < self.WAV_BUFFER_LENGTH:
                        # Do we want to loop the WAV playback?
                        self.__wav_file.close()                                 # Stop playing, so close the file
                        self.__state = WavPlayer.FLUSH                          # and enter the flush state on the next callback

            else:
                if self.__queued_samples is not None:
                    self.__tone_samples = self.__queued_samples
                    self.__queued_samples = None
                self.__audio_out.write(self.__tone_samples)

        # PAUSE or STOP
        elif self.__state == WavPlayer.PAUSE or self.__state == WavPlayer.STOP:
            self.__audio_out.write(self.__silence_samples)                  # Play silence

        # FLUSH
        elif self.__state == WavPlayer.FLUSH:
            # Flush is used to allow the residual audio samples in the internal buffer to be written
            # to the I2S peripheral. This step avoids part of the sound file from being cut off
            if self.__flush_count > 0:
                self.__flush_count -= 1
            else:
                self.__state = WavPlayer.STOP                               # Enter the stop state on the next callback
            self.__audio_out.write(self.__silence_samples)                  # Play silence

        # NONE
        elif self.__state == WavPlayer.NONE:
            pass
