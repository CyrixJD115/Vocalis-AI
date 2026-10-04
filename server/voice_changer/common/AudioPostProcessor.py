"""Real-time post-processing chain applied to converted audio ("Audio Enhancer").

Runs inside the audio callback thread, so every stage is block-based, stateful
and keeps its output length identical to its input length. Parameters are read
from VoiceChangerSettings on each call, which lets the UI tune the chain live
without touching filter state; only coefficient-defining parameters (cutoff
frequencies, sample rate) rebuild their filters.

Chain order:
    high-pass -> low-pass -> noise reduction -> noise gate
    -> EQ (low shelf / mid peak / high shelf) -> de-esser
    -> compressor -> limiter
"""

import logging

import numpy as np
from scipy.signal import lfilter, lfilter_zi

logger = logging.getLogger(__name__)


def db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def lin_to_db(x):
    return 20.0 * np.log10(np.maximum(x, 1e-10))


# RBJ audio-eq-cookbook biquad designs. Coefficients are float64; filtering runs
# in scipy's C loop so this stays well below 1ms for a 24k-sample block.
def _normalize(b0, b1, b2, a0, a1, a2):
    return np.array([b0, b1, b2]) / a0, np.array([1.0, a1 / a0, a2 / a0])


def rbj_highpass(fc: float, sr: float, q: float = 0.7071):
    w0 = 2.0 * np.pi * min(fc, sr * 0.45) / sr
    alpha = np.sin(w0) / (2.0 * q)
    c = np.cos(w0)
    return _normalize((1 + c) / 2, -(1 + c), (1 + c) / 2, 1 + alpha, -2 * c, 1 - alpha)


def rbj_lowpass(fc: float, sr: float, q: float = 0.7071):
    w0 = 2.0 * np.pi * min(fc, sr * 0.45) / sr
    alpha = np.sin(w0) / (2.0 * q)
    c = np.cos(w0)
    return _normalize((1 - c) / 2, (1 - c), (1 - c) / 2, 1 + alpha, -2 * c, 1 - alpha)


def rbj_low_shelf(fc: float, sr: float, gain_db: float, q: float = 0.7071):
    w0 = 2.0 * np.pi * min(fc, sr * 0.45) / sr
    alpha = np.sin(w0) / (2.0 * q)
    c = np.cos(w0)
    A = 10.0 ** (gain_db / 40.0)
    two_sqrtA_alpha = 2.0 * np.sqrt(A) * alpha
    return _normalize(
        A * ((A + 1) - (A - 1) * c + two_sqrtA_alpha),
        2.0 * A * ((A - 1) - (A + 1) * c),
        A * ((A + 1) - (A - 1) * c - two_sqrtA_alpha),
        (A + 1) + (A - 1) * c + two_sqrtA_alpha,
        -2.0 * ((A - 1) + (A + 1) * c),
        (A + 1) + (A - 1) * c - two_sqrtA_alpha,
    )


def rbj_high_shelf(fc: float, sr: float, gain_db: float, q: float = 0.7071):
    w0 = 2.0 * np.pi * min(fc, sr * 0.45) / sr
    alpha = np.sin(w0) / (2.0 * q)
    c = np.cos(w0)
    A = 10.0 ** (gain_db / 40.0)
    two_sqrtA_alpha = 2.0 * np.sqrt(A) * alpha
    return _normalize(
        A * ((A + 1) + (A - 1) * c + two_sqrtA_alpha),
        -2.0 * A * ((A - 1) + (A + 1) * c),
        A * ((A + 1) + (A - 1) * c - two_sqrtA_alpha),
        (A + 1) - (A - 1) * c + two_sqrtA_alpha,
        2.0 * ((A - 1) - (A + 1) * c),
        (A + 1) - (A - 1) * c - two_sqrtA_alpha,
    )


