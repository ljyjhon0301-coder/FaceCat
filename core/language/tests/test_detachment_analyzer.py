from core.language import DetachmentAnalyzer


def test_empty_segments_return_zero_scores():
    result = DetachmentAnalyzer().analyze([])

    assert result['detachment_score'] == 0.0
    assert result['passive_ratio'] == 0.0


def test_passive_and_first_person_absence_raise_score():
    result = DetachmentAnalyzer().analyze([
        {'start': 0.0, 'end': 1.0, 'text': '这个事情被处理了。'},
        {'start': 1.0, 'end': 2.0, 'text': '那个人后来没有再说。'},
    ])

    assert result['detachment_score'] > 0.0
    assert result['passive_ratio'] > 0.0
    assert result['first_person_absence'] > 0.0


def test_emotion_words_reduce_flatness():
    analyzer = DetachmentAnalyzer()
    flat = analyzer.analyze([{'text': '这个事情发生了。'}])
    expressive = analyzer.analyze([{'text': '我很开心，也非常感动。'}])

    assert expressive['emotional_flatness'] < flat['emotional_flatness']
