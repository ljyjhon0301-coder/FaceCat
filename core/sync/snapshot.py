"""统一四轨时间线快照格式。"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class UnifiedSnapshot:
    """单帧 (100ms) 的统一快照。"""
    timestamp_ms: float

    # 轨1 面部
    aus: Dict[str, float] = field(default_factory=dict)
    head_pose: Dict[str, float] = field(default_factory=dict)

    # 轨2 生理
    heart_rate: float = 0.0
    breath_rate: float = 0.0

    # 轨3 语音
    f0: float = 0.0
    rms: float = 0.0
    jitter: float = 0.0
    shimmer: float = 0.0
    speech_rate: float = 0.0

    # 轨4 语言
    text: str = ''
    detachment_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'timestamp_ms': self.timestamp_ms,
            'face': {
                'aus': self.aus,
                'head_pose': self.head_pose,
            },
            'physiological': {
                'heart_rate': self.heart_rate,
                'breath_rate': self.breath_rate,
            },
            'voice': {
                'f0': self.f0,
                'rms': self.rms,
                'jitter': self.jitter,
                'shimmer': self.shimmer,
                'speech_rate': self.speech_rate,
            },
            'language': {
                'text': self.text,
                'detachment_score': self.detachment_score,
            },
        }


class SnapshotBuilder:
    """从各轨原始输出构建统一快照序列。"""

    def __init__(self):
        self._snapshots: List[UnifiedSnapshot] = []

    def add_frame(self, ts_ms: float, au_dict: Dict, head_pose: Dict,
                  hr: float = 0.0, br: float = 0.0):
        snap = UnifiedSnapshot(
            timestamp_ms=ts_ms,
            aus=dict(au_dict),
            head_pose=dict(head_pose),
            heart_rate=hr,
            breath_rate=br,
        )
        self._snapshots.append(snap)
        return snap

    def apply_voice(self, voice_result: Dict):
        """将语音分析结果逐帧填入最近的快照。"""
        times = voice_result.get('times', [])
        f0_list = voice_result.get('f0', [])
        rms_list = voice_result.get('rms', [])
        jitter = voice_result.get('jitter', 0.0)
        shimmer = voice_result.get('shimmer', 0.0)
        speech_rate = voice_result.get('speech_rate', 0.0)

        for snap in self._snapshots:
            ts_s = snap.timestamp_ms / 1000.0
            snap.jitter = jitter
            snap.shimmer = shimmer
            snap.speech_rate = speech_rate
            for i, t in enumerate(times):
                if abs(t - ts_s) < 0.05 and i < len(f0_list):
                    snap.f0 = f0_list[i]
                    snap.rms = rms_list[i] if i < len(rms_list) else 0.0
                    break

    def apply_language(self, segments: list[dict], detachment: Dict):
        """将转录文字和疏离化评分填入快照。"""
        for snap in self._snapshots:
            ts_s = snap.timestamp_ms / 1000.0
            for seg in segments:
                if seg['start'] <= ts_s <= seg['end']:
                    snap.text = seg.get('text', '')
                    break
            snap.detachment_score = detachment.get('detachment_score', 0.0)

    def to_list(self) -> List[Dict]:
        return [s.to_dict() for s in self._snapshots]