def rbj_peaking(fc: float, sr: float, gain_db: float, q: float = 1.0):
    w0 = 2.0 * np.pi * min(fc, sr * 0.45) / sr
    alpha = np.sin(w0) / (2.0 * q)
    c = np.cos(w0)
    A = 10.0 ** (gain_db / 40.0)
    return _normalize(
        1.0 + alpha * A,
        -2.0 * c,
        1.0 - alpha * A,
        1.0 + alpha / A,
        -2.0 * c,
        1.0 - alpha / A,
    )


class Biquad:
    """Biquad section with persistent state across process() calls."""

    def __init__(self, b, a):
        self.b = b
        self.a = a
        self.zi = np.zeros(2)

    @classmethod
    def make(cls, b, a) -> "Biquad":
        return cls(b, a)

    def set_coefficients(self, b, a):
        if not (np.allclose(self.b, b) and np.allclose(self.a, a)):
            self.b, self.a = b, a
            self.zi = np.zeros(max(len(self.zi), 2))[: len(self.a) - 1]

    def reset(self):
        self.zi = np.zeros_like(self.zi)

    def process(self, x: np.ndarray) -> np.ndarray:
        y, self.zi = lfilter(self.b, self.a, x, zi=self.zi)
        return y.astype(np.float32)


class OnePoleSmoother:
    """One-pole (exponential) smoother with persistent state.

    a = 1 - exp(-1 / (time_seconds * sr)) gives the classic attack/release
    coefficient; the recursion y[n] = a*x[n] + (1-a)*y[n-1] runs in lfilter.
    """

    def __init__(self, sample_rate: float):
        self.sample_rate = sample_rate
        self.a = 1.0
        self.zi = np.zeros(1)

    def set_time(self, time_ms: float):
        time_ms = max(time_ms, 0.01)
        a = 1.0 - np.exp(-1.0 / (time_ms / 1000.0 * self.sample_rate))
        self.a = float(np.clip(a, 0.0, 1.0))

    def reset(self):
        self.zi = np.zeros(1)

    def process(self, x: np.ndarray) -> np.ndarray:
        y, self.zi = lfilter([self.a], [1.0, -(1.0 - self.a)], x, zi=self.zi)
        return y.astype(np.float32)


class EnvelopeFollower:
    """Peak envelope with independent attack/release via max(fast, slow)."""

    def __init__(self, sample_rate: float):
        self.attack = OnePoleSmoother(sample_rate)
        self.release = OnePoleSmoother(sample_rate)

    def set_times(self, attack_ms: float, release_ms: float):
        self.attack.set_time(attack_ms)
        self.release.set_time(release_ms)

    def reset(self):
        self.attack.reset()
        self.release.reset()

    def process(self, x: np.ndarray) -> np.ndarray:
        fast = self.attack.process(x)
        slow = self.release.process(x)
        return np.maximum(fast, slow)


class NoiseGate:
    """RMS-domain gate with fast attack and slow release."""

    def __init__(self, sample_rate: float):
        self.env = EnvelopeFollower(sample_rate)
        self.open_fast = OnePoleSmoother(sample_rate)
        self.close_slow = OnePoleSmoother(sample_rate)
        self.open_fast.set_time(2.0)
        self.close_slow.set_time(120.0)

    def reset(self):
        self.env.reset()
        self.open_fast.reset()
        self.close_slow.reset()

    def process(self, x: np.ndarray, threshold_db: float) -> np.ndarray:
        env = self.env.process(np.abs(x))
        mask = (lin_to_db(env) > threshold_db).astype(np.float32)
        # max(fast, slow) => opens within 2ms, closes over ~120ms
        gain = np.maximum(self.open_fast.process(mask), self.close_slow.process(mask))
        return x * gain


