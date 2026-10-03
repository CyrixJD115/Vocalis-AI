import wave
import os
import logging
from const import TMP_DIR

logger = logging.getLogger(__name__)

STREAM_INPUT_FILE = os.path.join(TMP_DIR, "in.wav")
STREAM_OUTPUT_FILE = os.path.join(TMP_DIR, "out.wav")

class IORecorder:
    def __init__(self, input_sampling_rate: int, output_sampling_rate: int):
        self.fi = None
        self.fo = None
        self.open(input_sampling_rate, output_sampling_rate)

    def _clear(self):
        self.close()
        self._clearFile(STREAM_INPUT_FILE)
        self._clearFile(STREAM_OUTPUT_FILE)

    def _clearFile(self, filename: str):
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except OSError as e:
                # F.e. when another voice changer instance holds the file open
                logger.warning(f"Cannot remove old recording file {filename}: {e}")

    def open(self, input_sampling_rate: int, output_sampling_rate: int):
        self._clear()

        # Normally created by main.py during startup; make the recorder
        # self-sufficient in case it is instantiated before that.
        os.makedirs(TMP_DIR, exist_ok=True)

        try:
            self.fi = wave.open(STREAM_INPUT_FILE, "wb")
            self.fi.setnchannels(1)
            self.fi.setsampwidth(2)
            self.fi.setframerate(input_sampling_rate)

            self.fo = wave.open(STREAM_OUTPUT_FILE, "wb")
            self.fo.setnchannels(1)
            self.fo.setsampwidth(2)
            self.fo.setframerate(output_sampling_rate)
        except OSError as e:
            # Recording is a side feature; do not take the whole server down
            # when the wav files cannot be created (locked by another
            # instance, read-only storage, etc.)
            logger.warning(f"Server audio recording is unavailable: {e}")
            self.close()
        logger.debug(f"Opened recording files: {STREAM_INPUT_FILE}, {STREAM_OUTPUT_FILE}")

    def write_input(self, wav):
        # Drop the data if the recorder is closed instead of raising:
        # this runs on the audio thread where a closed recorder is a
        # normal transient state after stopping a recording.
        if self.fi is None:
            return
        self.fi.writeframes(wav)

    def write_output(self, wav):
        if self.fo is None:
            return
        self.fo.writeframes(wav)

    def close(self):
        if self.fi is not None:
            self.fi.close()
            self.fi = None
        if self.fo is not None:
            self.fo.close()
            self.fo = None
