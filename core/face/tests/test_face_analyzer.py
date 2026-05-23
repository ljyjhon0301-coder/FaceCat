"""测试 FaceAnalyzer 抽象基类和 MediaPipeFaceAnalyzer 接口一致性。"""

import pytest

from core.face import FaceAnalyzer, MediaPipeFaceAnalyzer


def test_abstract_cannot_instantiate():
    with pytest.raises(TypeError):
        FaceAnalyzer()


def test_concrete_subclass():
    analyzer = MediaPipeFaceAnalyzer()
    assert isinstance(analyzer, FaceAnalyzer)
    analyzer.close()


def test_process_frame_signature():
    assert hasattr(MediaPipeFaceAnalyzer, 'process_frame')
    assert callable(MediaPipeFaceAnalyzer.process_frame)


def test_process_video_signature():
    assert hasattr(MediaPipeFaceAnalyzer, 'process_video')
    assert callable(MediaPipeFaceAnalyzer.process_video)
