import numpy as np
import time
from const import SERVER_DEVICE_SAMPLE_RATES

from queue import Queue
import logging
from voice_changer.VoiceChangerSettings import VoiceChangerSettings
from voice_changer.Local.AudioDeviceList import checkSamplingRate, list_audio_device
import sounddevice as sd
import librosa

from voice_changer.utils.VoiceChangerModel import AudioInOutFloat
from typing import Union, Protocol

logger = logging.getLogger(__name__)

ERR_SAMPLE_RATE_NOT_SUPPORTED = """Specified sample rate is not supported by all selected audio devices.
Available sample rates:
  [Input]: %s
  [Output]: %s
  [Monitor]: %s"""
ERR_GENERIC_SERVER_AUDIO_ERROR = "A server audio error occurred."
ERR_DEVICE_NOT_SELECTED = (
    "Input or output audio device is not selected. "
    "Select both an input (microphone) and an output (speakers/virtual cable) device in the Device area."
)
ERR_HOST_API_MISMATCH = (
    "Input and output devices use different audio APIs (%s vs %s). "
    "Windows cannot open them in a single stream. Select both devices from the same API "
    "(recommended: 'Windows WASAPI', or 'Windows DirectSound')."
)
ERR_SERVER_AUDIO_START_FAILED = "Failed to open the audio stream: %s"

# Minimum interval between identical errors emitted from the audio callback,
# so a persistent failure does not spam the UI with a toast per audio block.
ERROR_EMIT_INTERVAL = 5.0

class ServerAudioCallbacks(Protocol):
    def on_audio(self, unpackedData: AudioInOutFloat) -> tuple[AudioInOutFloat, list[Union[int, float]]]:
        ...

    def emit_to(self, volume: float, performance: list[float], err: tuple[str, str] | None):
        ...

