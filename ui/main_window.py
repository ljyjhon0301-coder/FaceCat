"""FaceCat 桌面界面 — PySide6 主窗口。"""

from collections import deque
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from core.cue import DeceptionCueAnalyzer
from core.emotion import EmotionInferrer
from core.face import MediaPipeFaceAnalyzer, MediaPipeBlendshapeLookupAU
from core.face._constants import AU_NAMES, AXIS_NAMES
from core.physiological import (
    CHROMRPPG, POSRPPG, BreathAnalyzer, extract_forehead_roi,
)
from ui.timeline_widget import TimelineWidget

_DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
_VIDEO_SIZE = (640, 480)
_WINDOW_SIZE = (1120, 760)
_MIN_WINDOW_SIZE = (900, 580)

_STYLE = """
QMainWindow { background: #1e1e1e; }
QGroupBox {
    color: #ccc; font-weight: bold; border: 1px solid #333;
    border-radius: 6px; margin-top: 14px; padding-top: 12px;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 12px; padding: 0 8px;
}
QPushButton {
    background: #3a3a3a; color: #ddd; border: 1px solid #4a4a4a;
    border-radius: 4px; padding: 6px 18px; font-size: 12px;
}
QPushButton:hover { background: #4a4a4a; border-color: #5a5a5a; }
QPushButton:pressed { background: #2a2a2a; }
QPushButton:disabled { background: #2a2a2a; color: #555; border-color: #333; }
QComboBox {
    background: #3a3a3a; color: #ddd; border: 1px solid #4a4a4a;
    border-radius: 4px; padding: 4px 10px; font-size: 12px;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background: #2a2a2a; color: #ddd; selection-background-color: #4a4a4a;
    border: 1px solid #4a4a4a;
}
QScrollArea { border: none; background: transparent; }
QProgressBar {
    background: #2a2a2a; border: none; border-radius: 3px;
    text-align: left; color: #aaa; font-size: 11px; min-height: 16px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00c853, stop:1 #69f0ae);
    border-radius: 3px;
}
"""


def _cv_frame_to_qpixmap(frame: np.ndarray) -> QPixmap:
    """OpenCV BGR → QPixmap (RGB)。"""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
    return QPixmap.fromImage(qimg)


class _CameraWorker(QThread):
    """后台线程：采集摄像头帧 + MediaPipe 分析。"""

    frame_ready = Signal(np.ndarray, dict, dict, dict)
    fps_updated = Signal(float)
    physio_updated = Signal(float, float)
    error_occurred = Signal(str)

    def __init__(self, camera_index: int, model_path: str,
                 rppg_algo: str = 'chrom'):
        super().__init__()
        self._camera_index = camera_index
        self._model_path = model_path
        self._rppg_algo = rppg_algo
        self.draw_landmarks = False

    def run(self):
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            self.error_occurred.emit(
                f'无法打开摄像头索引 {self._camera_index}')
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        analyzer = MediaPipeFaceAnalyzer(model_path=self._model_path)
        au_mapper = MediaPipeBlendshapeLookupAU()
        rppg_cls = POSRPPG if self._rppg_algo == 'pos' else CHROMRPPG
        rppg = rppg_cls(fps=30.0)
        breath = BreathAnalyzer(fps=30.0)
        fps_history = deque(maxlen=30)
        frame_count = 0

        while not self.isInterruptionRequested():
            t0 = cv2.getTickCount()
            ret, frame = cap.read()
            if not ret:
                break

            result = analyzer.process_frame(frame)
            blendshapes = result.get('blendshapes', {})
            au_dict = au_mapper.to_au(blendshapes)
            head_pose = result.get('head_pose', {})
            landmarks = result.get('landmarks', [])

            if landmarks:
                rgb = extract_forehead_roi(landmarks, frame)
                rppg.feed_rgb(rgb)
                breath.feed_rgb(rgb)

            frame_count += 1
            if frame_count % 90 == 0:
                hr = rppg.get_heart_rate()
                br = breath.get_heart_rate()
                self.physio_updated.emit(hr, br)

            if self.draw_landmarks:
                if landmarks:
                    h, w = frame.shape[:2]
                    for lm in landmarks:
                        px, py = int(lm[0] * w), int(lm[1] * h)
                        cv2.circle(frame, (px, py), 1, (0, 255, 128), -1)

            self.frame_ready.emit(frame.copy(), au_dict, head_pose, blendshapes)

            t1 = cv2.getTickCount()
            fps_history.append((t1 - t0) / cv2.getTickFrequency())
            self.fps_updated.emit(1.0 / (sum(fps_history) / len(fps_history)))

        cap.release()
        analyzer.close()

    def stop(self):
        self.requestInterruption()