class SpectralNoiseReducer:
    """Streaming STFT spectral-subtraction denoiser.

    Frames are Hann-windowed with 50% overlap. The noise spectrum is tracked
    with an EMA that updates quickly whenever a frame looks like background
    noise and decays slowly during speech. The per-bin gain is over-subtracted
    by `amount` and floored to keep artifacts (musical noise) tolerable.

    The STFT introduces one hop of latency. An internal queue compensates so
    process() always returns exactly len(x) samples (the first block starts
    with ~hop samples of near-silence).
    """

    GAIN_FLOOR = 0.08  # -22 dB minimum per-bin attenuation
    GAIN_SMOOTH_TIME = 0.06  # seconds, temporal gain smoothing

    def __init__(self, sample_rate: float):
        self.sample_rate = sample_rate
        self.N = 1024 if sample_rate <= 48000 else 2048
        self.hop = self.N // 2
        self.win = np.hanning(self.N + 1)[: self.N].astype(np.float32)
        self.win2 = self.win**2
        self.inbuf = np.zeros(self.N - self.hop, dtype=np.float32)
        self.outqueue = np.zeros(0, dtype=np.float32)
        self.noise_power: np.ndarray | None = None
        self.prev_gain: np.ndarray | None = None
        self.gain_smoother = OnePoleSmoother(sample_rate)
        self.gain_smoother.set_time(self.GAIN_SMOOTH_TIME * 1000)

    def reset(self):
        self.inbuf = np.zeros(self.N - self.hop, dtype=np.float32)
        self.outqueue = np.zeros(0, dtype=np.float32)
        self.noise_power = None
        self.prev_gain = None
        self.gain_smoother.reset()

    def process(self, x: np.ndarray, amount: float) -> np.ndarray:
        # amount: 0..1 user scale -> 0..2.5 over-subtraction factor
        beta = 2.5 * float(np.clip(amount, 0.0, 1.0))
        if beta <= 0.01:
            return x

        N, hop, win, win2 = self.N, self.hop, self.win, self.win2
        buf = np.concatenate([self.inbuf, x])
        n_frames = 0 if len(buf) < N else 1 + (len(buf) - N) // hop

        emitted = np.zeros(0, dtype=np.float32)
        if n_frames > 0:
            out_len = (n_frames - 1) * hop + N
            acc = np.zeros(out_len, dtype=np.float64)
            norm = np.zeros(out_len, dtype=np.float64)
            for i in range(n_frames):
                frame = buf[i * hop : i * hop + N]
                spec = np.fft.rfft(frame * win)
                power = np.abs(spec) ** 2
                frame_db = float(lin_to_db(np.sqrt(power.mean())))

                if self.noise_power is None:
                    self.noise_power = power.copy()
                elif frame_db < float(lin_to_db(np.sqrt(self.noise_power.mean()))) + 6.0:
                    # quiet frame: track the noise floor quickly
                    self.noise_power = 0.6 * self.noise_power + 0.4 * power
                else:
                    # active frame: let the estimate creep down only
                    self.noise_power = 0.995 * self.noise_power + 0.005 * power

                gain = np.clip(1.0 - beta * self.noise_power / (power + 1e-10), self.GAIN_FLOOR, 1.0)
                if self.prev_gain is not None:
                    gain = 0.4 * gain + 0.6 * self.prev_gain
                self.prev_gain = gain
                # 3-tap frequency smoothing keeps broadband gain from gating
                gain = np.convolve(gain, [0.25, 0.5, 0.25], mode="same")

                filtered = np.fft.irfft(spec * gain, n=N)
                acc[i * hop : i * hop + N] += filtered * win
                norm[i * hop : i * hop + N] += win2

            # fully-overlapped region: hop .. n_frames*hop
            valid = slice(N - hop, n_frames * hop)
            den = np.maximum(norm[valid], 1e-3)
            emitted = (acc[valid] / den).astype(np.float32)
            self.inbuf = buf[(n_frames - 1) * hop :].copy()

        self.outqueue = np.concatenate([self.outqueue, emitted])
        # Bound the queue in case a caller feeds uneven block sizes
        if len(self.outqueue) > 4 * self.N + 2 * len(x):
            self.outqueue = self.outqueue[-(2 * self.N + len(x)) :]

        if len(self.outqueue) >= len(x):
            out = self.outqueue[: len(x)]
            self.outqueue = self.outqueue[len(x) :]
            return out
        # underrun only happens on the very first block (STFT latency)
        out = np.concatenate([self.outqueue, np.zeros(len(x) - len(self.outqueue), dtype=np.float32)])
        self.outqueue = np.zeros(0, dtype=np.float32)
        return out


