"""实时微表情 → 情绪/心理状态推理引擎。

基于 Ekman 基本情绪框架，将 AU 激活值 + 生理信号
映射为七类基本情绪和连续维度（valence/arousal）。
参考来源：
  - Ekman & Friesen (1978) Facial Action Coding System
  - Ekman (1999) Basic Emotions, in Handbook of Cognition and Emotion
  - Matsumoto & Ekman (2008) Facial Expression Recognition
  - Russell (1980) Circumplex Model of Affect
"""

from typing import Dict, Tuple


# ── 七类基本情绪的 AU 签名（权重 + 阈值） ──

_EKMAN_SIGNATURES: Dict[str, Dict] = {
    'happiness': {
        'label': '快乐',
        'contributors': {
            'AU12': 1.0,  # 嘴角上扬（核心信号）
            'AU6': 0.6,   # 脸颊提升（Duchenne 标志）
        },
        'inhibitors': {
            'AU4': 0.8,   # 皱眉 → 抑制快乐
            'AU15': 0.6,  # 嘴角下压
        },
        'threshold': 0.15,
    },
    'sadness': {
        'label': '悲伤',
        'contributors': {
            'AU1': 0.8,   # 内眉上扬
            'AU4': 0.7,   # 皱眉
            'AU15': 0.8,  # 嘴角下压
            'AU17': 0.4,  # 下巴提升
        },
        'inhibitors': {
            'AU12': 0.7,  # 微笑抑制悲伤
            'AU27': 0.5,  # 张嘴
        },
        'threshold': 0.15,
    },
    'surprise': {
        'label': '惊讶',
        'contributors': {
            'AU1': 0.7,   # 内眉上扬
            'AU2': 0.7,   # 外眉上扬
            'AU5': 0.6,   # 上睑提升
            'AU26': 0.5,  # 下颌张开
        },
        'inhibitors': {
            'AU4': 0.6,   # 皱眉 → 不是惊讶
            'AU9': 0.5,   # 皱鼻
        },
        'threshold': 0.15,
    },
    'fear': {
        'label': '恐惧',
        'contributors': {
            'AU1': 0.6,   # 内眉上扬
            'AU2': 0.6,   # 外眉上扬
            'AU4': 0.5,   # 皱眉（与抬眉共存=恐惧特有）
            'AU5': 0.7,   # 上睑提升（瞪眼）
            'AU20': 0.5,  # 嘴唇拉伸
            'AU26': 0.3,  # 下颌微张
        },
        'inhibitors': {
            'AU12': 0.7,  # 微笑抑制恐惧
            'AU9': 0.4,   # 皱鼻
        },
        'threshold': 0.15,
    },
    'anger': {
        'label': '愤怒',
        'contributors': {
            'AU4': 1.0,   # 皱眉（核心）
            'AU5': 0.6,   # 上睑提升（瞪）
            'AU7': 0.7,   # 眼睑收紧
            'AU23': 0.6,  # 嘴唇收紧
        },
        'inhibitors': {
            'AU12': 0.6,  # 微笑抑制愤怒
            'AU6': 0.3,   # 脸颊提升
        },
        'threshold': 0.15,
    },
    'disgust': {
        'label': '厌恶',
        'contributors': {
            'AU9': 1.0,   # 皱鼻（核心信号）
            'AU10': 0.7,  # 上唇提升
            'AU4': 0.3,   # 轻度皱眉辅助
        },
        'inhibitors': {
            'AU12': 0.5,
            'AU1': 0.3,
        },
        'threshold': 0.15,
    },
    'contempt': {
        'label': '轻蔑',
        'contributors': {
            'AU14': 0.8,  # 嘴角收紧（单侧=轻蔑）
            'AU12': 0.3,  # 轻蔑常伴不对称微笑
            'AU23': 0.2,  # 嘴唇收紧
        },
        'inhibitors': {
            'AU6': 0.4,   # 脸颊提升抑制轻蔑
        },
        'threshold': 0.12,
    },
}

_EMOTION_ORDER = [
    'happiness', 'sadness', 'surprise', 'fear',
    'anger', 'disgust', 'contempt',
]

# ── Valence/Arousal 映射 ──

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

_AROUSAL_MAP: Dict[str, float] = {
    'happiness': 0.50,
    'sadness': 0.20,
    'surprise': 0.85,
    'fear': 0.80,
    'anger': 0.75,
    'disgust': 0.40,
    'contempt': 0.30,
    'neutral': 0.0,
}

_EMOTION_LABELS: Dict[str, str] = {
    s['label']: ek  # reverse: '快乐' → 'happiness'
    for ek, s in _EKMAN_SIGNATURES.items()
}


