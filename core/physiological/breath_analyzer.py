"""呼吸率分析 — 从面部 RGB 信号的低频成分提取呼吸频率。"""

import numpy as np

from .rppg_analyzer import RPPGAnalyzer


class BreathAnalyzer(RPPGAnalyzer):
    """从面部绿色通道低频信号估算呼吸率 (breaths per minute)。

    使用与心率相同的前端采集，但频率窗口为 0.1-0.5 Hz (6-30 BPM)。
    """

    def _extract_pulse(self, rgb_data: np.ndarray) -> np.ndarray:
        n = rgb_data.shape[0]
        if n < 64:
            return np.zeros(n)
        green = rgb_data[:, 1] - rgb_data[:, 1].mean()
        return self._bandpass(green, self._fps, low=0.1, high=0.5)

    def _compute_heart_rate(self, signal: np.ndarray) -> float:
        return self._dominant_freq(signal, self._fps, freq_range=(0.1, 0.5))
