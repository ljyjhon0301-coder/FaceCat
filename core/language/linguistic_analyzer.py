"""语言分析器抽象基类。"""

from abc import ABC, abstractmethod
from typing import Dict


class LinguisticAnalyzer(ABC):
    """对转录文字稿做语言特征分析。"""

    @abstractmethod
    def analyze(self, segments: list[dict]) -> Dict:
        """返回 {
            'detachment_score': float,      # 0-1 疏离化总评分
            'passive_ratio': float,          # 被动语态比例
            'first_person_absence': float,   # 第一人称缺失
            'over_specification': float,     # 过度具体化
            'emotional_flatness': float,     # 情感扁平化
        }"""
