from pathlib import Path
from typing import Dict, List, Optional

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core import base_options

from .face_analyzer import FaceAnalyzer

_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / 'data'
_MODEL_PATH = str(_MODEL_DIR / 'face_landmarker.task')

# 3D 参考点坐标 (solvePnP)，单位任意。
# 坐标系: x→右, y→上, z→观察者方向。
_MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),          # 1   鼻尖
    (-60.0, 35.0, -40.0),     # 33  左眼外角
    (60.0, 35.0, -40.0),      # 263 右眼外角
    (0.0, 45.0, -15.0),       # 168 鼻根 (眉间)
    (0.0, -110.0, -45.0),     # 152 下巴底部
], dtype=np.float64)

_LANDMARK_INDICES = [1, 33, 263, 168, 152]


class MediaPipeFaceAnalyzer(FaceAnalyzer):
    """基于 MediaPipe Face Landmarker 的面部分析器。

    使用 tasks API (mediapipe >= 0.10)，输出 468 个 landmarks、
    52 个 blendshapes 和 solvePnP 估计的头部姿态。
    """

    def __init__(self, model_path: Optional[str] = None):
        mp_path = model_path or _MODEL_PATH
        options = vision.FaceLandmarkerOptions(
            base_options=base_options.BaseOptions(
                model_asset_path=mp_path),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
            output_face_blendshapes=True,
        )
        self._landmarker = vision.FaceLandmarker.create_from_options(options)
        self._fps_target = 10

    def process_frame(self, frame: np.ndarray) -> Dict:
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)

        if not result.face_landmarks:
            return {
                'aus': {},
                'landmarks': [],
                'head_pose': {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0},
                'blendshapes': {},
            }

        landmarks = [[lm.x, lm.y, lm.z] for lm in result.face_landmarks[0]]

        blendshapes = {}
        if result.face_blendshapes:
            for cat in result.face_blendshapes[0]:
                blendshapes[cat.category_name] = cat.score

        head_pose = self._estimate_head_pose(landmarks, h, w)

        return {
            'aus': {},
            'landmarks': landmarks,
            'head_pose': head_pose,
            'blendshapes': blendshapes,
        }

    def process_video(self, video_path: str) -> List[Dict]:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0
        frame_skip = max(1, int(fps / self._fps_target))
        frame_count = 0
        results = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % frame_skip == 0:
                res = self.process_frame(frame)
                res['timestamp_ms'] = frame_count / fps * 1000.0
                results.append(res)
            frame_count += 1

        cap.release()
        return results

    def close(self):
        """释放 MediaPipe 资源。"""
        self._landmarker.close()

    def _estimate_head_pose(self, landmarks: List, h: int, w: int) -> Dict:
        image_points = np.array([
            [landmarks[idx][0] * w, landmarks[idx][1] * h]
            for idx in _LANDMARK_INDICES
        ], dtype=np.float64)

        focal = float(w)
        camera_matrix = np.array([
            [focal, 0, w / 2.0],
            [0, focal, h / 2.0],
            [0, 0, 1],
        ], dtype=np.float64)

        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        success, rvec, tvec = cv2.solvePnP(
            _MODEL_POINTS_3D, image_points,
            camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_EPNP,
        )

        if not success:
            return {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0}

        rmat, _ = cv2.Rodrigues(rvec)
        sy = np.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)
        singular = sy < 1e-6

        if not singular:
            pitch = np.arctan2(-rmat[2, 0], sy)
            yaw = np.arctan2(rmat[1, 0], rmat[0, 0])
            roll = np.arctan2(rmat[2, 1], rmat[2, 2])
        else:
            pitch = np.arctan2(-rmat[2, 0], sy)
            yaw = np.arctan2(-rmat[0, 1], rmat[1, 1])
            roll = 0.0

        return {
            'yaw': float(np.degrees(yaw)),
            'pitch': float(np.degrees(pitch)),
            'roll': float(np.degrees(roll)),
        }