class DeEsser:
    """Band-split compressor that tames sibilance above ~5 kHz."""

    def __init__(self, sample_rate: float):
        self.split = Biquad.make(*rbj_highpass(5200.0, sample_rate))
        self.env = EnvelopeFollower(sample_rate)
        self.gain = OnePoleSmoother(sample_rate)
        self.env.set_times(2.0, 60.0)
        self.gain.set_time(8.0)

    def reset(self):
        self.split.reset()
        self.env.reset()
        self.gain.reset()

    def process(self, x: np.ndarray, amount: float) -> np.ndarray:
        # amount 0..10 maps to a de-essing threshold of -8..-48 dB
        threshold_db = -8.0 - 4.0 * float(np.clip(amount, 0.0, 10.0))
        if amount <= 0.01:
            return x
        high = self.split.process(x)
        low = x - high
        env = self.env.process(np.abs(high))
        over = np.maximum(lin_to_db(env) - threshold_db, 0.0)
        target = db_to_lin(-over * (1.0 - 1.0 / 4.0))  # ratio 4:1 on the band
        gain = self.gain.process(target)
        return low + high * gain


class Compressor:
    """Feed-forward compressor on a peak/RMS envelope."""

    def __init__(self, sample_rate: float):
        self.env = EnvelopeFollower(sample_rate)
        self.gain = OnePoleSmoother(sample_rate)
        self.gain.set_time(10.0)
        self._attack = 10.0
        self._release = 100.0

    def reset(self):
        self.env.reset()
        self.gain.reset()

    def process(self, x: np.ndarray, threshold_db: float, ratio: float, attack_ms: float, release_ms: float, makeup_db: float) -> np.ndarray:
        attack_ms = float(np.clip(attack_ms, 0.1, 200.0))
        release_ms = float(np.clip(release_ms, 1.0, 1000.0))
        if attack_ms != self._attack or release_ms != self._release:
            self._attack, self._release = attack_ms, release_ms
            self.env.set_times(attack_ms, release_ms)
        env = self.env.process(np.abs(x))
        over = np.maximum(lin_to_db(env) - threshold_db, 0.0)
        target = db_to_lin(-over * (1.0 - 1.0 / max(ratio, 1.0)))
        gain = self.gain.process(target)
        return x * gain * db_to_lin(makeup_db)


class Limiter:
    """Brickwall limiter: fast envelope, gain clamps signal to the ceiling.

    The gain target brings the envelope exactly to the ceiling (infinite ratio)
    and a final hard clip catches attack transients, so the output can never
    exceed the requested ceiling.
    """

    def __init__(self, sample_rate: float):
        self.env = EnvelopeFollower(sample_rate)
        self.env.set_times(0.1, 40.0)
        self.gain = OnePoleSmoother(sample_rate)
        self.gain.set_time(2.0)

    def reset(self):
        self.env.reset()
        self.gain.reset()

    def process(self, x: np.ndarray, ceiling_db: float) -> np.ndarray:
        ceiling = db_to_lin(ceiling_db)
        env = self.env.process(np.abs(x))
        target = np.minimum(1.0, ceiling / np.maximum(env, 1e-10))
        gain = self.gain.process(target)
        out = x * gain
        # hard clip so an attack transient can never pass the ceiling
        return np.clip(out, -ceiling, ceiling)


