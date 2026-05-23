"""CHROM (Chrominance-based) rPPG 心率提取。"""

import numpy as np

from .rppg_analyzer import RPPGAnalyzer


class CHROMRPPG(RPPGAnalyzer):
    """CHROM 算法：将 RGB 投影到色度平面消除运动伪影。

    De Haan & Jeanne, "Robust pulse rate from chrominance-based rPPG",
    IEEE Trans. Biomed. Eng., 2013.
    """

    def _extract_pulse(self, rgb_data: np.ndarray) -> np.ndarray:
        n = rgb_data.shape[0]
        if n < 32:
            return np.zeros(n)

        rgb_mean = rgb_data - rgb_data.mean(axis=0)
        r, g, b = rgb_mean[:, 0], rgb_mean[:, 1], rgb_mean[:, 2]

        xs = 3.0 * r - 2.0 * g
        ys = 1.5 * r + g - 1.5 * b

        xsf = self._bandpass(xs, self._fps)
        ysf = self._bandpass(ys, self._fps)

        alpha = np.std(xsf) / (np.std(ysf) + 1e-8)
        return xsf - alpha * ysf

    def _compute_heart_rate(self, signal: np.ndarray) -> float:
        return self._dominant_freq(signal, self._fps)
