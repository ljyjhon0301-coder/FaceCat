"""实时不一致性与欺骗线索分析器。

消费已有数据流（EmotionResult + AU + 头部姿态 + 心率），
维护滚动窗口，输出9个统计线索。

所有线索是数学统计量，不是说谎判断。
"""

from collections import deque
from typing import Dict, List, Optional, Tuple

import numpy as np


# ── 用于不对称检测的双侧AU对 ──
_BILATERAL_AUS = ['AU2', 'AU6', 'AU9', 'AU10', 'AU12',
                  'AU14', 'AU15', 'AU20', 'AU23']

# ── 左侧和右侧对应的blendshape key后缀 ──
_LEFT_KEYS = {'AU2': 'browOuterUpLeft',
              'AU6': 'cheekSquintLeft',
              'AU7': 'eyeSquintLeft',
              'AU9': 'noseSneerLeft',
              'AU10': 'mouthUpperUpLeft',
              'AU12': 'mouthSmileLeft',
              'AU14': 'mouthDimpleLeft',
              'AU15': 'mouthFrownLeft',
              'AU20': 'mouthStretchLeft',
              'AU23': 'mouthPressLeft'}

_RIGHT_KEYS = {'AU2': 'browOuterUpRight',
               'AU6': 'cheekSquintRight',
               'AU7': 'eyeSquintRight',
               'AU9': 'noseSneerRight',
               'AU10': 'mouthUpperUpRight',
               'AU12': 'mouthSmileRight',
               'AU14': 'mouthDimpleRight',
               'AU15': 'mouthFrownRight',
               'AU20': 'mouthStretchRight',
               'AU23': 'mouthPressRight'}


