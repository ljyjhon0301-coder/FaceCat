from abc import ABC, abstractmethod
from typing import Dict, List

import numpy as np


class FaceAnalyzer(ABC):
    """面部分析器抽象基类。

    所有面部分析引擎（MediaPipe / CNN / OpenFace）均实现此接口。
    """

    @abstractmethod
    def process_frame(self, frame: np.ndarray) -> Dict:
        """处理单帧 BGR 图像。

        Returns:
            Dict 包含 aus, landmarks, head_pose, blendshapes 四个键。
        """

    @abstractmethod
    def process_video(self, video_path: str) -> List[Dict]:
        """处理视频文件，返回每 100ms 一帧的结果列表。"""
