# FaceCat 架构与落地方案优化评审

评审日期：2026-05-23  
关联文档：

- `docs/micro-expression-market-opportunity.md`
- `docs/technical-theory-architecture.md`
- `docs/cost-and-tech-stack.md`

## 1. 总体评审结论

现有方案方向正确，但还可以进一步收窄和工程化。

最值得保留的是：

- 不做“读心/测谎/真实情绪判断”。
- 以 FACS / AU / 面部行为事件为理论基础。
- 本地优先，保留证据链和人工复核。
- UI、分析引擎、模型、数据层解耦。

最需要优化的是：

- 第一版范围仍然偏大，应先做“本地视频标注提效工具”，不要先做完整桌面平台、SDK、云端或多模态。
- 开源依赖有许可证风险，不能把所有研究工具默认打包进商业产品。
- 需要更早定义项目文件格式、分析任务 API、性能预算和评测闭环。
- 需要把“候选事件召回率”和“每分钟误报数量”作为比情绪准确率更重要的指标。

优化后的第一版目标：

> FaceCat v0 应是一个本地运行的 AI 辅助面部行为视频标注原型：导入视频，生成帧级特征，发现候选短时变化片段，支持人工修正和导出。

## 2. 产品范围优化

### 2.1 从平台改成工具

原方案容易让团队一上来想做：

- 桌面工作台。
- SDK。
- 批处理。
- 团队协作。
- 多模态。
- 自研模型。
- 报告系统。

这会拖慢验证。建议第一阶段只做一个窄工具：

```text
视频 -> 特征曲线 -> 候选事件 -> 人工标注 -> 导出
```

第一版不做：

- 登录和账号系统。
- 云端存储。
- 多用户协作。
- 实时摄像头分析。
- 自研深度模型训练。
- 情绪类别自动判断。
- SDK 封装。

### 2.2 从“微表情识别”改成“短时面部行为标注”

“微表情识别”是一个高预期、高争议词。建议对外主文案用：

- 面部行为视频标注。
- AU/FACS 辅助分析。
- 短时面部变化候选检测。
- 研究和用户测试视频分析。

“微表情”可以作为 SEO 和功能说明出现，但不要成为第一版价值承诺的中心。

## 3. 依赖与许可证优化

开源工具不能只看能力，还要看商业化与再分发限制。当前更合理的策略是：**按风险分层接入，不把研究工具默认捆绑进商业版**。

| 依赖 | 能力 | 许可证/风险判断 | 建议 |
|---|---|---|---|
| MediaPipe | landmarks、blendshapes、face landmarker、端侧能力 | Apache 2.0，商业化相对友好，但仍需检查具体模型和二进制分发条款 | MVP 默认底座 |
| Py-Feat | AU、表情分析、研究友好 | 代码为 MIT；其依赖和模型有各自许可证，需要逐项核查 | 可作为研究模式或内部 baseline |
| OpenFace | AU、头姿、眼动，学术影响力强 | 官方许可证写明 noncommercial research use，商业使用需联系授权 | 不默认打包；只做可选外部 adapter 或评测 baseline |
| LibreFace | AU/表情分析，实时深度模型 | README 明确 free-to-use non-commercial toolbox，并采用 USC research license | 不默认打包；仅做研究参考或用户自带模型 adapter |

依赖策略建议：

1. MVP 默认只内置 MediaPipe 类商业友好底座。
2. Py-Feat 可作为内部验证工具，但发布前要做模型/依赖许可证清单。
3. OpenFace/LibreFace 不随商业包分发，除非拿到明确商业授权。
4. 所有模型 adapter 都要记录 `license`, `source_url`, `model_version`, `redistribution_allowed`。

参考来源：

- OpenFace commercial license note: https://github.com/TadasBaltrusaitis/OpenFace
- OpenFace license: https://raw.githubusercontent.com/TadasBaltrusaitis/OpenFace/master/OpenFace-license.txt
- Py-Feat license: https://raw.githubusercontent.com/cosanlab/py-feat/master/LICENSE
- LibreFace README/license note: https://github.com/ihp-lab/LibreFace
- MediaPipe license: https://raw.githubusercontent.com/google-ai-edge/mediapipe/master/LICENSE

