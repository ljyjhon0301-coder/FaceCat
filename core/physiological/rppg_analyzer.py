"""rPPG 心率分析器抽象基类。"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import numpy as np


def extract_forehead_roi(landmarks, frame):
    """从 468 点 FaceMesh 中提取额头 ROI 的 RGB 均值。

    MediaPipe 额头关键点：10(顶部中点)、151(眉心偏上)、
    104(左)、334(右)。取四边形内像素均值。
    """
    h, w = frame.shape[:2]
    indices = [10, 151, 104, 334]
    pts = []
    for idx in indices:
        if idx < len(landmarks):
            lm = landmarks[idx]
            pts.append([int(lm[0] * w), int(lm[1] * h)])
    pts = np.array(pts, dtype=np.int32)

    mask = np.zeros((h, w), dtype=np.uint8)
    cv2 = _import_cv2()
    cv2.fillPoly(mask, [pts], 255)
    roi = cv2.bitwise_and(frame, frame, mask=mask)

    r = np.mean(roi[:, :, 2][mask > 0]) if np.any(mask) else 0.0
    g = np.mean(roi[:, :, 1][mask > 0]) if np.any(mask) else 0.0
    b = np.mean(roi[:, :, 0][mask > 0]) if np.any(mask) else 0.0
    return np.array([r, g, b])


def _import_cv2():
    import cv2
    return cv2


class RPPGAnalyzer(ABC):
    """rPPG 分析器抽象基类。

    子类实现 _compute_heart_rate 即可接入不同算法（CHROM/POS）。
    """

    def __init__(self, fps: float = 30.0):
        self._fps = fps
        self._rgb_history: List[np.ndarray] = []
        self._max_history = int(fps * 30.0)

    def feed_rgb(self, rgb: np.ndarray):
        """输入一帧的额头 RGB 均值 [R, G, B]。"""
        self._rgb_history.append(rgb)
        if len(self._rgb_history) > self._max_history:
            self._rgb_history.pop(0)

    @abstractmethod
    def _compute_heart_rate(self, signal: np.ndarray) -> float:
        """子类实现：从时序信号计算心率 (BPM)。"""

    def get_heart_rate(self) -> float:
        """从累积的 RGB 历史中估算心率。"""
        if len(self._rgb_history) < self._fps * 3:
            return 0.0
        signal = self._compute_signal()
        return self._compute_heart_rate(signal)

    def _compute_signal(self) -> np.ndarray:
        data = np.array(self._rgb_history)
        return self._extract_pulse(data)

    @abstractmethod
    def _extract_pulse(self, rgb_data: np.ndarray) -> np.ndarray:
        """从 RGB 矩阵 (N×3) 中提取脉搏信号。"""

    @staticmethod
    def _bandpass(signal: np.ndarray, fps: float,
                  low: float = 0.7, high: float = 4.0) -> np.ndarray:
        """Butterworth 带通滤波。"""
        from scipy.signal import butter, filtfilt
        nyq = fps / 2.0
        order = 4
        b, a = butter(order, [low / nyq, high / nyq], btype='band')
        return filtfilt(b, a, signal)

    @staticmethod
    def _dominant_freq(signal: np.ndarray, fps: float,
                       freq_range: Tuple[float, float] = (0.7, 4.0)) -> float:
        """FFT 取主频 → BPM。"""
        n = len(signal)
        if n < 32:
            return 0.0
        freqs = np.fft.rfftfreq(n, 1.0 / fps)
        fft = np.abs(np.fft.rfft(signal))
        mask = (freqs >= freq_range[0]) & (freqs <= freq_range[1])
        if not np.any(mask):
            return 0.0
        peak_idx = np.argmax(fft[mask])
        return freqs[mask][peak_idx] * 60.0
