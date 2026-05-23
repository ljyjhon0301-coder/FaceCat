"""测试 MediaPipeFaceAnalyzer._estimate_head_pose() — 接口校验。

注意：solvePnP 的精度依赖真实面部几何，mock 数据无法准确验证数值。
因此主要验证函数签名的正确性。
"""

import pytest

from core.face import MediaPipeFaceAnalyzer


def _make_landmarks():
    """基于真实面部比例的 synthetic 5 关键点 landmark 列表。"""
    lm = [[0.0, 0.0, 0.0] for _ in range(478)]
    lm[1] = [0.50, 0.55, -0.05]
    lm[33] = [0.38, 0.40, -0.12]
    lm[263] = [0.62, 0.40, -0.12]
    lm[168] = [0.50, 0.35, -0.08]
    lm[152] = [0.50, 0.80, -0.10]
    return lm


class TestEstimateHeadPose:

    @pytest.fixture(scope='class')
    def analyzer(self):
        a = MediaPipeFaceAnalyzer()
        yield a
        a.close()

    def test_returns_valid_dict(self, analyzer):
        landmarks = _make_landmarks()
        pose = analyzer._estimate_head_pose(landmarks, 480, 640)
        assert isinstance(pose, dict)
        assert set(pose.keys()) == {'yaw', 'pitch', 'roll'}
        assert all(isinstance(v, float) for v in pose.values())

    def test_all_landmarks_at_origin(self, analyzer):
        landmarks = [[0.0, 0.0, 0.0] for _ in range(478)]
        pose = analyzer._estimate_head_pose(landmarks, 480, 640)
        assert set(pose.keys()) == {'yaw', 'pitch', 'roll'}

    def test_result_in_degrees(self, analyzer):
        landmarks = _make_landmarks()
        pose = analyzer._estimate_head_pose(landmarks, 480, 640)
        for val in pose.values():
            assert -180.0 <= val <= 180.0, f'{val} out of range'