## 4. 技术栈优化

### 4.1 第一阶段不要急着封桌面壳

原文写了 Tauri/Electron 二选一。优化建议是：**前 2-4 周先不选桌面壳**。

更快的原型形态：

```text
Python FastAPI analysis service
+ React/Vite browser UI
+ local project folder
```

优势：

- 调试简单。
- 不被桌面打包问题拖住。
- Python 模型依赖更好处理。
- UI 之后仍可被 Electron/Tauri 复用。
- 后续 CLI、SDK、私有化服务都可以复用同一个引擎 API。

阶段选择：

| 阶段 | 推荐形态 |
|---|---|
| Spike | Python CLI + 静态 HTML/React UI |
| MVP | FastAPI 本地服务 + React UI |
| 可交付桌面版 | Electron 或 Tauri 包一层 |
| 私有化/团队版 | Headless server + Web UI |

### 4.2 Electron vs Tauri 的实际建议

如果后续要快速交付 Windows 桌面版，优先 Electron。原因是：

- 子进程管理和本地服务集成成熟。
- 前端生态顺。
- 调试和分发资料多。

如果后续更看重安装包体积、安全边界和原生质感，再评估 Tauri。不要在验证期把时间花在桌面壳选型上。

## 5. 项目文件格式优化

建议第一天就采用“项目文件夹”格式，后续再压缩成 `.facecatproj`。

```text
project.facecat/
  manifest.json
  assets/
    original.mp4
    thumbnails/
  runs/
    run_20260523_001/
      run.json
      features.parquet
      events.json
      quality.json
  annotations/
    annotations.json
  exports/
    events.csv
    report.html
```

关键点：

- `assets` 保存原始或引用路径。
- `runs` 是不可变分析结果。
- `annotations` 是人工标注，不覆盖自动结果。
- `exports` 是可再生成产物。

这样未来支持多次模型运行、参数对比、人工复核和报告审计时不会乱。

## 6. API 契约优化

前端不要直接读模型输出文件，而是通过稳定 API 或 SDK 层访问。

MVP 最小 API：

```text
POST /projects
POST /projects/{project_id}/videos
POST /analysis-runs
GET  /analysis-runs/{run_id}
GET  /analysis-runs/{run_id}/features?track_id=&from_ms=&to_ms=
GET  /analysis-runs/{run_id}/events
POST /annotations
PATCH /annotations/{annotation_id}
POST /exports
```

长期收益：

- UI 可以换。
- 引擎可以换。
- 本地版和私有化版可以共用接口。
- SDK 可以直接包这套 API。

## 7. 算法路线优化

### 7.1 MVP 不要追求 AU 完整性

如果第一版要等完整 AU 强度都稳定，会慢。建议第一版把特征分成两类：

- 必须稳定：face bbox、landmarks、head pose、quality、基础 blendshape。
- 可选增强：AU、gaze、光流、局部纹理。

事件检测第一版可以基于：

- mouth smile/frown 类 blendshape。
- eyebrow/eye landmarks。
- head pose gate。
- face quality gate。
- peak/change detection。

先验证“候选片段是否有用”，不要先卷“AU 模型准确率”。

### 7.2 指标从准确率改成标注提效

第一阶段主指标：

- 候选事件召回率：用户关心的片段有没有被覆盖。
- 每分钟候选数：误报不能多到用户看不过来。
- 人工节省时间：相比纯手工看视频节省多少。
- 低质量片段拦截率：不该分析的地方是否提示。
- 导出可用率：用户能不能直接拿去做论文/报告/分析。

先不要把“情绪分类准确率”作为核心指标。

### 7.3 候选检测策略

MVP 检测器建议采用规则 ensemble：

1. 每条特征曲线做平滑。
2. 对每个人脸轨迹做局部 baseline。
3. 检测短时间显著变化。
4. 用持续时间约束过滤太长/太短片段。
5. 用头姿、模糊、遮挡过滤伪变化。
6. 合并相近候选。
7. 生成候选理由，例如 `mouth_corner_change + stable_head_pose`。

这套方法不一定最强，但足够透明，适合早期用户一起调。

## 8. 性能预算优化

