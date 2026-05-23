import numpy as np

from core.voice import LibrosaVoiceAnalyzer


def test_estimate_speech_rate_short_audio_returns_zero():
    y = np.zeros(1000, dtype=float)

    rate = LibrosaVoiceAnalyzer._estimate_speech_rate(y, 22050, None)

    assert rate == 0.0


def test_estimate_speech_rate_detects_energy_onsets():
    sr = 22050
    y = np.zeros(sr * 2, dtype=float)
    y[1000:1200] = 1.0
    y[12000:12200] = 1.0

    rate = LibrosaVoiceAnalyzer._estimate_speech_rate(y, sr, None)

    assert rate > 0.0