class AudioPostProcessor:
    """The full enhancer chain. Owns all DSP state for one audio stream."""

    MIN_BLOCK = 64  # skip tiny buffers (error-path placeholders etc.)

    def __init__(self, settings):
        self.settings = settings
        self.sample_rate = int(settings.inputSampleRate)
        self._was_enabled = False
        self._filter_params: tuple | None = None
        self._build()

    def _build(self):
        s = self.settings
        self.hp = Biquad.make(*rbj_highpass(float(s.enhancerHpFreq), self.sample_rate))
        self.lp = Biquad.make(*rbj_lowpass(float(s.enhancerLpFreq), self.sample_rate))
        self.eq_low = Biquad.make(*rbj_low_shelf(180.0, self.sample_rate, float(s.enhancerEqLow)))
        self.eq_mid = Biquad.make(*rbj_peaking(1200.0, self.sample_rate, float(s.enhancerEqMid)))
        self.eq_high = Biquad.make(*rbj_high_shelf(4000.0, self.sample_rate, float(s.enhancerEqHigh)))
        self.noise_reducer = SpectralNoiseReducer(self.sample_rate)
        self.gate = NoiseGate(self.sample_rate)
        self.de_esser = DeEsser(self.sample_rate)
        self.compressor = Compressor(self.sample_rate)
        self.limiter = Limiter(self.sample_rate)
        self._filter_params = (
            float(s.enhancerHpFreq),
            float(s.enhancerLpFreq),
            float(s.enhancerEqLow),
            float(s.enhancerEqMid),
            float(s.enhancerEqHigh),
        )

    def set_sample_rate(self, sample_rate: int):
        sample_rate = int(sample_rate)
        if sample_rate == self.sample_rate:
            return
        self.sample_rate = sample_rate
        self._build()

    def parameters_changed(self):
        """Rebuild coefficient-dependent stages when their defining params moved."""
        s = self.settings
        params = (
            float(s.enhancerHpFreq),
            float(s.enhancerLpFreq),
            float(s.enhancerEqLow),
            float(s.enhancerEqMid),
            float(s.enhancerEqHigh),
        )
        if params != self._filter_params:
            self._build()

    def reset(self):
        for stage in (self.hp, self.lp, self.eq_low, self.eq_mid, self.eq_high):
            stage.reset()
        self.noise_reducer.reset()
        self.gate.reset()
        self.de_esser.reset()
        self.compressor.reset()
        self.limiter.reset()

    def process(self, x: np.ndarray) -> np.ndarray:
        s = self.settings
        if not int(s.enhancerEnabled):
            self._was_enabled = False
            return x
        if not self._was_enabled:
            # coming back from disabled: stale envelopes would pump, start clean
            self.reset()
            self._was_enabled = True

        if len(x) < self.MIN_BLOCK:
            return x

        # guard the live stream against NaN/inf poisoning every downstream state
        x = np.nan_to_num(np.asarray(x, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)

        if int(s.enhancerHpEnabled):
            x = self.hp.process(x)
        if int(s.enhancerLpEnabled):
            x = self.lp.process(x)
        if int(s.enhancerNrEnabled):
            x = self.noise_reducer.process(x, float(s.enhancerNrAmount) / 100.0)
        if int(s.enhancerGateEnabled):
            x = self.gate.process(x, float(s.enhancerGateThreshold))
        if int(s.enhancerEqEnabled):
            if abs(float(s.enhancerEqLow)) > 0.1:
                x = self.eq_low.process(x)
            if abs(float(s.enhancerEqMid)) > 0.1:
                x = self.eq_mid.process(x)
            if abs(float(s.enhancerEqHigh)) > 0.1:
                x = self.eq_high.process(x)
        if int(s.enhancerDeEssEnabled):
            x = self.de_esser.process(x, float(s.enhancerDeEssAmount))
        if int(s.enhancerCompEnabled):
            x = self.compressor.process(
                x,
                float(s.enhancerCompThreshold),
                float(s.enhancerCompRatio),
                float(s.enhancerCompAttack),
                float(s.enhancerCompRelease),
                float(s.enhancerCompMakeup),
            )
        if int(s.enhancerLimiterEnabled):
            x = self.limiter.process(x, float(s.enhancerLimiterCeiling))

        return np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=-1.0).astype(np.float32)