class DeceptionCueAnalyzer:
    """滚动窗口不一致性分析器。

    Usage:
        analyzer = DeceptionCueAnalyzer(window_size=30)
        for each_frame:
            analyzer.feed(emotion_result, au_dict, head_pose)
            cues = analyzer.get_cues(hr, br)
    """

    EMOTION_LABELS = {
        'happiness': '快乐', 'sadness': '悲伤',
        'surprise': '惊讶', 'fear': '恐惧',
        'anger': '愤怒', 'disgust': '厌恶',
        'contempt': '轻蔑',
    }

    def __init__(self, window_size: int = 30):
        self._win_size = window_size

        # 三条并行时间序列
        self._emotions: deque = deque(maxlen=window_size)  # list of dict
        self._aus: deque = deque(maxlen=window_size)        # list of dict
        self._poses: deque = deque(maxlen=window_size)      # list of dict

        # 缓存最后已知的blendshapes（用于不对称计算需要原始左右值）
        self._last_blendshapes: Dict[str, float] = {}

    def feed_blendshapes(self, blendshapes: Dict[str, float]):
        """单独喂入原始blendshapes（不对称计算需要）。"""
        self._last_blendshapes = blendshapes

    def feed(self, emotion_result, au_dict: Dict[str, float],
             head_pose: Dict[str, float]):
        """每帧调用一次：喂入当前帧所有数据。"""
        emo_dict = dict(emotion_result.emotions)
        emo_dict['_dominant'] = emotion_result.dominant_emotion
        emo_dict['_valence'] = emotion_result.valence
        emo_dict['_arousal'] = emotion_result.arousal
        emo_dict['_is_micro'] = emotion_result.is_micro

        self._emotions.append(emo_dict)
        self._aus.append(au_dict)
        self._poses.append(head_pose)

    def get_cues(self, heart_rate: float = 0.0,
                 breath_rate: float = 0.0) -> Dict:
        """输出当前所有线索。窗口未填满时返回空或0。"""
        if len(self._emotions) < 3:
            return self._empty_cues()

        return {
            # 帧内混合
            'affect_blend': self._calc_affect_blend(),
            'masking': self._calc_masking(),

            # 时序不稳定
            'lability': self._calc_lability(),
            'micro_count': self._calc_micro_count(),

            # AU/pose直接衍生
            'fake_smile': self._calc_fake_smile(),
            'asymmetry': self._calc_asymmetry(),
            'motor_suppression': self._calc_motor_suppression(),
            'cognitive_load': self._calc_cognitive_load(),

            # 跨模态
            'physio_mismatch': self._calc_physio_mismatch(heart_rate),
        }

    # ── 内部算法 ──

    def _calc_affect_blend(self) -> Dict:
        """情绪混合：主情绪与次级情绪的效价冲突程度。"""
        latest = self._emotions[-1]
        dom = latest.get('_dominant', 'neutral')
        scores = {k: v for k, v in latest.items()
                  if not k.startswith('_') and k != dom}

        if not scores:
            return {'score': 0.0, 'detail': '无次级情绪'}

        top_sec = max(scores, key=lambda k: scores[k])
        sec_score = scores[top_sec]

        if sec_score < 0.05:
            return {'score': 0.0, 'detail': '次级情绪微弱'}

        dom_valence = _VALENCE_MAP.get(dom, 0.0)
        sec_valence = _VALENCE_MAP.get(top_sec, 0.0)

        # 冲突程度 = 效价差 × 次级情绪强度
        conflict = abs(dom_valence - sec_valence) * sec_score
        name = self.EMOTION_LABELS.get(top_sec, top_sec)

        return {
            'score': min(1.0, conflict),
            'detail': f'{name}({sec_score:.0%})' if sec_score > 0.05 else '',
        }

    def _calc_masking(self) -> Dict:
        """情绪掩蔽：主情绪为正时，窗口内出现负情绪的频次。"""
        pos_emotions = {'happiness'}
        neg_emotions = {'sadness', 'fear', 'anger', 'disgust', 'contempt'}

        last_few = list(self._emotions)[-min(15, len(self._emotions)):]

        dom = last_few[-1].get('_dominant', 'neutral')
        if dom not in pos_emotions:
            return {'score': 0.0, 'detail': '当前主情绪非正'}

        # 检查窗口内有几次负情绪闪现
        flashes = 0
        for emo in last_few:
            for neg_ek in neg_emotions:
                score = emo.get(neg_ek, 0.0)
                if score > 0.15:
                    flashes += 1
                    break

        rate = flashes / len(last_few)
        return {
            'score': min(1.0, rate * 3.0),
            'detail': f'{flashes}次/{len(last_few)}帧' if flashes > 0 else '',
        }

    def _calc_lability(self) -> Dict:
        """表达不稳：窗口内主导情绪切换频率。"""
        doms = [e.get('_dominant', 'neutral') for e in self._emotions]
        switches = sum(1 for i in range(1, len(doms))
                       if doms[i] != doms[i - 1])
        rate = switches / len(doms)
        return {
            'score': min(1.0, rate * 5.0),
            'detail': f'{switches}次切换/{len(doms)}帧',
        }

    def _calc_micro_count(self) -> Dict:
        """微表情计数：窗口内is_micro的帧数。"""
        count = sum(1 for e in self._emotions if e.get('_is_micro', False))
        return {
            'score': min(1.0, count / max(1, len(self._emotions)) * 5.0),
            'detail': f'{count}次' if count > 0 else '',
        }

    def _calc_fake_smile(self) -> Dict:
        """假笑指数：AU12(微笑) 高但 AU6(脸颊/Duchenne) 低。"""
        if not self._aus:
            return {'score': 0.0, 'detail': ''}

        latest_au = self._aus[-1]
        au12 = latest_au.get('AU12', 0.0)
        au6 = latest_au.get('AU6', 0.0)

        if au12 < 0.1:
            return {'score': 0.0, 'detail': '无微笑'}

        fake = max(0.0, au12 - au6)
        return {
            'score': min(1.0, fake * 2.0),
            'detail': f'AU12={au12:.0%} AU6={au6:.0%}',
        }

    def _calc_asymmetry(self) -> Dict:
        """左右不对称：双侧AU的左右差值绝对值均值。

        需要原始blendshapes。如果不可用，退化为AU的左右均值差。
        """
        if not self._aus:
            return {'score': 0.0, 'detail': ''}

        latest_au = self._aus[-1]

        # 优先使用blendshapes原始左右值
        diffs = []
        for au_code in _BILATERAL_AUS:
            l_key = _LEFT_KEYS.get(au_code)
            r_key = _RIGHT_KEYS.get(au_code)
            if l_key and r_key:
                l_val = self._last_blendshapes.get(l_key, 0.0)
                r_val = self._last_blendshapes.get(r_key, 0.0)
                if l_val > 0.0 or r_val > 0.0:
                    diffs.append(abs(l_val - r_val))

        if not diffs:
            return {'score': 0.0, 'detail': ''}

        avg_asym = sum(diffs) / len(diffs)
        return {
            'score': min(1.0, avg_asym * 5.0),
            'detail': f'均值 {avg_asym:.2f}',
        }

    def _calc_motor_suppression(self) -> Dict:
        """运动抑制：头部姿态角度的方差倒数。

        方差越小（头越不动）→ 抑制程度越高。
        """
        if len(self._poses) < 5:
            return {'score': 0.0, 'detail': '窗口未满'}

        recent = list(self._poses)

        variances = []
        for axis in ['yaw', 'pitch', 'roll']:
            vals = [p.get(axis, 0.0) for p in recent]
            variances.append(np.var(vals))

        avg_var = sum(variances) / len(variances)

        # 方差小 = 不动 = 抑制程度高 → 分数高
        # 用指数衰减映射：var=0 → score=1.0, var→∞ → score→0
        suppression = np.exp(-avg_var * 2.0)
        return {
            'score': min(1.0, max(0.0, suppression)),
            'detail': f'方差={avg_var:.2f}',
        }

    def _calc_cognitive_load(self) -> Dict:
        """认知负荷：AU4(皱眉) × 运动抑制的组合指标。"""
        if not self._aus:
            return {'score': 0.0, 'detail': ''}

        au4 = self._aus[-1].get('AU4', 0.0)
        motor = self._calc_motor_suppression()
        motor_score = motor['score']

        # 两者都高=认知负荷高
        combined = au4 * 0.6 + motor_score * 0.4
        return {
            'score': min(1.0, combined),
            'detail': f'AU4={au4:.0%} 抑制={motor_score:.0%}',
        }

    def _calc_physio_mismatch(self, heart_rate: float) -> Dict:
        """身心不一致：情绪valence与心率的偏差。

        高快乐(vclence>0.5) + 高心率(>90BPM) = 不一致。
        高悲伤(valence<-0.3) + 低心率(<60BPM) = 可能但不是不一致。
        """
        if heart_rate < 30 or not self._emotions:
            return {'score': 0.0, 'detail': '数据不足'}

        latest_valence = self._emotions[-1].get('_valence', 0.0)

        # 正情绪 + 高心率 = 身心不一致
        hr_high = max(0.0, (heart_rate - 85.0) / 40.0)  # 85+ BPM 开始算高
        valence_pos = max(0.0, latest_valence)

        mismatch = hr_high * valence_pos
        return {
            'score': min(1.0, mismatch),
            'detail': f'心率={heart_rate:.0f}BPM 效价={latest_valence:+.2f}',
        }

    # ── 辅助 ──

    @staticmethod
    def _empty_cues() -> Dict:
        return {
            'affect_blend': {'score': 0.0, 'detail': ''},
            'masking': {'score': 0.0, 'detail': ''},
            'lability': {'score': 0.0, 'detail': ''},
            'micro_count': {'score': 0.0, 'detail': ''},
            'fake_smile': {'score': 0.0, 'detail': ''},
            'asymmetry': {'score': 0.0, 'detail': ''},
            'motor_suppression': {'score': 0.0, 'detail': ''},
            'cognitive_load': {'score': 0.0, 'detail': ''},
            'physio_mismatch': {'score': 0.0, 'detail': ''},
        }


_VALENCE_MAP: Dict[str, float] = {
    'happiness': 0.85,
    'sadness': -0.75,
    'surprise': 0.0,
    'fear': -0.65,
    'anger': -0.70,
    'disgust': -0.65,
    'contempt': -0.30,
    'neutral': 0.0,
}
