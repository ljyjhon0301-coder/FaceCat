# FaceCat — 面部行为线索标注工具

## 角色

你是一位资深计算机视觉与信号处理工程师，专攻面部行为分析（FACS AU）、生理信号处理（rPPG、心率/呼吸率）、语音分析（F0、jitter、shimmer）和语言分析（Whisper、NLP 疏离化检测）。同时负责 PySide6 桌面界面和后续 FastAPI 本地服务开发。

代码追求可扩展性、可读性和工程质量，遵循 Google Python Style Guide。架构优先使用抽象基类、策略模式和清晰数据契约。

## 项目定位

FaceCat 是本地优先的 AI 辅助面部行为视频标注工具。输入视频或摄像头预览，输出四轨同步时间线，并支持人工复核、标注和导出。

FaceCat 不是测谎仪，不自动判断真实情绪、心理状态或是否说谎。所有“情绪推断”和“不一致性线索”都只能作为统计提示和复核线索。

## 目录结构

```text
FaceCat/
├── core/
│   ├── face/              # 面部: MediaPipe -> AU/head pose
│   ├── physiological/     # 生理: CHROM/POS rPPG + 呼吸率
│   ├── voice/             # 语音: F0/RMS/语速/jitter/shimmer
│   ├── language/          # 语言: Whisper + 疏离化检测
│   ├── emotion/           # AU -> 弱情绪/valence/arousal
│   ├── cue/               # 不一致性线索统计指标
│   └── sync/              # snapshot + JSON/CSV 导出
├── ui/
│   ├── main_window.py     # PySide6 主窗口
│   ├── timeline_widget.py # pyqtgraph AU 波形时间线
│   └── __init__.py
├── data/                  # 本地模型文件，仓库默认忽略
├── docs/
│   └── 技术方案.md
├── .claude/
│   └── agents/            # Claude 专精角色 agent 定义
├── run_face.py
├── run_ui.py
├── README.md
├── PLAN.md
└── CLAUDE.md
```

## 角色间工作流

```text
PM -> 工程师 -> 测试 -> 开发者(review) -> PM(更新计划) -> 下一轮
```

详细流程见 `.claude/agents/`。

## 已完成模块

### 第 1 步：MediaPipe -> AU 映射层 + PySide6 桌面界面

- `MediaPipeFaceAnalyzer`：468 landmarks、52 blendshapes、solvePnP 头部姿态。
- `MediaPipeBlendshapeLookupAU`：blendshape -> 18 个 FACS AU。
- PySide6 `MainWindow`：实时摄像头、AU 进度条、头部姿态、视频文件回放。
- CLI `run_face.py`：`--camera`、`--camera-index N`、`--video PATH`。
- 模型 `data/face_landmarker.task` 本地使用，仓库默认不提交。

### 第 2 步：pyqtgraph AU 时间线播放器

- `TimelineWidget`：多轨 AU 波形叠加，默认 AU12/AU6/AU4/AU1/AU25。
- 播放头：点击和拖拽跳转。
- 暂停/继续：视频播放和时间线同步。
- 摄像头模式自动隐藏时间线。

### 第 3 步：rPPG 心率 + 呼吸率

- `CHROMRPPG` 和 `POSRPPG`。
- `BreathAnalyzer`。
- 额头 ROI RGB 采样。
- UI 右侧生理信号面板。

### 第 4 步：语音、语言、同步核心模块

- `LibrosaVoiceAnalyzer`：F0、RMS、语速、jitter、shimmer。
- `WhisperTranscriber`：带时间戳转录接口。
- `DetachmentAnalyzer`：中文疏离化语言检测。
- `UnifiedSnapshot` 和 JSON/CSV 导出。

### 第 5 步：情绪弱推断与不一致性线索

- `EmotionInferrer`：Ekman AU 规则、valence/arousal、微表情低幅提示。
- `DeceptionCueAnalyzer`：9 个统计线索。
- UI 右侧情绪和线索面板。

## 当前优先级

1. 主仓库整理：当前本地项目是主线，GitHub `FaceCat/main` 应指向当前代码和文档。
2. 项目文件格式：`project.facecat/` 分离资产、分析运行、人工标注和导出。
3. 视频质量门控：模糊、光照、脸部占比、遮挡、极端头姿。
4. 候选事件检测：基于 AU/blendshape 曲线生成 onset/apex/offset。
5. 标注闭环：自动候选和人工确认分离存储，导出包含来源、质量和模型版本。
6. 语音/语言轨接入离线批处理和 UI。

## 架构约定

- 每一轨 = 抽象基类 + 具体实现，可插拔。
- 自动结果和人工标注分离保存。
- 分析运行不可变，重新分析生成新的 AnalysisRun。
- 数据处理按约 100ms 采样一帧，输出统一 snapshot。
- 项目数据必须保留 `video_id`、`track_id`、`analysis_run_id` 的扩展空间。
- 模型通过 adapter 接入，UI 不感知模型细节。
- 桌面 UI 当前使用 PySide6；后续本地服务可用 FastAPI。
- 不做实时流处理承诺；摄像头模式用于预览、调试和演示。
- 不做自动说谎判断。

## 开发约束

### 代码规范

- Google Python Style Guide。
- 4 空格缩进，2 空行隔顶级定义，1 空行隔方法。
- import 顺序：stdlib -> third-party -> local，每组内按字母序。
- 类名 CamelCase，方法/函数 snake_case，模块级常量 UPPER_CASE。
- 类型注解必须用 `Optional[X]`，不用 `X | None`。
- docstring 用三重引号，首行一句话总结。
- 禁止节注释横幅，用方法名表达意图。
- 单个方法尽量不超过 50 行。

### PySide6 / QThread 生命周期

- QThread 必须在退出前安全停止：窗口 `closeEvent` 中调用 `worker.stop() + worker.wait()`。
- 线程停止使用 `QThread.requestInterruption()` + `isInterruptionRequested()`。
- 停止后将 `self._worker = None`。
- 信号名不与 Qt 内置信号冲突，使用 `error_occurred` 等明确名称。

### venv 与运行

- Python：`/opt/homebrew/bin/python3`。
- venv：`~/venvs/facecat`。
- 激活：`source ~/venvs/facecat/bin/activate`。
- 所有依赖在 venv 中安装，不污染系统 Python。

## 开发日志

| 日期 | 内容 |
|---|---|
| 2026-05-13 | 第 1 步完成：MediaPipe FaceAnalyzer + AU 查表映射 + head_pose |
| 2026-05-13 | PySide6 桌面界面：MainWindow + CameraWorker + AU 面板 |
| 2026-05-13 | CLI `run_face.py`：摄像头和视频入口 |
| 2026-05-13 | 修复 QThread 退出崩溃 |
| 2026-05-13 | UI 汉化、AU17 修正、新增 AU22 |
| 2026-05-13 | 第 2 步完成：pyqtgraph AU 时间线播放器 |
| 2026-05-13 | 测试覆盖：15 个 face 相关测试通过 |
| 2026-05-13 | 第 3 步完成：rPPG 心率 + 呼吸率 |
| 2026-05-23 | 合并远端研究文档中有价值的目标、边界、质量门控和项目格式到当前文档 |
