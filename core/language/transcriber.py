"""语音转录器抽象基类。"""

from abc import ABC, abstractmethod
from typing import Dict, List


class Transcriber(ABC):
    """将音频转录为带时间戳的文字稿。"""

    @abstractmethod
    def transcribe(self, audio_path: str) -> List[Dict]:
        """返回 [{'start': 0.0, 'end': 2.3, 'text': '你好'}, ...]"""
