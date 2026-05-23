from abc import ABC, abstractmethod
from typing import Dict


class AUStrategy(ABC):
    """AU 映射策略抽象基类。

    将 blendshape 强度映射为 FACS Action Unit 强度。
    不同实现可使用查表法、ML 回归等策略。
    """

    @abstractmethod
    def to_au(self, blendshapes: Dict[str, float]) -> Dict[str, float]:
        """输入 blendshape 名称→强度，返回 AU 名称→强度。"""
