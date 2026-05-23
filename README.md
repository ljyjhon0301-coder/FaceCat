# FaceCat

FaceCat 是一个本地优先的面部行为与微表情线索标注工具。它把视频中的可观察信号转换为同步时间线，帮助研究者或用户测试团队复核、标注和导出证据，而不是自动判断真实情绪或是否说谎。

## 产品边界

FaceCat 做：

- 提取 FACS Action Units、MediaPipe blendshapes、468 点 landmarks 和头部姿态。
- 估算 rPPG 心率、低频呼吸率，并在 UI 中同步展示。
- 提供情绪弱推断和不一致性线索，作为统计提示而不是结论。
- 支持视频时间线、播放头拖拽、人工标注和 JSON/CSV 导出。
- 保持本地处理，默认不上传原始人脸视频。

FaceCat 不做：

- 不做测谎仪。
- 不输出“此人说谎了”“真实情绪是 X”这类高风险结论。
- 不用于招聘、绩效、课堂监控、安防审讯结论或隐蔽采集。
- 不承诺普通 30fps 视频能稳定识别严格意义上的高帧率微表情。

## 当前功能

- **面部轨**：MediaPipe Face Landmarker tasks API，输出 468 landmarks、52 blendshapes、18 个 AU 和 solvePnP 头部姿态。
- **时间线**：pyqtgraph 多轨 AU 波形，默认显示 AU12/AU6/AU4/AU1/AU25，支持点击和拖拽播放头。
- **生理轨**：CHROM/POS rPPG 心率、绿色通道低频呼吸率，摄像头模式下每 3 秒更新。
- **情绪与线索**：Ekman AU 规则弱推断、valence/arousal、不一致性线索面板。
- **语音轨核心模块**：librosa F0、RMS、语速，parselmouth jitter/shimmer。
- **语言轨核心模块**：Whisper 转录接口、中文疏离化规则检测。
- **同步与导出**：统一 snapshot 数据结构，JSON/CSV 导出。
- **运行入口**：CLI `run_face.py` 和 PySide6 桌面 UI `run_ui.py`。

## 环境配置

### 前置要求

- Python 3.14.5：`/opt/homebrew/bin/python3`
- 虚拟环境：`~/venvs/facecat`
- 摄像头可选，用于实时预览和 rPPG 调试

### 创建虚拟环境

```bash
/opt/homebrew/bin/python3 -m venv ~/venvs/facecat
source ~/venvs/facecat/bin/activate
python -m pip install -U pip
```

### 安装依赖

基础运行：

```bash
pip install -e ".[dev]"
```

语音和语言轨可选依赖：

```bash
pip install -e ".[voice,language]"
```

### 下载模型文件

模型文件不提交到仓库，按需下载到 `data/`：

```bash
mkdir -p data
python3 -c "
import urllib.request
url = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'
urllib.request.urlretrieve(url, 'data/face_landmarker.task')
print('Done')
"
```

如果 Google Storage 不可达，可从 HuggingFace 镜像下载 `face_landmarker.task` 放到 `data/face_landmarker.task`。

## 使用

### 命令行

```bash
source ~/venvs/facecat/bin/activate

# 摄像头实时分析
python run_face.py

# 指定摄像头索引
python run_face.py --camera-index 1

# 处理视频文件
python run_face.py --video /path/to/video.mp4
```

### 桌面界面

```bash
source ~/venvs/facecat/bin/activate
python run_ui.py
```

界面能力：

- 左侧视频/摄像头画面。
- 右侧 AU、头部姿态、生理信号、情绪弱推断和不一致性线索。
- 底部摄像头、视频、rPPG 算法、标注和导出控制。
- 视频模式下显示 AU 时间线；按 `M` 标记起止，`Ctrl+E` 导出。

## 项目结构

```text
FaceCat/
├── core/
│   ├── face/              # 面部: MediaPipe -> AU/head pose
│   ├── physiological/     # 生理: CHROM/POS rPPG + 呼吸率
│   ├── voice/             # 语音: F0/RMS/语速/jitter/shimmer
│   ├── language/          # 语言: Whisper + 疏离化检测
│   ├── emotion/           # AU -> 弱情绪/valence/arousal
│   ├── cue/               # 不一致性/欺骗线索统计指标
│   └── sync/              # 统一 snapshot + JSON/CSV 导出
├── ui/
│   ├── main_window.py     # PySide6 主窗口
│   └── timeline_widget.py # pyqtgraph AU 时间线
├── data/                  # 本地模型，仓库默认忽略
├── docs/
│   ├── 项目深度分析与精修方案.md
│   └── 技术方案.md
├── run_face.py
├── run_ui.py
├── PLAN.md
└── AGENTS.md
```

## 下一阶段目标

当前代码已经有多轨核心模块，但产品闭环还需要补齐：

1. 视频质量门控：帧率、脸部占比、模糊、光照、遮挡、极端头姿。
2. 短时事件候选：基于 AU/blendshape 曲线的 onset/apex/offset 候选检测。
3. 项目文件格式：`project.facecat/` 中分离原始资产、分析运行、人工标注和导出。
4. 标注工作流：自动候选和人工确认分离存储，导出时保留来源和质量信息。
5. 评测闭环：维护小型 golden set，跟踪候选召回、每分钟误报和标注节省时间。

第一版成功标准不是“情绪分类准确率”，而是减少人工搜片段和标注时间，并让每个候选都有可回放证据、质量上下文和可审计导出。

## 项目文档

- [项目深度分析与精修方案](docs/项目深度分析与精修方案.md)：后续精修主参考，包含 agent、业务、软件、项目架构、完成度和路线图。
- [技术方案](docs/技术方案.md)：核心技术路线、数据模型、质量门控、候选事件和导出方案。
- [开发计划](PLAN.md)：阶段拆分和当前优先级。
- [Agent 说明](AGENTS.md)：Codex agent 工作入口和协作约束。
