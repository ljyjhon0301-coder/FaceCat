"""AU 时间线组件 — pyqtgraph 波形 + 播放头。"""

from typing import Dict, List, Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from core.face import MediaPipeBlendshapeLookupAU
from core.face._constants import AU_NAMES as _AU_NAMES


class TimelineWidget(QWidget):
    """pyqtgraph 时间线：叠画多条 AU 波形 + 拖拽播放头。"""

    playhead_moved = Signal(float)  # 用户拖拽播放头 → 时间(ms)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._au_data: Dict[str, np.ndarray] = {}
        self._time_axis: np.ndarray = np.array([])
        self._duration_ms = 0.0
        self._current_ms = 0.0
        self._last_emitted_ms = 0.0
        self._colors = [
            '#00e676', '#ff9100', '#448aff', '#ff4081', '#00bcd4',
        ]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._plot = pg.PlotWidget()
        self._plot.setBackground('#1a1a1a')
        self._plot.showGrid(x=True, y=True, alpha=0.15)
        self._plot.setLabel('bottom', '时间', units='s')
        self._plot.getAxis('left').setTicks([])
        self._plot.setMenuEnabled(False)
        self._plot.setMouseEnabled(x=True, y=False)
        self._plot.scene().sigMouseClicked.connect(self._on_click)
        self._plot.scene().sigMouseMoved.connect(self._on_mouse_move)

        self._playhead_line = pg.InfiniteLine(
            pos=0, angle=90, pen=pg.mkPen('#ff5252', width=1.5))
        self._plot.addItem(self._playhead_line)
        self._is_dragging = False

        layout.addWidget(self._plot)

    def load_au_data(self, results: List[Dict],
                     selected_aus: Optional[List[str]] = None):
        """从视频分析结果加载 AU 时间序列。

        Args:
            results: process_video 返回的帧结果列表。
            selected_aus: 要显示的 AU 代码列表，默认显示 5 个主要 AU。
        """
        self._plot.clear()
        self._plot.addItem(self._playhead_line)

        if not results:
            return

        if selected_aus is None:
            selected_aus = ['AU12', 'AU6', 'AU4', 'AU1', 'AU22']

        timestamps = np.array([
            r.get('timestamp_ms', i * 100) for i, r in enumerate(results)
        ])
        self._time_axis = timestamps / 1000.0
        self._duration_ms = timestamps[-1] if len(timestamps) > 0 else 0.0

        mapper = MediaPipeBlendshapeLookupAU()

        all_au_dicts = [
            mapper.to_au(r.get('blendshapes', {})) for r in results
        ]

        self._au_data.clear()
        for idx, au_code in enumerate(selected_aus):
            values = [ad.get(au_code, 0.0) for ad in all_au_dicts]
            signal = np.array(values)
            self._au_data[au_code] = signal

            color = self._colors[idx % len(self._colors)]
            name = _AU_NAMES.get(au_code, au_code)
            pen = pg.mkPen(color, width=1.0)
            self._plot.plot(
                self._time_axis, signal,
                pen=pen, name=f'{au_code} {name}',
            )

        self.set_time(0.0)

    def set_time(self, ms: float):
        """设置播放头位置 (毫秒)。"""
        self._current_ms = ms
        self._playhead_line.setPos(ms / 1000.0)

    def _on_click(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = self._plot.getViewBox().mapSceneToView(event.scenePos())
        ms = pos.x() * 1000.0
        if 0.0 <= ms <= self._duration_ms:
            self._is_dragging = True
            self.set_time(ms)
            self.playhead_moved.emit(ms)

    def _on_mouse_move(self, pos):
        if not self._is_dragging:
            return
        vb = self._plot.getViewBox()
        view_pos = vb.mapSceneToView(pos)
        ms = view_pos.x() * 1000.0
        if 0.0 <= ms <= self._duration_ms:
            self.set_time(ms)
            if abs(ms - self._last_emitted_ms) > 50.0:
                self._last_emitted_ms = ms
                self.playhead_moved.emit(ms)

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self._is_dragging = False
        super().leaveEvent(event)
