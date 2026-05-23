import numpy as np

from core.physiological.rppg_analyzer import RPPGAnalyzer, extract_forehead_roi


def test_dominant_freq_returns_expected_bpm():
    fps = 30.0
    times = np.arange(0.0, 10.0, 1.0 / fps)
    signal = np.sin(2.0 * np.pi * 1.2 * times)

    bpm = RPPGAnalyzer._dominant_freq(signal, fps)

    assert abs(bpm - 72.0) < 3.0


def test_extract_forehead_roi_returns_rgb_mean():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[:, :] = [10, 20, 30]
    landmarks = [[0.0, 0.0, 0.0] for _ in range(468)]
    landmarks[10] = [0.5, 0.2, 0.0]
    landmarks[151] = [0.5, 0.4, 0.0]
    landmarks[104] = [0.3, 0.3, 0.0]
    landmarks[334] = [0.7, 0.3, 0.0]

    rgb = extract_forehead_roi(landmarks, frame)

    assert np.allclose(rgb, [30.0, 20.0, 10.0])
