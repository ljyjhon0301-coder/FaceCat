"""POS (Plane-Orthogonal-to-Skin) rPPG 心率提取。"""

import numpy as np

from .rppg_analyzer import RPPGAnalyzer


class POSRPPG(RPPGAnalyzer):
    """POS 算法：正交投影到肤色平面提取脉搏。

    Wang et al., "Algorithmic principles of remote PPG",
    IEEE Trans. Biomed. Eng., 2017.
    """

    def _extract_pulse(self, rgb_data: np.ndarray) -> np.ndarray:
        n = rgb_data.shape[0]
        if n < 32:
            return np.zeros(n)

        temporal_mean = rgb_data.mean(axis=0, keepdims=True)
        cn = rgb_data / (temporal_mean + 1e-8) - 1.0

        r, g, b = cn[:, 0], cn[:, 1], cn[:, 2]
        xs = g - b
        ys = -2.0 * r + g + b

        alpha = np.std(xs) / (np.std(ys) + 1e-8)
        s = xs + alpha * ys

        return self._bandpass(s, self._fps)

    def _compute_heart_rate(self, signal: np.ndarray) -> float:
        return self._dominant_freq(signal, self._fps)