class ServerAudio:
    def __init__(self, callbacks: ServerAudioCallbacks, settings: VoiceChangerSettings):
        self.settings = settings
        self.callbacks = callbacks
        self.mon_wav = None
        self.serverAudioInputDevices = None
        self.serverAudioOutputDevices = None
        self.monQueue = Queue()
        self.performance = [0, 0, 0]

        self.stream = None
        self.monitor = None

        self.running = False

        self._last_error: tuple[str, str] | None = None
        self._last_error_time = 0.0

    def _emit_error_throttled(self, err: tuple[str, str]):
        """Emit a callback-thread error at most once per ERROR_EMIT_INTERVAL,
        keeping the UI informed without flooding it on every audio block."""
        now = time.time()
        if self._last_error != err or now - self._last_error_time >= ERROR_EMIT_INTERVAL:
            self._last_error = err
            self._last_error_time = now
            self.callbacks.emit_to(0, self.performance, err)

    def getServerInputAudioDevice(self, index: int):
        audioinput, _ = list_audio_device()
        serverAudioDevice = [x for x in audioinput if x.index == index]
        if len(serverAudioDevice) > 0:
            return serverAudioDevice[0]
        else:
            return None

    def getServerOutputAudioDevice(self, index: int):
        _, audiooutput = list_audio_device()
        serverAudioDevice = [x for x in audiooutput if x.index == index]
        if len(serverAudioDevice) > 0:
            return serverAudioDevice[0]
        else:
            return None

    ###########################################
    # Callback Section
    ###########################################

    def _processData(self, indata: np.ndarray):
        indata = indata * self.settings.serverInputAudioGain
        unpackedData = librosa.to_mono(indata.T)
        return self.callbacks.on_audio(unpackedData)

    def _processDataWithTime(self, indata: np.ndarray):
        out_wav, vol, perf, err = self._processData(indata)
        self.performance = perf
        self.callbacks.emit_to(vol, self.performance, err)
        return out_wav

    def audio_stream_callback(self, indata: np.ndarray, outdata: np.ndarray, frames, times, status):
        try:
            out_wav = self._processDataWithTime(indata)
            outputChannels = outdata.shape[1]
            outdata[:] = (np.repeat(out_wav, outputChannels).reshape(-1, outputChannels) * self.settings.serverOutputAudioGain)
        except Exception as e:
            self._emit_error_throttled(('ERR_GENERIC_SERVER_AUDIO_ERROR', f"{ERR_GENERIC_SERVER_AUDIO_ERROR} ({e})"))
            logger.exception(e)
            outdata.fill(0)

    def audio_stream_callback_mon_queue(self, indata: np.ndarray, outdata: np.ndarray, frames, times, status):
        try:
            out_wav = self._processDataWithTime(indata)
            self.monQueue.put(out_wav)
            outputChannels = outdata.shape[1]
            outdata[:] = (np.repeat(out_wav, outputChannels).reshape(-1, outputChannels) * self.settings.serverOutputAudioGain)
        except Exception as e:
            self._emit_error_throttled(('ERR_GENERIC_SERVER_AUDIO_ERROR', f"{ERR_GENERIC_SERVER_AUDIO_ERROR} ({e})"))
            logger.exception(e)
            outdata.fill(0)

    def audio_monitor_callback(self, outdata: np.ndarray, frames, times, status):
        try:
            if self.settings.serverMonitorMuted:
                # Mute for the user only: keep draining the monitor queue so
                # unmuting resumes instantly instead of replaying a backlog,
                # while the output device (f.e. a virtual cable) keeps playing.
                while True:
                    try:
                        self.monQueue.get_nowait()
                    except Exception:  # NOQA: BLE001 queue.Empty
                        break
                outdata.fill(0)
                return
            mon_wav = self.monQueue.get()
            while self.monQueue.qsize() > 0:
                self.monQueue.get()
            outputChannels = outdata.shape[1]
            outdata[:] = (np.repeat(mon_wav, outputChannels).reshape(-1, outputChannels) * self.settings.serverMonitorAudioGain)
        except Exception as e:
            self._emit_error_throttled(('ERR_GENERIC_SERVER_AUDIO_ERROR', f"{ERR_GENERIC_SERVER_AUDIO_ERROR} ({e})"))
            logger.exception(e)
            outdata.fill(0)

    ###########################################
    # Main Loop Section
    ###########################################
    def run_no_monitor(self, block_frame: int, inputMaxChannel: int, outputMaxChannel: int, inputExtraSetting, outputExtraSetting):
        self.stream = sd.Stream(
            callback=self.audio_stream_callback,
            latency='low',
            dtype="float32",
            device=(self.settings.serverInputDeviceId, self.settings.serverOutputDeviceId),
            blocksize=block_frame,
            samplerate=self.settings.serverInputAudioSampleRate,
            channels=(inputMaxChannel, outputMaxChannel),
            extra_settings=(inputExtraSetting, outputExtraSetting)
        )
        self.stream.start()

    def run_with_monitor(self, block_frame: int, inputMaxChannel: int, outputMaxChannel: int, monitorMaxChannel: int, inputExtraSetting, outputExtraSetting, monitorExtraSetting):
        self.stream = sd.Stream(
            callback=self.audio_stream_callback_mon_queue,
            latency='low',
            dtype="float32",
            device=(self.settings.serverInputDeviceId, self.settings.serverOutputDeviceId),
            blocksize=block_frame,
            samplerate=self.settings.serverInputAudioSampleRate,
            channels=(inputMaxChannel, outputMaxChannel),
            extra_settings=(inputExtraSetting, outputExtraSetting)
        )
        self.monitor = sd.OutputStream(
            callback=self.audio_monitor_callback,
            dtype="float32",
            device=self.settings.serverMonitorDeviceId,
            blocksize=block_frame,
            samplerate=self.settings.serverMonitorAudioSampleRate,
            channels=monitorMaxChannel,
            extra_settings=monitorExtraSetting
        )
        self.stream.start()
        self.monitor.start()

    def stop(self):
        self.running = False
        if self.stream is not None:
            self.stream.close()
            self.stream = None
        if self.monitor is not None:
            self.monitor.close()
            self.monitor = None

    ###########################################
    # Start Section
    ###########################################
    def start(self):
        self.stop()
        self._last_error = None
        self._last_error_time = 0.0

        sd._terminate()
        sd._initialize()

        # Device 特定
        serverInputAudioDevice = self.getServerInputAudioDevice(self.settings.serverInputDeviceId)
        serverOutputAudioDevice = self.getServerOutputAudioDevice(self.settings.serverOutputDeviceId)
        serverMonitorAudioDevice = self.getServerOutputAudioDevice(self.settings.serverMonitorDeviceId)

        # Deviceがなかったら中断
        if serverInputAudioDevice is None or serverOutputAudioDevice is None:
            missing = []
            if serverInputAudioDevice is None:
                missing.append("input")
            if serverOutputAudioDevice is None:
                missing.append("output")
            logger.error(f"Device is not selected: {', '.join(missing)}")
            self.callbacks.emit_to(0, self.performance, ('ERR_DEVICE_NOT_SELECTED', ERR_DEVICE_NOT_SELECTED))
            return

        # Windows (and most PortAudio backends) cannot combine devices from
        # different host APIs in one full-duplex stream (PaErrorCode -9993).
        if serverInputAudioDevice.hostAPI != serverOutputAudioDevice.hostAPI:
            err = ERR_HOST_API_MISMATCH % (serverInputAudioDevice.hostAPI, serverOutputAudioDevice.hostAPI)
            logger.error(err)
            self.callbacks.emit_to(0, self.performance, ('ERR_HOST_API_MISMATCH', err))
            return

        # Generate ExtraSetting
        wasapiExclusiveMode = bool(self.settings.exclusiveMode)

        inputChannels = serverInputAudioDevice.maxInputChannels
        inputExtraSetting = None
        if "WASAPI" in serverInputAudioDevice.hostAPI:
            inputExtraSetting = sd.WasapiSettings(exclusive=wasapiExclusiveMode, auto_convert=not wasapiExclusiveMode)
        elif "ASIO" in serverInputAudioDevice.hostAPI and self.settings.asioInputChannel != -1:
            inputExtraSetting = sd.AsioSettings(channel_selectors=[self.settings.asioInputChannel])
            inputChannels = 1

        outputChannels = serverOutputAudioDevice.maxOutputChannels
        outputExtraSetting = None
        if "WASAPI" in serverOutputAudioDevice.hostAPI:
            outputExtraSetting = sd.WasapiSettings(exclusive=wasapiExclusiveMode, auto_convert=not wasapiExclusiveMode)
        elif "ASIO" in serverOutputAudioDevice.hostAPI and self.settings.asioOutputChannel != -1:
            outputExtraSetting = sd.AsioSettings(channel_selectors=[self.settings.asioOutputChannel])
            outputChannels = 1

        monitorExtraSetting = None
        if serverMonitorAudioDevice is not None and "WASAPI" in serverMonitorAudioDevice.hostAPI:
            monitorExtraSetting = sd.WasapiSettings(exclusive=wasapiExclusiveMode, auto_convert=not wasapiExclusiveMode)

        logger.info("Devices:")
        logger.info(f"  [Input]: {serverInputAudioDevice} {inputExtraSetting}")
        logger.info(f"  [Output]: {serverOutputAudioDevice}, {outputExtraSetting}")
        logger.info(f"  [Monitor]: {serverMonitorAudioDevice}, {monitorExtraSetting}")

        # サンプリングレート
        # 同一サンプリングレートに統一（変換時にサンプルが不足する場合があるため。パディング方法が明らかになれば、それぞれ設定できるかも）
        self.settings.serverInputAudioSampleRate = self.settings.serverAudioSampleRate
        self.settings.serverOutputAudioSampleRate = self.settings.serverAudioSampleRate
        self.settings.serverMonitorAudioSampleRate = self.settings.serverAudioSampleRate

        # Sample Rate Check (each device is checked with the settings the real
        # stream will use; WASAPI shared mode converts sample rates, so any
        # requested rate is valid there unless exclusive mode is requested).
        inputAudioSampleRateAvailable = checkSamplingRate(self.settings.serverInputDeviceId, self.settings.serverInputAudioSampleRate, "input", exclusive=wasapiExclusiveMode)
        outputAudioSampleRateAvailable = checkSamplingRate(self.settings.serverOutputDeviceId, self.settings.serverOutputAudioSampleRate, "output", exclusive=wasapiExclusiveMode)
        monitorAudioSampleRateAvailable = checkSamplingRate(self.settings.serverMonitorDeviceId, self.settings.serverMonitorAudioSampleRate, "output", exclusive=wasapiExclusiveMode) if serverMonitorAudioDevice else True

        logger.info("Sample Rate:")
        logger.info(f"  [Input]: {self.settings.serverInputAudioSampleRate} -> {inputAudioSampleRateAvailable}")
        logger.info(f"  [Output]: {self.settings.serverOutputAudioSampleRate} -> {outputAudioSampleRateAvailable}")
        if serverMonitorAudioDevice is not None:
            logger.info(f"  [Monitor]: {self.settings.serverMonitorAudioSampleRate} -> {monitorAudioSampleRateAvailable}")

        # FIXME: Ideally, there are two options:
        # 1. UI must be provided with all sample rates and select only valid combinations of sample rates.
        # 2. Server must pick the default device sample rate automatically so UI doesn't have to bother.
        # This must be removed once it's done.
        if not inputAudioSampleRateAvailable or not outputAudioSampleRateAvailable or not monitorAudioSampleRateAvailable:
            logger.info("Checking Available Sample Rate:")
            availableInputSampleRate = []
            availableOutputSampleRate = []
            availableMonitorSampleRate = []
            for sr in SERVER_DEVICE_SAMPLE_RATES:
                if checkSamplingRate(self.settings.serverInputDeviceId, sr, "input", exclusive=wasapiExclusiveMode):
                    availableInputSampleRate.append(sr)
                if checkSamplingRate(self.settings.serverOutputDeviceId, sr, "output", exclusive=wasapiExclusiveMode):
                    availableOutputSampleRate.append(sr)
                if serverMonitorAudioDevice is not None:
                    if checkSamplingRate(self.settings.serverMonitorDeviceId, sr, "output", exclusive=wasapiExclusiveMode):
                        availableMonitorSampleRate.append(sr)
            err = ERR_SAMPLE_RATE_NOT_SUPPORTED % (availableInputSampleRate, availableOutputSampleRate, availableMonitorSampleRate)
            self.callbacks.emit_to(
                0,
                self.performance,
                ('ERR_SAMPLE_RATE_NOT_SUPPORTED', err)
            )
            logger.error(err)
            return

        # FIXME: In UI, block size is calculated based on 48kHz so we convert from 48kHz to input device sample rate.
        block_frame = int((self.settings.serverReadChunkSize * 128 / 48000) * self.settings.serverInputAudioSampleRate)

        try:
            if serverMonitorAudioDevice is None:
                self.run_no_monitor(block_frame, inputChannels, outputChannels, inputExtraSetting, outputExtraSetting)
            else:
                self.run_with_monitor(block_frame, inputChannels, outputChannels, serverMonitorAudioDevice.maxOutputChannels, inputExtraSetting, outputExtraSetting, monitorExtraSetting)
            self.running = True
        except Exception as e:
            # Surface the actual PortAudio error (f.e. "Invalid sample rate
            # [PaErrorCode -9997]") instead of a generic message.
            err = ('ERR_SERVER_AUDIO_START_FAILED', ERR_SERVER_AUDIO_START_FAILED % e)
            self.callbacks.emit_to(0, self.performance, err)
            logger.exception(e)

    ###########################################
    # Info Section
    ###########################################
    def get_info(self):
        data = {}
        try:
            audioinput, audiooutput = list_audio_device()
            self.serverAudioInputDevices = audioinput
            self.serverAudioOutputDevices = audiooutput
        except Exception as e:
            self.callbacks.emit_to(0, self.performance, ('ERR_GENERIC_SERVER_AUDIO_ERROR', ERR_GENERIC_SERVER_AUDIO_ERROR))
            logger.exception(e)

        data["serverAudioInputDevices"] = self.serverAudioInputDevices
        data["serverAudioOutputDevices"] = self.serverAudioOutputDevices
        return data

    def update_settings(self, key: str, val, old_val):
        if key == 'serverAudioStated':
            if val:
                self.start()
            else:
                self.stop()
        if self.running and key in { 'serverInputDeviceId', 'serverOutputDeviceId', 'serverMonitorDeviceId', 'serverReadChunkSize', 'serverAudioSampleRate', 'asioInputChannel', 'asioOutputChannel', 'exclusiveMode' }:
            self.start()