没有性能预算，原型很容易变成“能跑但没人愿意等”。建议 MVP 设以下软目标：

| 指标 | MVP 目标 |
|---|---|
| 5 分钟 1080p/30fps 视频分析 | 普通开发机 10 分钟内完成 |
| 曲线 UI 响应 | 缩放/拖动 100ms 级反馈 |
| 单项目可承载 | 至少 10 个视频、每个 30 分钟 |
| 内存 | 长视频分块处理，不把所有帧图像常驻内存 |
| 导出 | 事件 CSV/JSON 秒级生成 |

技术手段：

- 分块抽帧和分析。
- 帧图像不进数据库。
- 时间序列用列式存储或分片缓存。
- UI 曲线做 downsampling。
- 分析任务异步执行，可暂停/恢复。

## 9. 评测闭环优化

建议从第一天建一个小型 `golden set`：

- 3 段高质量正脸视频。
- 3 段普通 webcam 视频。
- 2 段头动明显视频。
- 2 段低光/遮挡/模糊视频。
- 2 段说话口型明显视频。

每次改算法都跑：

- 候选数量是否暴涨。
- 明显候选是否漏掉。
- 低质量片段是否被拦截。
- 同一视频多次运行是否稳定。
- 输出 schema 是否兼容旧项目。

这比一开始追公开数据集 SOTA 更适合产品早期。

## 10. 隐私与合规优化

原方案已经强调本地优先，但工程上还要落到功能：

- 项目级开关：是否复制原视频到项目目录，还是只保存引用路径。
- 导出级开关：导出是否包含截图/视频片段。
- 删除机制：删除项目时清理缩略图、缓存、临时帧。
- 日志脱敏：日志不记录用户路径中的敏感信息和人脸图像。
- 原始视频和衍生特征分离：允许用户只分享特征和事件，不分享视频。
- 报告模板默认声明：结果是面部行为候选，不代表真实情绪或意图。

如果未来做云端或团队版，再加：

- 加密存储。
- 权限隔离。
- 访问审计。
- 数据保留期限。
- 同意书/被试授权记录。

## 11. 推荐的优化后开发顺序

### 第 1 阶段：文件级闭环

- `facecat analyze input.mp4 --out project.facecat`
- 生成 `manifest.json`、`features.csv`、`events.json`。
- 简单 React UI 读取项目文件夹。

### 第 2 阶段：本地服务闭环

- FastAPI 管理项目和分析任务。
- WebSocket 推送分析进度。
- 前端支持视频、曲线、事件联动。
- 支持保存人工标注。

### 第 3 阶段：可交付工具

- 封 Electron/Tauri。
- 增加安装包。
- 增加报告导出。
- 增加错误处理和依赖检查。

### 第 4 阶段：商业化试点

- 批量处理。
- 试点客户定制导出格式。
- 模型/依赖许可证清单。
- 合规模板和用户协议。

## 12. 优化后的关键 ADR

建议把下面这些作为早期架构决策记录：

1. `ADR-001`: FaceCat 输出面部行为事件，不输出真实情绪判断。
2. `ADR-002`: 自动候选和人工标注分离存储。
3. `ADR-003`: 分析结果不可变，重新分析生成新的 AnalysisRun。
4. `ADR-004`: 模型通过 adapter 接入，不让 UI 感知模型细节。
5. `ADR-005`: MVP 默认使用商业友好依赖，研究工具只做可选 adapter。
6. `ADR-006`: 第一阶段使用本地 Web UI + Python service，桌面壳后置。
7. `ADR-007`: 所有项目数据采用版本化 schema。

## 13. 最终优化建议

最优路径可以压成一句话：

> 先做一个本地 Web 原型，跑通视频特征、候选事件、人工标注和导出；用清晰的数据契约和模型 adapter 留好未来扩展，而不是一开始做大平台。

如果现在要开工，最应该先做三件事：

1. 定义 `project.facecat` 文件夹格式和 `features/events/annotations` schema。
2. 用 MediaPipe 跑通帧级特征和规则候选检测。
3. 做一个能看视频、曲线、候选片段并保存人工修改的最小 UI。

这三个完成后，FaceCat 才真正从“方向判断”进入“可验证产品”。
