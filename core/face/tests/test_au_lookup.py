"""测试 MediaPipeBlendshapeLookupAU.to_au() — 纯函数，零外部依赖。"""

import math

import pytest

from core.face.au_lookup import MediaPipeBlendshapeLookupAU


@pytest.fixture
def mapper():
    return MediaPipeBlendshapeLookupAU()


def test_empty_blendshapes(mapper):
    assert mapper.to_au({}) == {}


def test_missing_keys(mapper):
    aus = mapper.to_au({'mouthSmileLeft': 0.5})
    assert aus['AU12'] == 0.25
    assert aus['AU1'] == 0.0
    assert len(aus) == 18


def test_bilateral_mean(mapper):
    aus = mapper.to_au({
        'browDownLeft': 0.2,
        'browDownRight': 0.6,
    })
    assert math.isclose(aus['AU4'], 0.4)


def test_bilateral_max(mapper):
    aus = mapper.to_au({
        'browOuterUpLeft': 0.3,
        'browOuterUpRight': 0.7,
    })
    assert math.isclose(aus['AU2'], 0.7)


def test_au22_dedicated(mapper):
    aus = mapper.to_au({'mouthFunnel': 0.75})
    assert math.isclose(aus['AU22'], 0.75)


def test_boundary_all_zero(mapper):
    all_bs = {k: 0.0 for k in [
        'browInnerUp', 'browOuterUpLeft', 'browOuterUpRight',
        'browDownLeft', 'browDownRight',
        'eyeWideLeft', 'eyeWideRight',
        'cheekSquintLeft', 'cheekSquintRight',
        'eyeSquintLeft', 'eyeSquintRight',
        'noseSneerLeft', 'noseSneerRight',
        'mouthUpperUpLeft', 'mouthUpperUpRight',
        'mouthSmileLeft', 'mouthSmileRight',
        'mouthDimpleLeft', 'mouthDimpleRight',
        'mouthFrownLeft', 'mouthFrownRight',
        'mouthShrugLower',
        'mouthStretchLeft', 'mouthStretchRight',
        'mouthFunnel',
        'mouthPressLeft', 'mouthPressRight',
        'jawOpen',
    ]}
    # mouthClose 不在此列表 — 默认 1.0 表示嘴唇闭合 → AU25=0
    aus = mapper.to_au(all_bs)
    for k in aus:
        assert aus[k] < 0.01, f'{k} should be near 0, got {aus[k]}'


def test_boundary_all_one(mapper):
    all_bs = {k: 1.0 for k in [
        'browInnerUp', 'browOuterUpLeft', 'browOuterUpRight',
        'browDownLeft', 'browDownRight',
        'eyeWideLeft', 'eyeWideRight',
        'cheekSquintLeft', 'cheekSquintRight',
        'eyeSquintLeft', 'eyeSquintRight',
        'noseSneerLeft', 'noseSneerRight',
        'mouthUpperUpLeft', 'mouthUpperUpRight',
        'mouthSmileLeft', 'mouthSmileRight',
        'mouthDimpleLeft', 'mouthDimpleRight',
        'mouthFrownLeft', 'mouthFrownRight',
        'mouthShrugLower',
        'mouthStretchLeft', 'mouthStretchRight',
        'mouthFunnel',
        'mouthPressLeft', 'mouthPressRight',
        'mouthClose', 'jawOpen',
    ]}
    aus = mapper.to_au(all_bs)
    assert math.isclose(aus['AU1'], 1.0)
    assert math.isclose(aus['AU2'], 1.0)
    assert math.isclose(aus['AU4'], 1.0)
    assert math.isclose(aus['AU12'], 1.0)
    assert math.isclose(aus['AU22'], 1.0)
    assert math.isclose(aus['AU25'], 0.0)
    assert math.isclose(aus['AU26'], 0.6)
    assert math.isclose(aus['AU27'], 1.0)


def test_singleton_default(mapper):
    m1 = MediaPipeBlendshapeLookupAU.default()
    m2 = MediaPipeBlendshapeLookupAU.default()
    assert m1 is m2
