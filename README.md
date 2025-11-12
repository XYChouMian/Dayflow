<div align="center">

# 🕐 Dayflow for Windows

**AI 驱动的时间追踪应用 - 自动记录、智能分析、可视化你的每一天**

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](https://www.microsoft.com/windows)

[English](README_EN.md) | 简体中文

</div>

---

## 💡 项目起源

本项目灵感来自 [Dayflow by JerryZLiu](https://github.com/JerryZLiu/Dayflow)，原项目是一款优秀的 macOS 时间追踪应用。由于原项目仅支持 macOS 操作系统，在 Windows 下无法使用，因此我按照原项目的核心理念，从零开始为 Windows 平台重新开发了这个版本。

本项目采用不同的技术栈和实现方式，专门针对 Windows 系统进行了优化，旨在为 Windows 用户提供同样优秀的自动化时间追踪体验。

---

## 📖 简介

Dayflow 是一款专为 Windows 设计的自动化时间追踪应用。它在后台静默运行，自动记录你的屏幕活动，使用 AI 智能分析并分类你的工作内容，帮助你：

- 📊 **了解时间分配** - 直观看到时间花在了哪里
- 🤖 **AI 智能分析** - 自动识别和分类不同的活动
- 🎬 **回顾精彩时刻** - 生成延时视频，快速回顾一天
- 🔒 **隐私优先** - 所有数据本地存储，3天自动清理

---

## ✨ 核心特性

### 🎯 自动化记录
- **无感知录制** - 每秒 1 帧低频捕获，不影响系统性能
- **智能暂停** - 系统锁定或睡眠时自动停止录制
- **视频片段化** - 每 15 秒保存一个视频片段，便于分析

### 🧠 AI 智能分析
- **多模型支持** - 支持 Google Gemini、OpenAI、Ollama 等多种 AI 模型
- **自动分类** - 识别工作、会议、休息、学习、娱乐等活动类型
- **中文优化** - AI 提示和结果完全针对中文用户优化
- **定时分析** - 每 15 分钟自动分析新录制的内容

### 📈 可视化看板
- **现代化界面** - 采用渐变色和卡片式设计
- **活动时间轴** - 直观展示一天的活动流
- **统计图表** - matplotlib 驱动的数据可视化
- **延时回放** - 20倍速回放，快速回顾一天

### 🔐 隐私与安全
- **本地存储** - 所有数据存储在本地，不上传云端
- **自动清理** - 3天自动删除旧录制，节省空间
- **凭据加密** - API 密钥通过 Windows 凭据管理器安全存储
- **可选本地 AI** - 支持 Ollama 本地大模型，无需网络

---

## 🚀 快速开始

### 系统要求

- **操作系统**: Windows 10 或 Windows 11
- **Python**: 3.10 或更高版本
- **内存**: 建议 4GB 以上
- **磁盘空间**: 至少 500MB（用于录制存储）
- **FFmpeg**: 必需（用于视频处理）

### 安装步骤

#### 1️⃣ 克隆仓库

```bash
git clone https://github.com/yourusername/dayflow.git
cd dayflow
```

#### 2️⃣ 设置开发环境

双击运行 `setup_dev.bat` 或在命令行执行：

```bash
setup_dev.bat
```

这将自动创建虚拟环境并安装所有依赖。

#### 3️⃣ 安装 FFmpeg

**方式 1: 使用 Chocolatey（推荐）**
```bash
choco install ffmpeg
```

**方式 2: 手动安装**
1. 下载 FFmpeg：https://ffmpeg.org/download.html#build-windows
2. 解压到目录（如 `C:\ffmpeg`）
3. 将 `bin` 目录添加到系统 PATH 环境变量

**验证安装：**
```bash
ffmpeg -version
```

#### 4️⃣ 启动应用

双击运行 `run.bat` 或在命令行执行：

```bash
run.bat
```

---

## ⚙️ 配置

### 首次配置

1. 启动应用后，进入 **设置（Settings）** 视图

2. 配置 AI Provider：
   - **Google Gemini**（推荐）
     - 获取 API Key：https://makersuite.google.com/app/apikey
   - **OpenAI**
     - 获取 API Key：https://platform.openai.com/api-keys
   - **Ollama**（本地）
     - 安装 Ollama：https://ollama.ai/
     - 下载模型：`ollama pull llama2`

3. 调整录制设置（可选）：
   - **Video Quality**: Low / Medium / High
   - **Keep Recordings**: 1-7 天
   - **Analysis Interval**: 分析频率

4. 点击 **💾 Save Settings** 保存配置

### 配置文件位置

所有配置和数据存储在：
```
%LOCALAPPDATA%\Dayflow\
├── config.json          # 应用配置
├── data\
│   └── dayflow.db       # SQLite 数据库
├── recordings\          # 录制片段
│   └── YYYY-MM-DD\
└── timelapses\          # 延时视频
    └── YYYY-MM-DD\
```

---

## 🎯 使用指南

### 基本工作流程

1. **启动应用** - 双击 `run.bat` 或通过系统托盘启动
2. **自动录制** - Dayflow 在后台自动开始录制
3. **AI 分析** - 每 15 分钟自动分析录制内容
4. **查看结果** - 在 Timeline 或 Dashboard 视图查看分析结果
5. **回顾视频** - 点击活动卡片播放延时视频

### 系统托盘功能

右键点击系统托盘图标：
- **打开 Dayflow** - 显示主窗口
- **暂停/继续录制** - 手动控制录制
- **退出** - 关闭应用

### 快捷键

- `Ctrl+Q` - 退出应用
- `F5` - 刷新当前视图

---

## 🏗️ 技术架构

### 技术栈

**前端框架**
- PyQt6 - 现代化 GUI 框架
- matplotlib - 数据可视化
- PyQt6-WebEngine - 视频播放

**后端核心**
- SQLAlchemy - ORM 数据库管理
- APScheduler - 定时任务调度
- mss - 高性能屏幕捕获

**视频处理**
- OpenCV - 图像处理
- FFmpeg - 视频编码和合并

**AI 集成**
- google-generativeai - Gemini API
- openai - OpenAI API
- requests - Ollama API

**系统集成**
- pywin32 - Windows API 集成
- psutil - 系统监控
- keyring - 凭据安全存储

### 项目结构

```
dayflow/
├── src/
│   └── dayflow/
│       ├── main.py              # 应用入口
│       ├── core/                # 核心录制引擎
│       │   ├── screen_recorder.py
│       │   ├── video_processor.py
│       │   └── storage_manager.py
│       ├── analysis/            # AI 分析引擎
│       │   ├── analysis_manager.py
│       │   └── llm_service.py
│       ├── models/              # 数据库模型
│       ├── ui/                  # UI 组件
│       │   ├── main_window.py
│       │   ├── dashboard_view.py
│       │   ├── timeline_view.py
│       │   └── widgets/
│       ├── services/            # 系统服务
│       └── utils/               # 工具函数
├── tests/                       # 测试文件
├── resources/                   # 资源文件
├── scripts/                     # 构建脚本
└── archive/                     # 归档文档
```

### 数据流

```
屏幕捕获 → 视频片段 → AI 分析 → 数据库存储 → UI 展示
    ↓          ↓          ↓          ↓          ↓
  1 FPS     15秒/片   Gemini AI   SQLite   PyQt6
```

---

## 🛠️ 开发指南

### 开发环境设置

```bash
# 安装 Poetry（可选，推荐）
pip install poetry

# 使用 Poetry 安装依赖
poetry install

# 或使用 pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 运行测试

```bash
# 使用 Poetry
poetry run pytest

# 或直接使用 pytest
venv\Scripts\pytest
```

### 代码格式化

```bash
# 格式化代码
poetry run black src/

# 检查代码风格
poetry run ruff check src/

# 类型检查
poetry run mypy src/
```

### 构建可执行文件

```bash
# 安装 PyInstaller
pip install pyinstaller

# 运行构建脚本
poetry run python scripts/build.py
```

构建完成后，可执行文件位于 `dist/` 目录。

---

## 🐛 常见问题

<details>
<summary><strong>❌ ModuleNotFoundError: No module named 'dayflow'</strong></summary>

**解决方案：**
1. 确保运行了 `setup_dev.bat`
2. 或使用 `run.bat` 启动（已自动设置 PYTHONPATH）
</details>

<details>
<summary><strong>❌ FFmpeg not found</strong></summary>

**解决方案：**
1. 安装 FFmpeg（参见安装步骤）
2. 确认 FFmpeg 已添加到系统 PATH
3. 重启应用
</details>

<details>
<summary><strong>❌ API 调用失败</strong></summary>

**检查清单：**
- ✅ API Key 是否正确
- ✅ 网络连接是否正常
- ✅ API 配额是否充足
- ✅ 设置是否已保存
</details>

<details>
<summary><strong>❌ 录制没有开始</strong></summary>

**排查步骤：**
1. 查看系统托盘图标状态
2. 检查日志：`%LOCALAPPDATA%\Dayflow\logs\dayflow.log`
3. 确认屏幕录制权限
</details>

更多问题请查看 [QUICKSTART.md](QUICKSTART.md)

---

## 🤝 贡献

欢迎贡献！请遵循以下步骤：

1. **Fork** 本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 提交 **Pull Request**

### 贡献指南

- 遵循现有代码风格（使用 Black 格式化）
- 添加必要的测试
- 更新相关文档
- 提交前运行所有测试

---

## 📄 许可证

本项目采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 许可协议进行许可。

**简单来说：**
- ✅ **可以免费使用** - 个人学习、研究、非商业用途
- ✅ **可以修改和分发** - 改进和分享你的修改版本
- ❌ **禁止商业使用** - 不得将本软件用于商业目的或销售
- 🔒 **相同方式共享** - 修改后的作品必须使用相同许可协议

查看 [LICENSE](LICENSE) 文件了解完整许可条款。

---

## 🙏 鸣谢

### 特别感谢

- [Dayflow by JerryZLiu](https://github.com/JerryZLiu/Dayflow) - 本项目的灵感来源，一款优秀的 macOS 时间追踪应用

### 开源项目

感谢以下开源项目的支持：

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI 框架
- [FFmpeg](https://ffmpeg.org/) - 视频处理
- [OpenCV](https://opencv.org/) - 计算机视觉
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI 分析
- [matplotlib](https://matplotlib.org/) - 数据可视化

---

## 📞 联系方式

- 提交 Issue：[GitHub Issues](https://github.com/yourusername/dayflow/issues)
- 讨论区：[GitHub Discussions](https://github.com/yourusername/dayflow/discussions)

---

## 🗺️ 路线图

- [ ] 支持多显示器录制
- [ ] 添加更多 AI 模型支持
- [ ] 导出功能（PDF、Excel 报告）
- [ ] 团队协作功能
- [ ] macOS 和 Linux 支持
- [ ] 浏览器扩展集成

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

Made with ❤️ by Dayflow Team

</div>
