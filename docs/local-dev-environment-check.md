# FaceCat 本机开发环境检查清单

检查日期：2026-05-23  
工作目录：`E:\VibeCoding\FaceCat`

## 1. 机器基础情况

| 项目 | 当前状态 | 结论 |
|---|---|---|
| OS | Windows 11 专业版 10.0.26200 | 可用 |
| CPU | 12 逻辑核 | 可用 |
| 内存 | 31.9 GB | 适合本地 MVP |
| GPU | NVIDIA GeForce GTX 1660 Ti, 6GB VRAM | 适合 MediaPipe/OpenCV/轻量推理，不适合大模型训练 |
| NVIDIA Driver | 591.59, CUDA runtime 13.1 | 驱动可用 |
| CUDA Toolkit | `nvcc` 未安装 | P0/P1 不需要，训练或自编译 CUDA 才需要 |
| C 盘 | 剩余 23.6 GB / 234.2 GB | 偏紧 |
| D 盘 | 剩余 69.9 GB / 284.1 GB | 建议放视频样本/缓存 |
| E 盘 | 剩余 32.6 GB / 434.6 GB | 当前项目盘，视频多了会紧 |

## 2. 已安装

| 工具 | 版本/路径 | 用途 |
|---|---|---|
| Conda | 22.11.1, `C:\Users\Liu_jy\miniconda3` | Python 环境管理 |
| Python base | 3.9.15 | 当前太旧，建议新建 3.11 环境 |
| Node.js | v22.20.0, `C:\Program Files\nodejs\node.exe` | 前端开发 |
| npm | 10.9.3 | 当前有异常，见第 4 节 |
| corepack | 0.34.0 | 可启用 pnpm |
| Git | 2.53.0.windows.2 | 可用 |
| CMake | 4.1.2 | 可用 |
| Docker | 29.4.3 | 可用，P0/P1 非必须 |
| Docker Compose | v5.1.3 | 可用，P0/P1 非必须 |
| VS Code | 已安装 | 可用 |
| winget | 已安装 | 可用于安装 ffmpeg 等工具 |

Conda 现有环境：

- `base`
- `transformers`
- `ultralytics`

## 3. 缺失或需要补齐

### 必须补齐

| 项目 | 当前状态 | 建议 |
|---|---|---|
| Python 3.11 环境 | 当前 base 是 3.9.15 | 新建 `facecat` conda env，不要直接污染 base |
| ffmpeg / ffprobe | 未安装 | 必装，用于视频解码、抽帧、元数据读取 |
| pnpm | 命令未启用 | 用 corepack 启用 |
| Python 核心依赖 | 多数缺失 | 在 `facecat` 环境内安装 |
| Git 仓库 | 当前目录不是 git repo | 开始开发前建议 `git init` |

### Python 包检查结果

当前 base Python：

- 已有：`pydantic`, `opencv-python`, `numpy`, `pandas`
- 缺失：`fastapi`, `uvicorn`, `mediapipe`, `scipy`, `polars`, `pyarrow`, `scikit-learn`, `pytest`

建议不要在 base 里补，直接建新环境。

### 可后置

| 项目 | 当前状态 | 何时需要 |
|---|---|---|
| Rust / Cargo | 未安装 | 只有选择 Tauri 时需要 |
| Visual Studio C++ Build Tools / `cl` | 未检测到 | pip 轮子不够用、需要本地编译时再装 |
| CUDA Toolkit / `nvcc` | 未安装 | 训练 CUDA 扩展或源码编译时需要 |
| Playwright | 未安装/无法通过 npx 检查 | 前端测试阶段再装 |
| Electron | 未安装 | 桌面封装阶段再装 |

## 4. 需要注意的问题

### 4.1 npm 当前有异常

现象：

- `node -v` 正常：`v22.20.0`
- `npm -v` 正常：`10.9.3`
- `npm list -g --depth=0` 报错
- `npx playwright --version` 报错

日志中看到：

```text
node v22.20.0
npm 10.9.3
stack: C:\Users\Liu_jy\AppData\Roaming\nvm\v20.19.5\node_modules\npm\...
```

这说明当前 Node/npm 路径可能混用了：

- `C:\Program Files\nodejs`
- `C:\Users\Liu_jy\AppData\Roaming\nvm`
- `C:\Users\Liu_jy\AppData\Roaming\npm`

建议在正式启动前端项目之前统一 Node 来源。两种方式选一种：

方案 A：使用官方 Node，清理/禁用 nvm 路径。

方案 B：使用 nvm-windows，重新安装并切到同一版本：

```powershell
nvm install 22.20.0
nvm use 22.20.0
where.exe node npm npx
npm cache verify
```

修好后再启用 pnpm。

### 4.2 磁盘空间偏紧

视频项目很容易产生缓存、缩略图、特征文件和导出片段。建议：

- 项目源码仍放 `E:\VibeCoding\FaceCat`。
- 大视频样本和缓存优先放 `D:\FaceCatData`。
- 不要把视频缓存放 C 盘。

## 5. 推荐安装/初始化清单

### 5.1 建 Python 环境

```powershell
conda create -n facecat python=3.11 -y
conda activate facecat
python -m pip install -U pip
```

### 5.2 安装 Python 依赖

```powershell
pip install fastapi "uvicorn[standard]" pydantic opencv-python mediapipe numpy scipy pandas polars pyarrow pytest
```

可选增强：

```powershell
pip install scikit-learn python-multipart aiofiles rich typer
```

### 5.3 安装 ffmpeg

```powershell
winget install --id Gyan.FFmpeg -e
```

安装后重新打开终端，确认：

```powershell
ffmpeg -version
ffprobe -version
```

### 5.4 启用 pnpm

先修复 npm/Node 路径混用问题，然后执行：

```powershell
corepack enable
corepack prepare pnpm@latest --activate
pnpm --version
```

### 5.5 初始化 Git 仓库

```powershell
git init
```

建议同时添加 `.gitignore`，至少忽略：

```gitignore
.venv/
__pycache__/
node_modules/
dist/
build/
*.facecat/
data/
cache/
exports/
*.mp4
*.mov
*.avi
```

## 6. 当前开工建议

按现有环境，建议先补齐这 5 件事：

1. 新建 `facecat` Python 3.11 conda 环境。
2. 安装 `ffmpeg`。
3. 修复 Node/npm 路径混用，再启用 `pnpm`。
4. 安装 Python MVP 依赖：FastAPI、MediaPipe、OpenCV、Polars/PyArrow、pytest。
5. 初始化 git 仓库。

补齐后就可以开始做第一个闭环：

```text
video.mp4 -> features.csv/parquet -> events.json -> React 时间线 UI -> annotations.json
```
