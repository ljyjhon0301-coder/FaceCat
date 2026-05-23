"""librosa + parselmouth 语音分析。"""

from typing import Dict, Optional

import numpy as np

from .voice_analyzer import VoiceAnalyzer


class LibrosaVoiceAnalyzer(VoiceAnalyzer):
    """用 librosa 提取基频/能量/语速，parselmouth 提取 jitter/shimmer。"""

    def __init__(self, frame_ms: float = 25.0, hop_ms: float = 10.0):
        self._frame_len = int(frame_ms / 1000.0 * 22050)
        self._hop_len = int(hop_ms / 1000.0 * 22050)

    def analyze(self, audio_path: str) -> Dict:
        import librosa
        y, sr = librosa.load(audio_path, sr=22050, mono=True)
        duration = len(y) / sr

        f0, voiced, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=sr,
            frame_length=2048,
            hop_length=int(sr * 0.01),
        )
        f0 = np.where(np.isnan(f0), 0.0, f0).tolist()
        rms = librosa.feature.rms(
            y=y, frame_length=2048, hop_length=int(sr * 0.01),
        )[0].tolist()
        times = librosa.frames_to_time(
            np.arange(len(f0)), sr=sr, hop_length=int(sr * 0.01),
        ).tolist()
        speech_rate = self._estimate_speech_rate(y, sr, voiced)
        jitter, shimmer = self._compute_jitter_shimmer(audio_path)

        return {
            'f0': f0,
            'rms': rms,
            'duration': float(duration),
            'speech_rate': speech_rate,
            'jitter': jitter,
            'shimmer': shimmer,
            'times': times,
        }

    @staticmethod
    def _estimate_speech_rate(
            y: np.ndarray, sr: int,
            voiced: Optional[np.ndarray]) -> float:
        onset_env = np.abs(y)
        onset_env = onset_env / (np.max(onset_env) + 1e-8)
        onsets = np.diff(onset_env > np.mean(onset_env) * 0.5)
        syllable_count = float(np.sum(onsets > 0))
        duration = len(y) / sr
        if duration < 0.5:
            return 0.0
        return syllable_count / duration

    @staticmethod
    def _compute_jitter_shimmer(audio_path: str):
        try:
            import parselmouth
            snd = parselmouth.Sound(audio_path)
            pulses = parselmouth.praat.call(snd, "To PointProcess (periodic, cc)", 75, 300)

            jitter = parselmouth.praat.call(
                pulses, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
            shimmer = parselmouth.praat.call(
                [snd, pulses], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
            return float(jitter), float(shimmer)
        except Exception:
            return 0.0, 0.0