class EmotionResult:
    """单帧情绪推理结果。"""

    __slots__ = (
        'emotions', 'dominant_emotion', 'confidence',
        'valence', 'arousal', 'is_micro',
    )

    def __init__(
        self,
        emotions: Dict[str, float],
        dominant_emotion: str,
        confidence: float,
        valence: float,
        arousal: float,
        is_micro: bool = False,
    ):
        self.emotions = emotions
        self.dominant_emotion = dominant_emotion
        self.confidence = confidence
        self.valence = valence
        self.arousal = arousal
        self.is_micro = is_micro

    @property
    def dominant_label(self) -> str:
        """情绪中文名。"""
        sig = _EKMAN_SIGNATURES.get(self.dominant_emotion)
        return sig['label'] if sig else '中性'

    @property
    def secondary_emotion(self) -> Tuple[str, float]:
        """第二高情绪 (英文名, 分数)。"""
        sorted_ = sorted(
            [(k, v) for k, v in self.emotions.items()
             if k != self.dominant_emotion],
            key=lambda x: -x[1],
        )
        if sorted_:
            return sorted_[0]
        return ('neutral', 0.0)

    def to_dict(self) -> Dict:
        """序列化为 JSON 可序列化字典。"""
        return {
            'emotions': dict(self.emotions),
            'dominant_emotion': self.dominant_emotion,
            'dominant_label': self.dominant_label,
            'confidence': self.confidence,
            'valence': self.valence,
            'arousal': self.arousal,
            'is_micro': self.is_micro,
        }


class EmotionInferrer:
    """AU → 情绪推理器。无状态，每帧独立推理。"""

    def infer(self, au_dict: Dict[str, float],
              heart_rate: float = 0.0,
              breath_rate: float = 0.0) -> EmotionResult:
        """根据 AU 激活值和可选生理信号输出情绪推理。

        Args:
            au_dict: AU -> 激活值 [0, 1] 字典。
            heart_rate: 心率 BPM（0 表示未知）。
            breath_rate: 呼吸率（0 表示未知）。

        Returns:
            EmotionResult 包含所有推理结果。
        """
        raw = self._compute_raw_scores(au_dict)
        emotions = self._apply_inhibitors(raw, au_dict)
        dominant, confidence = self._find_dominant(emotions)
        emo_valence = _VALENCE_MAP.get(dominant, 0.0)
        emo_arousal = _AROUSAL_MAP.get(dominant, 0.0)

        # 用生理信号微调 arousal
        if heart_rate > 0:
            hr_factor = min(1.0, (heart_rate - 50.0) / 100.0)
            emo_arousal = max(0.0, min(1.0,
                emo_arousal * 0.7 + hr_factor * 0.3))

        is_micro = self._detect_micro(au_dict)

        return EmotionResult(
            emotions=emotions,
            dominant_emotion=dominant,
            confidence=confidence,
            valence=emo_valence,
            arousal=emo_arousal,
            is_micro=is_micro,
        )

    def _compute_raw_scores(
            self, au_dict: Dict[str, float]) -> Dict[str, float]:
        """计算每种情绪的原始 AU 贡献分。"""
        scores: Dict[str, float] = {}
        for ek, sig in _EKMAN_SIGNATURES.items():
            score = 0.0
            for au_code, weight in sig['contributors'].items():
                val = au_dict.get(au_code, 0.0)
                if val > 0.01:
                    score += weight * val
            # 归一化到 [0, 1]
            max_possible = sum(sig['contributors'].values())
            scores[ek] = score / max_possible if max_possible > 0 else 0.0
        return scores

    def _apply_inhibitors(
            self, scores: Dict[str, float],
            au_dict: Dict[str, float]) -> Dict[str, float]:
        """应用抑制项（某些 AU 存在时会降低特定情绪分）。"""
        result = dict(scores)
        for ek, sig in _EKMAN_SIGNATURES.items():
            for au_code, penalty in sig['inhibitors'].items():
                val = au_dict.get(au_code, 0.0)
                if val > 0.15:
                    result[ek] *= (1.0 - penalty * val)
        return result

    def _find_dominant(
            self, emotions: Dict[str, float]
    ) -> Tuple[str, float]:
        """找出优势情绪，小于阈值则返回 'neutral'。"""
        best_ek = max(emotions, key=lambda k: emotions[k])
        best_score = emotions[best_ek]
        threshold = _EKMAN_SIGNATURES[best_ek]['threshold']
        if best_score < threshold:
            return ('neutral', 0.0)
        return (best_ek, best_score)

    @staticmethod
    def _detect_micro(au_dict: Dict[str, float]) -> bool:
        """简易微表情检测：AU 激活但绝对值极低。"""
        active = [v for v in au_dict.values() if v > 0.01]
        if not active:
            return False
        avg_activation = sum(active) / len(active)
        return avg_activation < 0.05
