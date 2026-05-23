# FaceCat 开发计划

## 当前定位

FaceCat 第一版定位为本地运行的 AI 辅助面部行为视频标注工具。目标是帮助用户更快发现、复核、标注和导出面部行为事件，而不是自动判断真实情绪或测谎。

核心闭环：

```text
视频 -> 帧级特征 -> 质量门控 -> 候选短时事件 -> 人工复核 -> JSON/CSV/报告导出
```

## 已完成

### 1. 面部轨

- `MediaPipeFaceAnalyzer`：468 landmarks、52 blendshapes、head pose。
- `MediaPipeBlendshapeLookupAU`：MediaPipe blendshape -> 18 个 FACS AU。
- CLI `run_face.py`：摄像头、摄像头索引、视频文件。
- 单元测试：AU 映射、FaceAnalyzer 抽象类、head pose。

### 2. 桌面 UI 与时间线

- PySide6 `MainWindow`：摄像头、视频回放、AU 面板、头部姿态。
- `TimelineWidget`：pyqtgraph 多轨 AU 曲线、播放头、拖拽跳转。
- QThread 生命周期修复：`requestInterruption()` + `wait()`。
- 基础人工标注：按 `M` 标记起止，JSON/CSV 导出。

### 3. 生理轨

- `CHROMRPPG` 和 `POSRPPG` 心率估计。
- `BreathAnalyzer` 低频呼吸率估计。
- 额头 ROI RGB 采样。
- UI 右侧生理信号显示。

### 4. 语音、语言、同步核心模块

- `LibrosaVoiceAnalyzer`：F0、RMS、语速、jitter、shimmer。
- `WhisperTranscriber`：带时间戳转录接口。
- `DetachmentAnalyzer`：中文疏离化规则检测。
- `UnifiedSnapshot` 和导出模块：四轨统一 JSON/CSV。

### 5. 情绪与线索模块

- `EmotionInferrer`：AU 规则弱推断、valence/arousal、微表情低幅提示。
- `DeceptionCueAnalyzer`：9 个不一致性线索，包括假笑、情绪掩蔽、表达不稳、运动抑制、身心不一致等。
- UI 右侧情绪推断和不一致性线索面板。

## 当前差距

| 差距 | 影响 |
|---|---|
| 缺少视频质量门控 | 低光、遮挡、头动、模糊片段可能被错误解释 |
| 缺少候选事件 detector | 用户仍需手动扫完整时间线 |
| 自动结果和人工标注没有完整项目结构 | 难以复现、对比多次分析、做报告审计 |
| 语音/语言轨未接入 UI 和离线批处理 | 多模态闭环不完整 |
| 导出 schema 还不含 quality/event/cue 完整字段 | 后续研究和报告使用不够稳 |
| 文档和代码状态曾不一致 | 已在本轮文档整理中修正 |

## P0: 主仓库与文档整理

- 初始化当前目录为 Git 主仓库。
- 设置 GitHub `ljyjhon0301-coder/FaceCat` 的 `main` 为当前项目主线。
- 将远端早期研究文档中仍有价值的目标、边界和路线合并进本地文档。
- 删除远端旧 `docs/*.md` 研究文档，只保留当前项目文档。

## P1: 项目文件与质量门控

### 1. `project.facecat/` 文件夹格式

```text
project.facecat/
  manifest.json
  assets/
    original.mp4
  runs/
    run_YYYYMMDD_HHMMSS/
      run.json
      features.csv
      events.json
      quality.json
  annotations/
    annotations.json
  exports/
    snapshots.json
    events.csv
```

要求：

- `runs/` 保存不可变自动分析结果。
- `annotations/` 保存人工标注，不覆盖自动候选。
- 每次分析记录模型版本、参数、输入视频哈希和运行时间。
- 数据结构预留 `video_id`、`track_id`、`analysis_run_id`。

### 2. 质量门控

实现 `core/quality/`：

- face detected confidence。
- face box size ratio。
- blur score。
- brightness/contrast。
- head pose extreme angle。
- landmark availability。

输出：

- 帧级 `quality_score`。
- 片段级 `quality_flags`。
- UI 时间线低质量片段提示。

## P2: 候选事件检测

新增 `core/events/`：

- 对 AU/blendshape 曲线做平滑。
- 计算局部 baseline 和 z-score。
- 检测短时间显著上升/回落。
- 生成 onset/apex/offset 候选。
- 用质量门控、头姿和持续时间过滤伪变化。
- 合并相近候选并给出触发原因。

事件 schema：

```json
{
  "event_id": "evt_001",
  "track_id": "face_1",
  "onset_ms": 12340,
  "apex_ms": 12480,
  "offset_ms": 12620,
  "confidence": 0.72,
  "source": "rule_change_point_v1",
  "trigger_features": ["AU12", "AU6"],
  "quality_flags": ["stable_head_pose"],
  "status": "candidate"
}
```

## P3: 标注和导出闭环

- 时间线上显示候选事件区间。
- 支持调整 onset/apex/offset。
- 支持标签：FACS AU、自定义标签、`uncertain`。
- 导出分离自动候选和人工确认。
- CSV/JSON 增加 `quality`、`event`、`cue` 字段。
- 生成 HTML 报告：方法、参数、质量说明、候选事件、人工确认、限制声明。

## P4: 多模态接入

- 离线批处理接入语音轨：F0、RMS、语速、jitter、shimmer。
- 离线批处理接入语言轨：Whisper segments、疏离化评分。
- `SnapshotBuilder` 按时间戳合并四轨。
- UI 增加语音/语言时间线显示。

## P5: 本地服务与未来产品化

当前 PySide6 先保留。后续如需要 Web/桌面混合形态，再拆出本地服务：

```text
POST /projects
POST /projects/{project_id}/videos
POST /analysis-runs
GET  /analysis-runs/{run_id}/features
GET  /analysis-runs/{run_id}/events
POST /annotations
PATCH /annotations/{annotation_id}
POST /exports
```

原则：

- UI 不直接依赖模型输出细节。
- 模型通过 adapter 接入。
- 自动结果、人工标注、导出产物分离。

## Golden Set 与评估指标

维护小型测试集：

- 3 段高质量正脸视频。
- 3 段普通 webcam 视频。
- 2 段头动明显视频。
- 2 段低光、遮挡或模糊视频。
- 2 段说话口型明显视频。

核心指标：

- 候选事件召回率。
- 每分钟候选数量。
- onset/apex/offset 时间误差。
- 低质量片段拦截率。
- 相比纯手工标注的时间节省比例。
- 导出数据能否进入用户已有论文、报告或 UX 分析流程。

## 红线

- 不做招聘、绩效、课堂监控或审讯结论。
- 不自动输出“说谎/真实情绪/心理状态异常”。
- 不把情绪分类准确率作为第一版成功标准。
- 不默认上传原始视频。
- 不把 OpenFace/LibreFace 等非商业友好依赖默认打包进商业发布。
