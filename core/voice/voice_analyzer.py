"""语音分析器抽象基类。"""

from abc import ABC, abstractmethod
from typing import Dict, List


class VoiceAnalyzer(ABC):
    """语音分析器——输入音频路径，输出分段指标。"""

    @abstractmethod
    def analyze(self, audio_path: str) -> Dict:
        """返回 {
            'f0': List[float],           # 基频 (Hz) 逐帧
            'rms': List[float],          # 能量 (RMS)
            'duration': float,           # 总时长 (s)
            'speech_rate': float,        # 语速 (音节/秒)
            'jitter': float,             # 基频扰动
            'shimmer': float,            # 振幅扰动
            'times': List[float],        # 时间戳
        }"""
