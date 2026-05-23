"""疏离化语言检测 — 四维评分。

检测维度:
1. 被动语态 — "被"字句、"受到"、"遭到" 等
2. 第一人称缺失 — 用"这个/那个/它"替代"我"
3. 过度具体化 — 不必要的细节堆砌（定语链长度）
4. 情感扁平化 — 缺少情感形容词/副词
"""

import re
from typing import Dict, List

from .linguistic_analyzer import LinguisticAnalyzer


class DetachmentAnalyzer(LinguisticAnalyzer):
    """中文疏离化语言检测器。"""

    _PASSIVE_MARKERS = re.compile(
        r'被|受到?|遭到?|让|给|为.{1,3}所|由.{1,3}给'
    )
    _FIRST_PERSON = re.compile(r'我|咱|本人|自己|自个儿')
    _THIRD_PERSON_SUB = re.compile(
        r'这个|那个|它|他|她|人家|别人|某人|一个人|这人|那人'
    )
    _EMOTION_WORDS = re.compile(
        r'开心|难过|生气|害怕|高兴|悲伤|兴奋|紧张|焦虑|愤怒'
        r'|喜悦|痛苦|恐惧|惊讶|厌恶|喜爱|恨|爱|烦|累|困'
        r'|快乐|幸福|伤心|失望|沮丧|激动|感动|温暖|冷'
        r'|很不错|挺好|还行|糟糕|难受|不舒服|舒服'
        r'|很|非常|特别|极其|太|十分|相当|满|蛮'
    )

    def analyze(self, segments: List[dict]) -> Dict:
        full_text = ' '.join(s.get('text', '') for s in segments)
        sentences = self._split_sentences(full_text)

        if not sentences:
            return {
                'detachment_score': 0.0,
                'passive_ratio': 0.0,
                'first_person_absence': 0.0,
                'over_specification': 0.0,
                'emotional_flatness': 0.0,
            }

        passive = self._passive_ratio(sentences)
        first_absence = self._first_person_absence(sentences, full_text)
        over_spec = self._over_specification(sentences)
        flatness = self._emotional_flatness(sentences)

        score = (passive * 0.25 + first_absence * 0.35
                 + over_spec * 0.20 + flatness * 0.20)

        return {
            'detachment_score': min(1.0, score),
            'passive_ratio': passive,
            'first_person_absence': first_absence,
            'over_specification': over_spec,
            'emotional_flatness': flatness,
        }

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        return [s.strip() for s in re.split(r'[。！？；\n]+', text) if s.strip()]

    def _passive_ratio(self, sentences: List[str]) -> float:
        if not sentences:
            return 0.0
        count = sum(1 for s in sentences if self._PASSIVE_MARKERS.search(s))
        return min(1.0, count / len(sentences))

    def _first_person_absence(
            self, sentences: List[str], full_text: str) -> float:
        has_i = self._FIRST_PERSON.search(full_text) is not None
        total = len(sentences)
        if total == 0:
            return 0.0
        third_count = sum(
            1 for s in sentences if self._THIRD_PERSON_SUB.search(s))
        third_ratio = third_count / total
        if has_i:
            return third_ratio * 0.3
        return min(1.0, third_ratio + 0.4)

    def _over_specification(self, sentences: List[str]) -> float:
        if not sentences:
            return 0.0
        scores = []
        for s in sentences:
            de_chain = len(re.findall(r'的[^的]{2,}', s))
            adj_chain = len(re.findall(
                r'[很非常特别极其十分][^\s，。！？]{1,4}', s))
            detail = len(re.findall(r'[0-9]+[个只条张次年天岁]', s))
            scores.append(min(1.0, (de_chain * 2 + adj_chain + detail * 2) / 10.0))
        return sum(scores) / len(scores)

    def _emotional_flatness(self, sentences: List[str]) -> float:
        if not sentences:
            return 0.0
        emotional = sum(
            1 for s in sentences if self._EMOTION_WORDS.search(s))
        ratio = emotional / len(sentences)
        return max(0.0, 1.0 - ratio * 3.0)
