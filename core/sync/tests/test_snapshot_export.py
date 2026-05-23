import csv
import json

from core.sync import SnapshotBuilder, export_to_csv, export_to_json


def test_snapshot_builder_applies_voice_and_language():
    builder = SnapshotBuilder()
    builder.add_frame(100.0, {'AU12': 0.5}, {'yaw': 1.0})
    builder.apply_voice({
        'times': [0.1],
        'f0': [220.0],
        'rms': [0.25],
        'jitter': 0.01,
        'shimmer': 0.02,
        'speech_rate': 3.0,
    })
    builder.apply_language(
        [{'start': 0.0, 'end': 0.2, 'text': '你好'}],
        {'detachment_score': 0.4},
    )

    snapshot = builder.to_list()[0]

    assert snapshot['face']['aus']['AU12'] == 0.5
    assert snapshot['voice']['f0'] == 220.0
    assert snapshot['language']['text'] == '你好'


def test_export_json_and_csv(tmp_path):
    snapshots = [{
        'timestamp_ms': 0.0,
        'face': {
            'aus': {'AU12': 0.5},
            'head_pose': {'yaw': 1.0, 'pitch': 2.0, 'roll': 3.0},
        },
        'emotion': {
            'dominant_emotion': 'happiness',
            'confidence': 0.8,
            'valence': 0.85,
            'arousal': 0.5,
        },
        'physiological': {'heart_rate': 72.0, 'breath_rate': 12.0},
        'voice': {'f0': 220.0, 'rms': 0.25, 'speech_rate': 3.0},
        'language': {'detachment_score': 0.1, 'text': 'ok'},
    }]
    json_path = tmp_path / 'out.json'
    csv_path = tmp_path / 'out.csv'

    export_to_json(snapshots, [{'label': 'smile'}], str(json_path))
    export_to_csv(snapshots, str(csv_path))

    assert json.loads(json_path.read_text(encoding='utf-8'))['annotations']
    with csv_path.open(encoding='utf-8') as handle:
        row = next(csv.DictReader(handle))
    assert row['au_AU12'] == '0.5'
    assert row['dominant_emotion'] == 'happiness'
