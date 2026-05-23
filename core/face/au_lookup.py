from typing import Dict

from .au_strategy import AUStrategy


class MediaPipeBlendshapeLookupAU(AUStrategy):
    """将 MediaPipe 52 blendshapes 映射为 FACS Action Units。

    映射规则遵循 FACS 定义与 MediaPipe blendshape 语义的对应关系。
    双侧 blendshape 取均值，部分取最大值。
    """

    _instance: 'MediaPipeBlendshapeLookupAU | None' = None

    @classmethod
    def default(cls) -> 'MediaPipeBlendshapeLookupAU':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def to_au(self, blendshapes: Dict[str, float]) -> Dict[str, float]:
        if not blendshapes:
            return {}

        s = blendshapes

        return {
            # 眉毛组
            'AU1': s.get('browInnerUp', 0.0),
            'AU2': max(
                s.get('browOuterUpLeft', 0.0),
                s.get('browOuterUpRight', 0.0)),
            'AU4': (
                s.get('browDownLeft', 0.0)
                + s.get('browDownRight', 0.0)) / 2.0,

            # 眼部组
            'AU5': (
                s.get('eyeWideLeft', 0.0)
                + s.get('eyeWideRight', 0.0)) / 2.0,
            'AU6': (
                s.get('cheekSquintLeft', 0.0)
                + s.get('cheekSquintRight', 0.0)) / 2.0,
            'AU7': (
                s.get('eyeSquintLeft', 0.0)
                + s.get('eyeSquintRight', 0.0)) / 2.0,

            # 鼻部组 — noseSneer 信号弱，double 增强 + 上唇提升辅助
            'AU9': max(
                (s.get('noseSneerLeft', 0.0)
                 + s.get('noseSneerRight', 0.0)),
                (s.get('mouthUpperUpLeft', 0.0)
                 + s.get('mouthUpperUpRight', 0.0)) * 0.3,
            ),

            # 唇部组
            'AU10': (
                s.get('mouthUpperUpLeft', 0.0)
                + s.get('mouthUpperUpRight', 0.0)) / 2.0,
            'AU12': (
                s.get('mouthSmileLeft', 0.0)
                + s.get('mouthSmileRight', 0.0)) / 2.0,
            'AU14': (
                s.get('mouthDimpleLeft', 0.0)
                + s.get('mouthDimpleRight', 0.0)) / 2.0,
            'AU15': (
                s.get('mouthFrownLeft', 0.0)
                + s.get('mouthFrownRight', 0.0)) / 2.0,
            'AU17': s.get('mouthShrugLower', 0.0),
            'AU20': (
                s.get('mouthStretchLeft', 0.0)
                + s.get('mouthStretchRight', 0.0)) / 2.0,
            'AU22': s.get('mouthFunnel', 0.0),
            'AU23': (
                s.get('mouthPressLeft', 0.0)
                + s.get('mouthPressRight', 0.0)) / 2.0,

            # 下颌组 — AU25 仅在下颌未动时量嘴唇分离
            'AU25': (1.0 - s.get('mouthClose', 1.0))
                    * max(0.0, 1.0 - s.get('jawOpen', 0.0) * 3.0),
            'AU26': s.get('jawOpen', 0.0) * 0.6,
            'AU27': s.get('jawOpen', 0.0),
        }
