"""FaceCat 命令行入口 — 面部 AU 分析。

支持摄像头实时分析和视频文件离线处理。
"""

import argparse
import time
from collections import deque
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from core.face import MediaPipeFaceAnalyzer, MediaPipeBlendshapeLookupAU
from core.face._constants import AU_DISPLAY_ORDER, AXIS_NAMES

_OVERLAY_BG_COLOR = (0, 0, 0)
_OVERLAY_ACTIVE_COLOR = (0, 255, 128)
_OVERLAY_INACTIVE_COLOR = (160, 160, 160)
_OVERLAY_WHITE = (255, 255, 255)
_OVERLAY_FPS_COLOR = (0, 255, 255)


def draw_au_overlay(
        frame: np.ndarray,
        au_dict: Dict[str, float],
        head_pose: Dict[str, float]) -> np.ndarray:
    """在画面左上角叠加 AU 数值和头部姿态。"""
    roi = frame[0:440, 0:280]
    overlay = roi.copy()
    cv2.rectangle(overlay, (0, 0), (280, 440), _OVERLAY_BG_COLOR, -1)
    frame[0:440, 0:280] = cv2.addWeighted(overlay, 0.4, roi, 0.6, 0)

    y = 25
    cv2.putText(frame, '动作单元强度', (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, _OVERLAY_WHITE, 1)
    y += 22

    for au_code, au_name in AU_DISPLAY_ORDER:
        val = au_dict.get(au_code, 0.0)
        color = _OVERLAY_ACTIVE_COLOR if val > 0.15 else _OVERLAY_INACTIVE_COLOR
        text = f'{au_code} {val:.2f}  {au_name}'
        cv2.putText(frame, text, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1)
        y += 22

    y += 5
    cv2.putText(frame, '头部姿态', (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, _OVERLAY_WHITE, 1)
    y += 20
    for axis in ('yaw', 'pitch', 'roll'):
        val = head_pose.get(axis, 0.0)
        name = AXIS_NAMES.get(axis, axis)
        cv2.putText(frame, f'  {name}: {val:+.1f}°', (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        y += 18

    return frame


def _open_camera(preferred_index: Optional[int] = None):
    """打开摄像头，指定索引则直接用，否则自动探测。"""
    if preferred_index is not None:
        cap = cv2.VideoCapture(preferred_index)
        if cap.isOpened():
            print(f'[FaceCat] 使用摄像头索引 {preferred_index}')
            return cap
        print(f'[FaceCat] 摄像头索引 {preferred_index} 无法打开')
        return None

    # 自动探测：优先内置摄像头
    for idx in (1, 0, 2):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            print(f'[FaceCat] 使用摄像头索引 {idx} (自动探测)')
            return cap
    return None


def run_camera(analyzer, au_strategy,
               camera_index: Optional[int] = None):
    """摄像头实时分析模式，按 q 退出。"""
    print('[FaceCat] 打开摄像头，按 q 退出...')
    cap = _open_camera(camera_index)
    if cap is None:
        print('[FaceCat] 无法打开任何摄像头')
        return

    fps_counter: deque[float] = deque(maxlen=30)
    while True:
        t0 = time.time()
        ret, frame = cap.read()
        if not ret:
            break

        result = analyzer.process_frame(frame)
        blendshapes = result.get('blendshapes', {})
        au_dict = au_strategy.to_au(blendshapes)
        head_pose = result.get('head_pose', {})

        display = draw_au_overlay(frame, au_dict, head_pose)

        fps_counter.append(time.time() - t0)
        avg_fps = 1.0 / (sum(fps_counter) / len(fps_counter))
        cv2.putText(display, f'帧率: {avg_fps:.1f}',
                    (10, frame.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    _OVERLAY_FPS_COLOR, 1)

        cv2.imshow('FaceCat - Face AU Analyzer', display)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print('[FaceCat] 摄像头已关闭')


def run_video(analyzer, au_strategy, video_path: str):
    """离线视频文件分析模式。"""
    print(f'[FaceCat] 处理视频: {video_path}')
    results = analyzer.process_video(video_path)
    total = len(results)
    print(f'[FaceCat] 共解析 {total} 帧 (每 100ms 采样)\n')

    au_names = {k: v for k, v in AU_DISPLAY_ORDER}
    for i, res in enumerate(results):
        ts = res.get('timestamp_ms', i * 100)
        blendshapes = res.get('blendshapes', {})
        au_dict = au_strategy.to_au(blendshapes)

        active_aus = {k: v for k, v in au_dict.items() if v > 0.1}
        if active_aus:
            parts = (
                f'{k}({au_names.get(k, k)})={v:.2f}'
                for k, v in sorted(active_aus.items())
            )
            active_str = ', '.join(parts)
        else:
            active_str = '(中性)'

        print(f'  [{ts:7.0f}ms]  {active_str}')

    print(f'\n[FaceCat] 完成，共 {total} 帧')


def main():
    parser = argparse.ArgumentParser(
        description='FaceCat — 面部动作单元分析工具')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--camera', action='store_true', default=False,
        help='实时摄像头分析 (默认)')
    group.add_argument(
        '--video', type=str, default=None,
        help='离线视频文件分析')
    parser.add_argument(
        '--camera-index', type=int, default=None,
        help='指定摄像头设备号 (0/1/2...)，不指定则自动探测')

    args = parser.parse_args()

    analyzer = MediaPipeFaceAnalyzer()
    au_strategy = MediaPipeBlendshapeLookupAU()

    if args.video:
        run_video(analyzer, au_strategy, args.video)
    else:
        run_camera(analyzer, au_strategy, args.camera_index)


if __name__ == '__main__':
    main()
