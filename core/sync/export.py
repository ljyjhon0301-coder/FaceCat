"""导出功能 — JSON / CSV。"""

import csv
import json
from pathlib import Path
from typing import Dict, List


def export_to_json(snapshots: List[Dict], annotations: List[Dict],
                   path: str):
    """导出完整分析结果 + 标注为 JSON，每帧一个对象。"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({
            'snapshots': snapshots,
            'annotations': annotations,
        }, f, ensure_ascii=False, indent=2)


def export_to_csv(snapshots: List[Dict], path: str):
    """导出多轨数据为 CSV，每列一个指标，每行一帧。"""
    if not snapshots:
        return

    all_au_keys = set()
    for s in snapshots:
        all_au_keys.update(s.get('face', {}).get('aus', {}).keys())
    au_keys = sorted(all_au_keys)

    fieldnames = [
        'timestamp_ms',
        *[f'au_{k}' for k in au_keys],
        'head_yaw', 'head_pitch', 'head_roll',
        'heart_rate', 'breath_rate',
        'dominant_emotion', 'confidence',
        'valence', 'arousal',
        'f0', 'rms', 'speech_rate', 'jitter', 'shimmer',
        'detachment_score',
        'text',
    ]

    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for s in snapshots:
            face = s.get('face', {})
            physio = s.get('physiological', {})
            voice = s.get('voice', {})
            lang = s.get('language', {})
            row = {'timestamp_ms': s.get('timestamp_ms', 0)}
            for k in au_keys:
                row[f'au_{k}'] = face.get('aus', {}).get(k, 0.0)
            hp = face.get('head_pose', {})
            row['head_yaw'] = hp.get('yaw', 0.0)
            row['head_pitch'] = hp.get('pitch', 0.0)
            row['head_roll'] = hp.get('roll', 0.0)
            row['heart_rate'] = physio.get('heart_rate', 0.0)
            row['breath_rate'] = physio.get('breath_rate', 0.0)
            emo = s.get('emotion', {})
            row['dominant_emotion'] = emo.get('dominant_emotion', '')
            row['confidence'] = emo.get('confidence', 0.0)
            row['valence'] = emo.get('valence', 0.0)
            row['arousal'] = emo.get('arousal', 0.0)
            row['f0'] = voice.get('f0', 0.0)
            row['rms'] = voice.get('rms', 0.0)
            row['speech_rate'] = voice.get('speech_rate', 0.0)
            row['jitter'] = voice.get('jitter', 0.0)
            row['shimmer'] = voice.get('shimmer', 0.0)
            row['detachment_score'] = lang.get('detachment_score', 0.0)
            row['text'] = lang.get('text', '')
            writer.writerow(row)


# 向后兼容别名
save_json = export_to_json
save_csv = export_to_csv
