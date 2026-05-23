from core.cue import DeceptionCueAnalyzer
from core.emotion import EmotionResult


def _emotion(
        dominant='happiness',
        happiness=0.8,
        sadness=0.0,
        valence=0.85):
    return EmotionResult(
        emotions={
            'happiness': happiness,
            'sadness': sadness,
            'fear': 0.0,
            'anger': 0.0,
            'disgust': 0.0,
            'contempt': 0.0,
        },
        dominant_emotion=dominant,
        confidence=happiness,
        valence=valence,
        arousal=0.5,
    )


def test_fake_smile_and_motor_suppression_scores():
    analyzer = DeceptionCueAnalyzer(window_size=10)
    for _ in range(5):
        analyzer.feed(
            _emotion(),
            {'AU12': 0.8, 'AU6': 0.1, 'AU4': 0.2},
            {'yaw': 1.0, 'pitch': 1.0, 'roll': 1.0},
        )

    cues = analyzer.get_cues(heart_rate=0.0)

    assert cues['fake_smile']['score'] > 0.0
    assert cues['motor_suppression']['score'] > 0.0


def test_asymmetry_uses_raw_blendshape_sides():
    analyzer = DeceptionCueAnalyzer(window_size=5)
    analyzer.feed_blendshapes({
        'mouthSmileLeft': 0.9,
        'mouthSmileRight': 0.1,
    })
    for _ in range(3):
        analyzer.feed(
            _emotion(),
            {'AU12': 0.5, 'AU6': 0.2},
            {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0},
        )

    cues = analyzer.get_cues()

    assert cues['asymmetry']['score'] > 0.0
