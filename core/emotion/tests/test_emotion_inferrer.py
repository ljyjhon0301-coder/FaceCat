from core.emotion import EmotionInferrer


def test_happiness_signature_dominates():
    result = EmotionInferrer().infer({'AU12': 0.8, 'AU6': 0.5})

    assert result.dominant_emotion == 'happiness'
    assert result.confidence > 0.5
    assert result.valence > 0.0


def test_empty_au_is_neutral():
    result = EmotionInferrer().infer({})

    assert result.dominant_emotion == 'neutral'
    assert result.confidence == 0.0


def test_low_activation_marks_micro_expression():
    result = EmotionInferrer().infer({'AU1': 0.02, 'AU2': 0.03})

    assert result.is_micro is True