class MainWindow(QMainWindow):
    """FaceCat 主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('FaceCat — 面部动作单元分析')
        self.resize(*_WINDOW_SIZE)
        self.setMinimumSize(*_MIN_WINDOW_SIZE)

        qr = self.frameGeometry()
        qr.moveCenter(self.screen().availableGeometry().center())
        self.move(qr.topLeft())

        self._worker: _CameraWorker | None = None
        self._model_path = str(_DATA_DIR / 'face_landmarker.task')
        self._au_mapper = MediaPipeBlendshapeLookupAU()
        self._mirrored = True
        self._frame_count = 0
        self._video_timer: QTimer | None = None
        self._annotations: list = []
        self._snapshots: list = []
        self._marking = False
        self._mark_start = 0.0
        self._video_results: list = []
        self._video_idx = 0

        self._emotion_inferrer = EmotionInferrer()
        self._cue_analyzer = DeceptionCueAnalyzer(window_size=30)
        self._latest_hr = 0.0
        self._latest_br = 0.0

        self._setup_ui()

    def closeEvent(self, event):
        if self._video_timer and self._video_timer.isActive():
            self._video_timer.stop()
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(5000)
            self._worker = None
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_M:
            self._toggle_mark()
        elif event.key() == Qt.Key_E and event.modifiers() & Qt.ControlModifier:
            self._export_data()
        else:
            super().keyPressEvent(event)

    # ── UI 搭建 ──

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 6)
        root.setSpacing(8)

        body = QHBoxLayout()
        body.setSpacing(10)

        body.addLayout(self._build_video_area(), 3)
        body.addWidget(self._build_au_panel(), 2)

        root.addLayout(body, 1)

        self._timeline = TimelineWidget()
        self._timeline.setMinimumHeight(180)
        self._timeline.playhead_moved.connect(self._on_timeline_seek)
        self._timeline.setVisible(False)
        root.addWidget(self._timeline)

        root.addLayout(self._build_controls())

        self.setStyleSheet(_STYLE)

    def _build_video_area(self):
        layout = QVBoxLayout()
        layout.setSpacing(4)

        self._video_label = QLabel()
        self._video_label.setMinimumSize(*_VIDEO_SIZE)
        self._video_label.setAlignment(Qt.AlignCenter)
        self._video_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._video_label.setStyleSheet(
            'background: #111; border: 1px solid #333; border-radius: 6px;')
        self._video_label.setText('摄像头未开启')
        layout.addWidget(self._video_label, 1)

        self._fps_label = QLabel('帧率: --')
        self._fps_label.setAlignment(Qt.AlignRight)
        self._fps_label.setStyleSheet('color: #666; font-size: 11px;')
        layout.addWidget(self._fps_label)

        return layout

    def _build_au_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet('background: transparent;')
        scroll.viewport().setAutoFillBackground(False)

        au_widget = QWidget()
        au_widget.setAutoFillBackground(False)
        au_widget.setStyleSheet('background: transparent;')
        au_layout = QVBoxLayout(au_widget)
        au_layout.setContentsMargins(0, 0, 0, 0)
        au_layout.setSpacing(2)

        self._au_bars = {}
        for au_code, au_name in AU_NAMES.items():
            row = QHBoxLayout()
            row.setSpacing(6)

            code_lbl = QLabel(au_code)
            code_lbl.setFixedWidth(36)
            code_lbl.setStyleSheet(
                'color: #999; font-size: 11px; font-weight: bold;')

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(True)
            bar.setFormat(au_name)
            bar.setFixedHeight(18)

            row.addWidget(code_lbl)
            row.addWidget(bar, 1)
            au_layout.addLayout(row)
            self._au_bars[au_code] = bar

        au_layout.addStretch()
        scroll.setWidget(au_widget)

        au_group = QGroupBox('动作单元强度')
        au_outer = QVBoxLayout(au_group)
        au_outer.addWidget(scroll)
        layout.addWidget(au_group, 1)

        # 头部姿态
        pose_group = QGroupBox('头部姿态')
        pose_layout = QHBoxLayout(pose_group)
        pose_layout.setSpacing(8)

        self._pose_labels = {}
        for axis, name in AXIS_NAMES.items():
            lbl = QLabel(f'{name}\n---')
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                'color: #ddd; font-size: 13px; padding: 4px 0;')
            lbl.setMinimumWidth(80)
            pose_layout.addWidget(lbl, 1)
            self._pose_labels[axis] = lbl

        layout.addWidget(pose_group)

        physio_group = QGroupBox('生理信号')
        physio_layout = QHBoxLayout(physio_group)
        physio_layout.setSpacing(12)

        self._hr_label = QLabel('心率\n--- BPM')
        self._hr_label.setAlignment(Qt.AlignCenter)
        self._hr_label.setStyleSheet('color: #ef5350; font-size: 14px;')
        physio_layout.addWidget(self._hr_label, 1)

        self._br_label = QLabel('呼吸\n--- /min')
        self._br_label.setAlignment(Qt.AlignCenter)
        self._br_label.setStyleSheet('color: #42a5f5; font-size: 14px;')
        physio_layout.addWidget(self._br_label, 1)

        layout.addWidget(physio_group)

        emotion_group = QGroupBox('情绪推断')
        emotion_layout = QVBoxLayout(emotion_group)
        emotion_layout.setSpacing(4)

        self._emotion_icon = QLabel('◉')
        self._emotion_icon.setAlignment(Qt.AlignCenter)
        self._emotion_icon.setStyleSheet(
            'color: #888; font-size: 28px; padding: 2px 0;')
        emotion_layout.addWidget(self._emotion_icon)

        self._emotion_label = QLabel('中性')
        self._emotion_label.setAlignment(Qt.AlignCenter)
        self._emotion_label.setStyleSheet(
            'color: #ccc; font-size: 18px; font-weight: bold;'
            'padding: 2px 0;')
        emotion_layout.addWidget(self._emotion_label)

        self._emotion_bar = QProgressBar()
        self._emotion_bar.setRange(0, 100)
        self._emotion_bar.setValue(0)
        self._emotion_bar.setTextVisible(False)
        self._emotion_bar.setFixedHeight(6)
        self._emotion_bar.setStyleSheet(
            'QProgressBar { background: #2a2a2a; border: none; '
            'border-radius: 3px; }'
            'QProgressBar::chunk { background: #888; '
            'border-radius: 3px; }')
        emotion_layout.addWidget(self._emotion_bar)

        valence_row = QHBoxLayout()
        valence_row.setSpacing(6)
        valence_lbl = QLabel('效价')
        valence_lbl.setFixedWidth(30)
        valence_lbl.setStyleSheet('color: #999; font-size: 10px;')
        valence_row.addWidget(valence_lbl)
        self._valence_bar = QProgressBar()
        self._valence_bar.setRange(-100, 100)
        self._valence_bar.setValue(0)
        self._valence_bar.setTextVisible(False)
        self._valence_bar.setFixedHeight(4)
        self._valence_bar.setStyleSheet(
            'QProgressBar { background: #2a2a2a; border: none; '
            'border-radius: 2px; }'
            'QProgressBar::chunk { background: qlineargradient('
            'x1:0, y1:0, x2:1, y2:0, '
            'stop:0 #ef5350, stop:0.5 #888, stop:1 #4caf50); '
            'border-radius: 2px; }')
        valence_row.addWidget(self._valence_bar, 1)
        emotion_layout.addLayout(valence_row)

        arousal_row = QHBoxLayout()
        arousal_row.setSpacing(6)
        arousal_lbl = QLabel('激活')
        arousal_lbl.setFixedWidth(30)
        arousal_lbl.setStyleSheet('color: #999; font-size: 10px;')
        arousal_row.addWidget(arousal_lbl)
        self._arousal_bar = QProgressBar()
        self._arousal_bar.setRange(0, 100)
        self._arousal_bar.setValue(0)
        self._arousal_bar.setTextVisible(False)
        self._arousal_bar.setFixedHeight(4)
        self._arousal_bar.setStyleSheet(
            'QProgressBar { background: #2a2a2a; border: none; '
            'border-radius: 2px; }'
            'QProgressBar::chunk { background: qlineargradient('
            'x1:0, y1:0, x2:1, y2:0, '
            'stop:0 #42a5f5, stop:1 #ef5350); '
            'border-radius: 2px; }')
        arousal_row.addWidget(self._arousal_bar, 1)
        emotion_layout.addLayout(arousal_row)

        self._emotion_secondary = QLabel('')
        self._emotion_secondary.setAlignment(Qt.AlignCenter)
        self._emotion_secondary.setStyleSheet(
            'color: #666; font-size: 11px; padding: 2px 0;')
        emotion_layout.addWidget(self._emotion_secondary)

        layout.addWidget(emotion_group)

        # ── 不一致性线索面板 ──
        cue_group = QGroupBox('不一致性线索')
        cue_layout = QVBoxLayout(cue_group)
        cue_layout.setSpacing(2)

        self._cue_bars = {}
        self._cue_bars_sec = {}
        for cue_key in self._CORE_CUES:
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(True)
            bar.setFormat(self._CUE_LABELS[cue_key])
            bar.setFixedHeight(14)
            bar.setStyleSheet(
                'QProgressBar { background: #2a2a2a; border: none; '
                'border-radius: 3px; text-align: left; '
                'color: #aaa; font-size: 10px; min-height: 14px; }'
                'QProgressBar::chunk { background: #888; '
                'border-radius: 3px; }')
            cue_layout.addWidget(bar)
            self._cue_bars[cue_key] = bar

        sec_row = QHBoxLayout()
        sec_row.setSpacing(4)
        for cue_key in self._SEC_CUES:
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedSize(40, 6)
            bar.setToolTip(self._CUE_LABELS[cue_key])
            color = self._CUE_COLORS.get(cue_key, '#888')
            bar.setStyleSheet(
                'QProgressBar { background: #2a2a2a; border: none; '
                'border-radius: 2px; }'
                f'QProgressBar::chunk {{ background: {color}; '
                'border-radius: 2px; }')
            sec_row.addWidget(bar)
            self._cue_bars_sec[cue_key] = bar
        sec_row.addStretch()
        cue_layout.addLayout(sec_row)

        disc_label = QLabel('线索为统计指标，非测谎结论')
        disc_label.setAlignment(Qt.AlignCenter)
        disc_label.setStyleSheet('color: #555; font-size: 9px; padding: 2px 0;')
        cue_layout.addWidget(disc_label)

        layout.addWidget(cue_group)

        return panel

    def _build_controls(self):
        bar = QHBoxLayout()
        bar.setSpacing(12)

        self._btn_start = QPushButton('▶  开始')
        self._btn_start.setFixedWidth(80)
        self._btn_start.clicked.connect(self._start_camera)

        self._btn_stop = QPushButton('■  停止')
        self._btn_stop.setFixedWidth(80)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop_camera)

        bar.addWidget(self._btn_start)
        bar.addWidget(self._btn_stop)

        sep1 = QLabel()
        sep1.setFixedWidth(1)
        sep1.setStyleSheet('background: #333;')
        bar.addWidget(sep1)

        cam_label = QLabel('摄像头')
        cam_label.setStyleSheet('color: #999; font-size: 12px;')
        bar.addWidget(cam_label)

        self._combo_camera = QComboBox()
        for idx in range(4):
            self._combo_camera.addItem(f'设备 {idx}', idx)
        self._combo_camera.setCurrentIndex(1)
        self._combo_camera.setFixedWidth(80)
        bar.addWidget(self._combo_camera)

        sep2 = QLabel()
        sep2.setFixedWidth(1)
        sep2.setStyleSheet('background: #333;')
        bar.addWidget(sep2)

        self._btn_video = QPushButton('📂  打开视频')
        self._btn_video.clicked.connect(self._open_video)
        bar.addWidget(self._btn_video)

        sep3 = QLabel()
        sep3.setFixedWidth(1)
        sep3.setStyleSheet('background: #333;')
        bar.addWidget(sep3)

        self._btn_landmarks = QPushButton('😶  面部网格')
        self._btn_landmarks.setCheckable(True)
        self._btn_landmarks.setChecked(False)
        self._btn_landmarks.toggled.connect(self._toggle_landmarks)
        self._btn_landmarks.setEnabled(False)
        bar.addWidget(self._btn_landmarks)

        self._btn_mirror = QPushButton('🪞  镜像')
        self._btn_mirror.setCheckable(True)
        self._btn_mirror.setChecked(True)
        self._btn_mirror.setEnabled(False)
        self._btn_mirror.toggled.connect(self._toggle_mirror)
        bar.addWidget(self._btn_mirror)

        sep4 = QLabel()
        sep4.setFixedWidth(1)
        sep4.setStyleSheet('background: #333;')
        bar.addWidget(sep4)

        rppg_label = QLabel('rPPG')
        rppg_label.setStyleSheet('color: #999; font-size: 12px;')
        bar.addWidget(rppg_label)

        self._combo_rppg = QComboBox()
        self._combo_rppg.addItem('CHROM', 'chrom')
        self._combo_rppg.addItem('POS', 'pos')
        self._combo_rppg.setCurrentIndex(0)
        self._combo_rppg.setFixedWidth(90)
        bar.addWidget(self._combo_rppg)

        sep5 = QLabel()
        sep5.setFixedWidth(1)
        sep5.setStyleSheet('background: #333;')
        bar.addWidget(sep5)

        self._btn_export = QPushButton('💾  导出')
        self._btn_export.setToolTip('标注: 按 M 键标记起止, Ctrl+E 导出')
        self._btn_export.clicked.connect(self._export_data)
        bar.addWidget(self._btn_export)

        bar.addStretch()

        self._status_icon = QLabel()
        self._status_icon.setFixedSize(8, 8)
        self._status_icon.setStyleSheet(
            'background: #888; border-radius: 4px;')
        bar.addWidget(self._status_icon)

        self._status_label = QLabel('就绪')
        self._status_label.setStyleSheet('color: #888; font-size: 12px;')
        bar.addWidget(self._status_label)

        return bar

    def _set_status(self, text, color='#888', dot_color='#888'):
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f'color: {color}; font-size: 12px;')
        self._status_icon.setStyleSheet(
            f'background: {dot_color}; border-radius: 4px;')

    # ── 摄像头 ──

    def _start_camera(self):
        if self._video_timer:
            self._video_timer.stop()
        self._timeline.setVisible(False)
        self._btn_video.setText('📂  打开视频')

        idx = self._combo_camera.currentData()
        algo = self._combo_rppg.currentData()
        self._worker = _CameraWorker(idx, self._model_path, algo)
        self._worker.frame_ready.connect(self._on_frame)
        self._worker.fps_updated.connect(self._on_fps)
        self._worker.physio_updated.connect(self._on_physio)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_video.setEnabled(False)
        self._btn_landmarks.setEnabled(True)
        self._btn_landmarks.setChecked(False)
        self._btn_mirror.setEnabled(True)
        self._set_status(f'设备 {idx} 运行中', '#4caf50', '#4caf50')

    def _toggle_landmarks(self, checked):
        if self._worker:
            self._worker.draw_landmarks = checked

    def _toggle_mirror(self, checked):
        self._mirrored = checked

    def _toggle_mark(self):
        ts = self._video_results[self._video_idx].get('timestamp_ms', 0) if self._video_results else 0
        if not self._marking:
            self._marking = True
            self._mark_start = ts
            self._set_status(f'标注起点: {ts:.0f}ms — 按 M 标记终点',
                             '#ffeb3b', '#ffeb3b')
        else:
            self._marking = False
            from PySide6.QtWidgets import QInputDialog
            label, ok = QInputDialog.getText(
                self, '标注标签', f'{self._mark_start:.0f}-{ts:.0f}ms:')
            if ok and label:
                self._annotations.append({
                    'start_ms': self._mark_start,
                    'end_ms': ts,
                    'label': label,
                })
                self._set_status(f'已标注: {label}', '#4caf50', '#4caf50')

    def _export_data(self):
        if not self._snapshots:
            self._set_status('无数据可导出', '#f44336', '#f44336')
            return
        path, _ = QFileDialog.getSaveFileName(
            self, '导出', 'facecat_export.json',
            'JSON (*.json);;CSV (*.csv)')
        if not path:
            return
        from core.sync import save_json, save_csv
        if path.endswith('.csv'):
            save_csv(self._snapshots, path)
        else:
            save_json(self._snapshots, self._annotations, path)
        self._set_status(f'已导出: {Path(path).name}', '#4caf50', '#4caf50')

    def _stop_camera(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(5000)
        self._worker = None

    def _on_worker_done(self):
        self._worker = None
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_video.setEnabled(True)
        self._set_status('已停止')

    def _on_error(self, msg):
        self._set_status(f'错误: {msg}', '#f44336', '#f44336')

    # ── 帧更新 ──

    def _on_frame(self, frame, au_dict, head_pose, blendshapes=None):
        self._frame_count += 1
        update_bars = (self._frame_count % 2 == 0)

        if self._mirrored:
            frame = cv2.flip(frame, 1)

        pixmap = _cv_frame_to_qpixmap(frame)
        scaled = pixmap.scaled(
            self._video_label.size(),
            Qt.KeepAspectRatio,
            Qt.FastTransformation,
        )
        self._video_label.setPixmap(scaled)

        if update_bars:
            for au_code, bar in self._au_bars.items():
                val = int(au_dict.get(au_code, 0.0) * 100)
                bar.setValue(val)

            for axis, lbl in self._pose_labels.items():
                val = head_pose.get(axis, 0.0)
                name = AXIS_NAMES.get(axis, axis)
                lbl.setText(f'{name}\n{val:+.1f}°')

        if update_bars:
            result = self._emotion_inferrer.infer(
                au_dict, self._latest_hr, self._latest_br)
            self._update_emotion_ui(result)

            # 喂入cue分析器
            self._cue_analyzer.feed(result, au_dict, head_pose)
            if blendshapes:
                self._cue_analyzer.feed_blendshapes(blendshapes)
            cues = self._cue_analyzer.get_cues(
                self._latest_hr, self._latest_br)
            self._update_cue_ui(cues)

    _CUE_LABELS = {
        'affect_blend': '情绪混合',
        'masking': '情绪掩蔽',
        'lability': '表达不稳',
        'micro_count': '微表情',
        'fake_smile': '假笑指数',
        'asymmetry': '不对称性',
        'motor_suppression': '运动抑制',
        'cognitive_load': '认知负荷',
        'physio_mismatch': '身心不一致',
    }

    _CUE_COLORS = {
        'affect_blend': '#ab47bc',    # 紫
        'masking': '#ff9800',         # 橙
        'lability': '#42a5f5',        # 蓝
        'micro_count': '#ffeb3b',     # 黄
        'fake_smile': '#ef5350',      # 红
        'asymmetry': '#78909c',       # 灰蓝
        'motor_suppression': '#8d6e63', # 棕
        'cognitive_load': '#26c6da',  # 青
        'physio_mismatch': '#66bb6a', # 绿
    }

    _CORE_CUES = ['fake_smile', 'masking', 'lability', 'affect_blend']
    _SEC_CUES = ['motor_suppression', 'cognitive_load', 'asymmetry',
                 'physio_mismatch', 'micro_count']

    def _update_cue_ui(self, cues: dict):
        for cue_key in self._CORE_CUES:
            data = cues.get(cue_key, {'score': 0.0})
            pct = min(100, int(data['score'] * 100))
            bar = self._cue_bars.get(cue_key)
            if bar:
                bar.setValue(pct)
                detail = data.get('detail', '')
                bar.setFormat(
                    f'{self._CUE_LABELS[cue_key]}  {detail}'[:30])
                # 分数越高颜色偏红
                hue = max(0, 120 - pct * 1.2)  # 120(green)→0(red)
                bar.setStyleSheet(
                    'QProgressBar { background: #2a2a2a; border: none; '
                    'border-radius: 3px; text-align: left; '
                    'color: #aaa; font-size: 10px; min-height: 14px; }'
                    f'QProgressBar::chunk {{ background: hsl({hue}, 70%, 50%); '
                    'border-radius: 3px; }')

        for cue_key in self._SEC_CUES:
            data = cues.get(cue_key, {'score': 0.0})
            pct = min(100, int(data['score'] * 100))
            bar = self._cue_bars_sec.get(cue_key)
            if bar:
                bar.setValue(pct)
    _EMOTION_COLORS = {
        'happiness': '#4caf50',
        'sadness': '#42a5f5',
        'surprise': '#ff9800',
        'fear': '#ab47bc',
        'anger': '#ef5350',
        'disgust': '#8d6e63',
        'contempt': '#78909c',
        'neutral': '#888',
    }

    def _update_emotion_ui(self, result):
        emo = result.dominant_emotion
        color = self._EMOTION_COLORS.get(emo, '#888')
        conf_pct = int(result.confidence * 100)
        valence_pct = int(result.valence * 100)
        arousal_pct = int(result.arousal * 100)

        self._emotion_label.setText(result.dominant_label)
        self._emotion_label.setStyleSheet(
            f'color: {color}; font-size: 18px; font-weight: bold;'
            'padding: 2px 0;')
        self._emotion_icon.setStyleSheet(
            f'color: {color}; font-size: 28px; padding: 2px 0;')

        self._emotion_bar.setValue(conf_pct)
        self._emotion_bar.setStyleSheet(
            'QProgressBar { background: #2a2a2a; border: none; '
            'border-radius: 3px; }'
            f'QProgressBar::chunk {{ background: {color}; '
            'border-radius: 3px; }}')

        self._valence_bar.setValue(valence_pct)
        self._arousal_bar.setValue(arousal_pct)

        sec_emo, sec_score = result.secondary_emotion
        if sec_score > 0.1:
            sec_label = self._EMOTION_COLORS.get(sec_emo, '#666')
            sec_name = {
                'happiness': '快乐', 'sadness': '悲伤',
                'surprise': '惊讶', 'fear': '恐惧',
                'anger': '愤怒', 'disgust': '厌恶',
                'contempt': '轻蔑', 'neutral': '中性',
            }.get(sec_emo, sec_emo)
            self._emotion_secondary.setText(
                f'次级: {sec_name}  ({sec_score:.0%})')
            self._emotion_secondary.setStyleSheet(
                f'color: {sec_label}; font-size: 11px; padding: 2px 0;')
        else:
            self._emotion_secondary.setText('')
        
        if result.is_micro:
            self._emotion_secondary.setText(
                self._emotion_secondary.text() + ' ⚡微表情')
            self._emotion_secondary.setStyleSheet(
                f'color: #ffeb3b; font-size: 11px; padding: 2px 0;')



    def _on_fps(self, fps):
        self._fps_label.setText(f'帧率: {fps:.1f}')

    def _on_physio(self, hr, br):
        self._latest_hr = hr
        self._latest_br = br
        if hr > 0:
            self._hr_label.setText(f'心率\n{hr:.0f} BPM')
        if br > 0:
            self._br_label.setText(f'呼吸\n{br:.0f} /min')

    # ── 视频 ──

    def _open_video(self):
        if self._video_timer and self._video_timer.isActive():
            self._toggle_video_playback()
            return

        path, _ = QFileDialog.getOpenFileName(
            self, '选择视频文件', '',
            '视频文件 (*.mp4 *.mov *.avi *.mkv *.webm);;所有文件 (*)',
        )
        if not path:
            return

        self._set_status(f'处理中: {Path(path).name}...',
                         '#ff9800', '#ff9800')
        self._btn_start.setEnabled(False)
        self._btn_video.setEnabled(False)
        self._run_video(path)

    def _toggle_video_playback(self):
        if self._video_timer.isActive():
            self._video_timer.stop()
            self._btn_video.setText('▶  继续')
            self._btn_video.setEnabled(True)
            self._set_status('已暂停', '#ff9800', '#ff9800')
        else:
            self._video_timer.start(100)
            self._btn_video.setText('⏸  暂停')
            self._btn_video.setEnabled(True)
            self._set_status('播放中', '#4caf50', '#4caf50')

    def _run_video(self, path):
        analyzer = MediaPipeFaceAnalyzer(model_path=self._model_path)
        results = analyzer.process_video(path)
        analyzer.close()

        self._video_results = results
        self._video_idx = 0

        self._timeline.load_au_data(results)
        self._timeline.setVisible(True)

        self._video_timer = QTimer()
        self._video_timer.timeout.connect(self._video_tick)
        self._video_timer.start(100)

        self._btn_video.setText('⏸  暂停')
        self._btn_video.setEnabled(True)
        self._btn_start.setEnabled(False)
        self._set_status(
            f'{Path(path).name}  ({len(results)} 帧)', '#4caf50', '#4caf50')

    def _on_timeline_seek(self, ms: float):
        if not self._video_results:
            return
        idx = int(ms / 100.0)
        self._video_idx = min(max(0, idx), len(self._video_results) - 1)
        self._show_seek_frame()

    def _show_seek_frame(self):
        res = self._video_results[self._video_idx]
        blendshapes = res.get('blendshapes', {})
        au_dict = self._au_mapper.to_au(blendshapes)
        head_pose = res.get('head_pose', {})

        canvas = np.full((480, 640, 3), 28, dtype=np.uint8)
        ts = res.get('timestamp_ms', self._video_idx * 100)
        total = len(self._video_results)
        cv2.putText(canvas,
                    f'帧 {self._video_idx + 1} / {total}    '
                    f'时间 {ts:.0f} ms',
                    (20, 240), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (255, 200, 80), 2)
        self._on_frame(canvas, au_dict, head_pose, blendshapes)

    def _video_tick(self):
        if self._video_idx >= len(self._video_results):
            self._video_timer.stop()
            self._btn_start.setEnabled(True)
            self._btn_video.setText('📂  打开视频')
            self._btn_video.setEnabled(True)
            self._set_status(
                f'完成 ({len(self._video_results)} 帧)', '#4caf50', '#4caf50')
            return

        res = self._video_results[self._video_idx]
        blendshapes = res.get('blendshapes', {})
        au_dict = self._au_mapper.to_au(blendshapes)
        head_pose = res.get('head_pose', {})

        canvas = np.full((480, 640, 3), 28, dtype=np.uint8)
        active = [(k, v) for k, v in au_dict.items() if v > 0.1]
        y = 30
        if active:
            for au_code, val in sorted(active)[:12]:
                name = AU_NAMES.get(au_code, au_code)
                cv2.putText(canvas, f'{au_code} {name}: {val:.2f}',
                            (20, y), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, (0, 230, 120), 1)
                y += 26
        else:
            cv2.putText(canvas, '(中性)', (20, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (140, 140, 140), 1)

        ts = res.get('timestamp_ms', self._video_idx * 100)
        cv2.putText(canvas,
                    f'时间: {ts:.0f}ms    帧: {self._video_idx + 1}/{len(self._video_results)}',
                    (20, 450), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (180, 180, 180), 1)

        self._on_frame(canvas, au_dict, head_pose, blendshapes)
        self._timeline.set_time(ts)
        emotion_result = self._emotion_inferrer.infer(au_dict)
        self._snapshots.append({
            'timestamp_ms': ts,
            'face': {
                'aus': au_dict,
                'head_pose': head_pose,
            },
            'emotion': emotion_result.to_dict(),
            'physiological': {'heart_rate': 0, 'breath_rate': 0},
            'voice': {},
            'language': {},
        })
        self._video_idx += 1

    # ── 辅助 ──
