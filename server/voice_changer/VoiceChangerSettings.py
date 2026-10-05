# from const import PitchExtractorType
from typing import NamedTuple

import logging
logger = logging.getLogger(__name__)

IGNORED_KEYS = { 'version' }
STATEFUL_KEYS = [ 'serverAudioStated', 'passThrough', 'recordIO' ]

def _js_bool_to_bool(value: str) -> bool:
    return value == 'true'

class SetPropertyResult(NamedTuple):
    error: bool
    old_value: str | int | float | bool | None

class VoiceChangerSettings:

    def to_dict(self) -> dict:
        return self.get_properties()

    # TODO: This is a temporary kostyl.
    # Stateful keys must not be part of the settings. Need to rework audio handling logic
    def to_dict_stateless(self) -> dict:
        data = self.to_dict()
        for key in STATEFUL_KEYS:
            del data[key]
        return data

    def get_properties(self) -> dict:
        return {
            key: value.fget(self)
            for key, value in self.__class__.__dict__.items()
            if isinstance(value, property)
        }

    def set_properties(self, data: dict) -> list[SetPropertyResult]:
        return [
            self.set_property(key, value)
            for key, value in data.items()
        ]

    def set_property(self, key, value) -> SetPropertyResult:
        cls = self.__class__
        if key in IGNORED_KEYS:
            return SetPropertyResult(error=False, old_value=None)
        if key not in cls.__dict__:
            logger.error(f'Failed to set setting: {key} does not exist')
            return SetPropertyResult(error=True, old_value=None)
        p = cls.__dict__[key]
        if not isinstance(p, property):
            return SetPropertyResult(error=True, old_value=None)
        if p.fset is None:
            logger.error(f'Failed to set setting: {key} is immutable.')
            return SetPropertyResult(error=True, old_value=None)
        old_value = p.fget(self)
        p.fset(self, value)
        return SetPropertyResult(error=False, old_value=old_value)

    def get_property(self, key):
        return getattr(self, key)

    # Immutable
    _version: str = 'v1'

    @property
    def version(self):
        return self._version

    # General settings
    _modelSlotIndex: int = -1

    _outputSampleRate: int = 48000
    _inputSampleRate: int = 48000

    _crossFadeOverlapSize: float = 0.1
    _serverReadChunkSize: int = 192
    _extraConvertSize: float = 0.5
    _gpu: int = -1
    _forceFp32: int = 0
    _disableJit: int = 0

    _passThrough: bool = False
    _recordIO: int = 0

    @property
    def modelSlotIndex(self):
        return self._modelSlotIndex

    @modelSlotIndex.setter
    def modelSlotIndex(self, idx: str):
        self._modelSlotIndex = int(idx)

    @property
    def inputSampleRate(self):
        return self._inputSampleRate

    @inputSampleRate.setter
    def inputSampleRate(self, sample_rate: str):
        self._inputSampleRate = int(sample_rate)

    @property
    def outputSampleRate(self):
        return self._outputSampleRate

    @outputSampleRate.setter
    def outputSampleRate(self, sample_rate: str):
        self._outputSampleRate = int(sample_rate)

    @property
    def passThrough(self):
        return self._passThrough

    @passThrough.setter
    def passThrough(self, enable: str):
        self._passThrough = _js_bool_to_bool(enable)

    @property
    def recordIO(self):
        return self._recordIO

    @recordIO.setter
    def recordIO(self, enable: str):
        self._recordIO = int(enable)

    @property
    def gpu(self):
        return self._gpu

    @gpu.setter
    def gpu(self, gpu: str):
        self._gpu = int(gpu)

    @property
    def extraConvertSize(self):
        return self._extraConvertSize

    @extraConvertSize.setter
    def extraConvertSize(self, size: str):
        self._extraConvertSize = float(size)

    @property
    def serverReadChunkSize(self):
        return self._serverReadChunkSize

    @serverReadChunkSize.setter
    def serverReadChunkSize(self, size: str):
        self._serverReadChunkSize = int(size)

    @property
    def crossFadeOverlapSize(self):
        return self._crossFadeOverlapSize

    @crossFadeOverlapSize.setter
    def crossFadeOverlapSize(self, size: str):
        self._crossFadeOverlapSize = float(size)

    @property
    def forceFp32(self):
        return self._forceFp32

    @forceFp32.setter
    def forceFp32(self, enable: str):
        self._forceFp32 = int(enable)

    @property
    def disableJit(self):
        return self._disableJit

    @disableJit.setter
    def disableJit(self, enable: str):
        self._disableJit = int(enable)

    # Server Audio settings
    # 48000 is the native rate of most modern Windows devices and virtual
    # cables (VB-CABLE defaults to 48000), avoiding extra resampling stages.
    _serverAudioStated: int = 0
    _enableServerAudio: int = 0
    _serverInputAudioSampleRate: int = 48000
    _serverOutputAudioSampleRate: int = 48000
    _serverMonitorAudioSampleRate: int = 48000

    _serverAudioSampleRate: int = 48000

    _serverInputDeviceId: int = -1
    _serverOutputDeviceId: int = -1
    _serverMonitorDeviceId: int = -1  # -1 でモニター無効
    _serverInputAudioGain: float = 1.0
    _serverOutputAudioGain: float = 1.0
    _serverMonitorAudioGain: float = 1.0
    # 1 = the monitor (local hearing) stream outputs silence while the output
    # device (f.e. a virtual cable feeding Discord/OBS) keeps playing.
    _serverMonitorMuted: int = 0

    _exclusiveMode: int = 0
    _asioInputChannel: int = -1
    _asioOutputChannel: int = -1

    @property
    def serverAudioStated(self):
        return self._serverAudioStated

    @serverAudioStated.setter
    def serverAudioStated(self, enabled: str):
        self._serverAudioStated = int(enabled)

    @property
    def enableServerAudio(self):
        return self._enableServerAudio

    @enableServerAudio.setter
    def enableServerAudio(self, enabled: str):
        self._enableServerAudio = int(enabled)

    @property
    def serverInputAudioSampleRate(self):
        return self._serverInputAudioSampleRate

    @serverInputAudioSampleRate.setter
    def serverInputAudioSampleRate(self, rate: str):
        self._serverInputAudioSampleRate = int(rate)

    @property
    def serverOutputAudioSampleRate(self):
        return self._serverOutputAudioSampleRate

    @serverOutputAudioSampleRate.setter
    def serverOutputAudioSampleRate(self, rate: str):
        self._serverOutputAudioSampleRate = int(rate)

    @property
    def serverMonitorAudioSampleRate(self):
        return self._serverMonitorAudioSampleRate

    @serverMonitorAudioSampleRate.setter
    def serverMonitorAudioSampleRate(self, rate: str):
        self._serverMonitorAudioSampleRate = int(rate)

    @property
    def serverAudioSampleRate(self):
        return self._serverAudioSampleRate

    @serverAudioSampleRate.setter
    def serverAudioSampleRate(self, rate: str):
        self._serverAudioSampleRate = int(rate)

    @property
    def serverInputDeviceId(self):
        return self._serverInputDeviceId

    @serverInputDeviceId.setter
    def serverInputDeviceId(self, id: str):
        self._serverInputDeviceId = int(id)

    @property
    def serverOutputDeviceId(self):
        return self._serverOutputDeviceId

    @serverOutputDeviceId.setter
    def serverOutputDeviceId(self, id: str):
        self._serverOutputDeviceId = int(id)

    @property
    def serverMonitorDeviceId(self):
        return self._serverMonitorDeviceId

    @serverMonitorDeviceId.setter
    def serverMonitorDeviceId(self, id: str):
        self._serverMonitorDeviceId = int(id)

    @property
    def serverInputAudioGain(self):
        return self._serverInputAudioGain

    @serverInputAudioGain.setter
    def serverInputAudioGain(self, gain: str):
        self._serverInputAudioGain = float(gain)

    @property
    def serverOutputAudioGain(self):
        return self._serverOutputAudioGain

    @serverOutputAudioGain.setter
    def serverOutputAudioGain(self, gain: str):
        self._serverOutputAudioGain = float(gain)

    @property
    def serverMonitorAudioGain(self):
        return self._serverMonitorAudioGain

    @serverMonitorAudioGain.setter
    def serverMonitorAudioGain(self, gain: str):
        self._serverMonitorAudioGain = float(gain)

    @property
    def serverMonitorMuted(self):
        return self._serverMonitorMuted

    @serverMonitorMuted.setter
    def serverMonitorMuted(self, muted: str):
        self._serverMonitorMuted = int(muted)

    @property
    def exclusiveMode(self):
        return self._exclusiveMode

    @exclusiveMode.setter
    def exclusiveMode(self, enabled: str):
        self._exclusiveMode = int(enabled)

    @property
    def asioInputChannel(self):
        return self._asioInputChannel

    @asioInputChannel.setter
    def asioInputChannel(self, id: str):
        self._asioInputChannel = int(id)

    @property
    def asioOutputChannel(self):
        return self._asioOutputChannel

    @asioOutputChannel.setter
    def asioOutputChannel(self, id: str):
        self._asioOutputChannel = int(id)

    # RVCv2 settings
    _dstId: int = 0

    _f0Detector: str = "rmvpe_onnx"
    _tran: int = 0
    _formantShift: float = 0
    _useONNX: int = 0

    _silentThreshold: int = -90

    _indexRatio: float = 0
    _protect: float = 0.5
    _silenceFront: int = 1

    @property
    def dstId(self):
        return self._dstId

    @dstId.setter
    def dstId(self, id: str):
        self._dstId = int(id)

    @property
    def f0Detector(self):
        return self._f0Detector

    @f0Detector.setter
    def f0Detector(self, pitch_extractor_type: str):
        self._f0Detector = pitch_extractor_type

    @property
    def tran(self):
        return self._tran

    @tran.setter
    def tran(self, tone: str):
        self._tran = int(tone)

    @property
    def formantShift(self):
        return self._formantShift

    @formantShift.setter
    def formantShift(self, shift_size: str):
        self._formantShift = float(shift_size)

    @property
    def useONNX(self):
        return self._useONNX

    @useONNX.setter
    def useONNX(self, enabled: str):
        self._useONNX = int(enabled)

    @property
    def silentThreshold(self):
        return self._silentThreshold

    @silentThreshold.setter
    def silentThreshold(self, threshold: str):
        self._silentThreshold = int(threshold)

    @property
    def indexRatio(self):
        return self._indexRatio

    @indexRatio.setter
    def indexRatio(self, ratio: str):
        self._indexRatio = float(ratio)

    @property
    def protect(self):
        return self._protect

    @protect.setter
    def protect(self, protect: str):
        self._protect = float(protect)

    @property
    def silenceFront(self):
        return self._silenceFront

    @silenceFront.setter
    def silenceFront(self, enable: str):
        self._silenceFront = int(enable)

    # Audio Enhancer (post-processing chain) settings
    _enhancerEnabled: int = 0

    _enhancerGateEnabled: int = 0
    _enhancerGateThreshold: float = -60

    _enhancerHpEnabled: int = 0
    _enhancerHpFreq: float = 80
    _enhancerLpEnabled: int = 0
    _enhancerLpFreq: float = 12000

    _enhancerNrEnabled: int = 0
    _enhancerNrAmount: float = 50

    _enhancerDeEssEnabled: int = 0
    _enhancerDeEssAmount: float = 3

    _enhancerEqEnabled: int = 0
    _enhancerEqLow: float = 0
    _enhancerEqMid: float = 0
    _enhancerEqHigh: float = 0

    _enhancerCompEnabled: int = 0
    _enhancerCompThreshold: float = -24
    _enhancerCompRatio: float = 4
    _enhancerCompAttack: float = 10
    _enhancerCompRelease: float = 100
    _enhancerCompMakeup: float = 0

    _enhancerLimiterEnabled: int = 1
    _enhancerLimiterCeiling: float = -1

    @property
    def enhancerEnabled(self):
        return self._enhancerEnabled

    @enhancerEnabled.setter
    def enhancerEnabled(self, val):
        self._enhancerEnabled = int(val)

    @property
    def enhancerGateEnabled(self):
        return self._enhancerGateEnabled

    @enhancerGateEnabled.setter
    def enhancerGateEnabled(self, val):
        self._enhancerGateEnabled = int(val)

    @property
    def enhancerGateThreshold(self):
        return self._enhancerGateThreshold

    @enhancerGateThreshold.setter
    def enhancerGateThreshold(self, val):
        self._enhancerGateThreshold = float(val)

    @property
    def enhancerHpEnabled(self):
        return self._enhancerHpEnabled

    @enhancerHpEnabled.setter
    def enhancerHpEnabled(self, val):
        self._enhancerHpEnabled = int(val)

    @property
    def enhancerHpFreq(self):
        return self._enhancerHpFreq

    @enhancerHpFreq.setter
    def enhancerHpFreq(self, val):
        self._enhancerHpFreq = float(val)

    @property
    def enhancerLpEnabled(self):
        return self._enhancerLpEnabled

    @enhancerLpEnabled.setter
    def enhancerLpEnabled(self, val):
        self._enhancerLpEnabled = int(val)

    @property
    def enhancerLpFreq(self):
        return self._enhancerLpFreq

    @enhancerLpFreq.setter
    def enhancerLpFreq(self, val):
        self._enhancerLpFreq = float(val)

    @property
    def enhancerNrEnabled(self):
        return self._enhancerNrEnabled

    @enhancerNrEnabled.setter
    def enhancerNrEnabled(self, val):
        self._enhancerNrEnabled = int(val)

    @property
    def enhancerNrAmount(self):
        return self._enhancerNrAmount

    @enhancerNrAmount.setter
    def enhancerNrAmount(self, val):
        self._enhancerNrAmount = float(val)

    @property
    def enhancerDeEssEnabled(self):
        return self._enhancerDeEssEnabled

    @enhancerDeEssEnabled.setter
    def enhancerDeEssEnabled(self, val):
        self._enhancerDeEssEnabled = int(val)

    @property
    def enhancerDeEssAmount(self):
        return self._enhancerDeEssAmount

    @enhancerDeEssAmount.setter
    def enhancerDeEssAmount(self, val):
        self._enhancerDeEssAmount = float(val)

    @property
    def enhancerEqEnabled(self):
        return self._enhancerEqEnabled

    @enhancerEqEnabled.setter
    def enhancerEqEnabled(self, val):
        self._enhancerEqEnabled = int(val)

    @property
    def enhancerEqLow(self):
        return self._enhancerEqLow

    @enhancerEqLow.setter
    def enhancerEqLow(self, val):
        self._enhancerEqLow = float(val)

    @property
    def enhancerEqMid(self):
        return self._enhancerEqMid

    @enhancerEqMid.setter
    def enhancerEqMid(self, val):
        self._enhancerEqMid = float(val)

    @property
    def enhancerEqHigh(self):
        return self._enhancerEqHigh

    @enhancerEqHigh.setter
    def enhancerEqHigh(self, val):
        self._enhancerEqHigh = float(val)

    @property
    def enhancerCompEnabled(self):
        return self._enhancerCompEnabled

    @enhancerCompEnabled.setter
    def enhancerCompEnabled(self, val):
        self._enhancerCompEnabled = int(val)

    @property
    def enhancerCompThreshold(self):
        return self._enhancerCompThreshold

    @enhancerCompThreshold.setter
    def enhancerCompThreshold(self, val):
        self._enhancerCompThreshold = float(val)

    @property
    def enhancerCompRatio(self):
        return self._enhancerCompRatio

    @enhancerCompRatio.setter
    def enhancerCompRatio(self, val):
        self._enhancerCompRatio = float(val)

    @property
    def enhancerCompAttack(self):
        return self._enhancerCompAttack

    @enhancerCompAttack.setter
    def enhancerCompAttack(self, val):
        self._enhancerCompAttack = float(val)

    @property
    def enhancerCompRelease(self):
        return self._enhancerCompRelease

    @enhancerCompRelease.setter
    def enhancerCompRelease(self, val):
        self._enhancerCompRelease = float(val)

    @property
    def enhancerCompMakeup(self):
        return self._enhancerCompMakeup

    @enhancerCompMakeup.setter
    def enhancerCompMakeup(self, val):
        self._enhancerCompMakeup = float(val)

    @property
    def enhancerLimiterEnabled(self):
        return self._enhancerLimiterEnabled

    @enhancerLimiterEnabled.setter
    def enhancerLimiterEnabled(self, val):
        self._enhancerLimiterEnabled = int(val)

    @property
    def enhancerLimiterCeiling(self):
        return self._enhancerLimiterCeiling

    @enhancerLimiterCeiling.setter
    def enhancerLimiterCeiling(self, val):
        self._enhancerLimiterCeiling = float(val)
