# Dayflow Windows - 快速开始指南

## 🚀 三步启动

### 第一步：设置开发环境（仅首次）

双击运行：
```
setup_dev.bat
```

这个脚本会自动：
1. 创建虚拟环境（如果不存在）
2. 安装所有依赖
3. 以可编辑模式安装 Dayflow

⏱️ 预计耗时：2-3 分钟

---

### 第二步：配置 FFmpeg（可选但推荐）

Dayflow 需要 FFmpeg 来处理视频。

**方式 1: 使用 Chocolatey（推荐）**
```bash
choco install ffmpeg
```

**方式 2: 手动安装**
1. 下载：https://ffmpeg.org/download.html#build-windows
2. 解压到任意目录（如 `C:\ffmpeg`）
3. 将 `bin` 目录添加到系统 PATH
   - 右键"此电脑" → 属性 → 高级系统设置 → 环境变量
   - 在"系统变量"中找到 `Path`，添加 `C:\ffmpeg\bin`

**验证安装：**
```bash
ffmpeg -version
```

---

### 第三步：启动应用

双击运行：
```
run.bat
```

或者在命令行：
```bash
venv\Scripts\python -m dayflow.main
```

---

## ⚙️ 首次配置

应用启动后：

1. 进入 **Settings**（设置）视图
2. 在 "AI Provider Settings" 配置 API 密钥：
   - 选择 **Gemini** 作为 AI Provider
   - 获取 API Key：https://makersuite.google.com/app/apikey
   - 输入 API Key 并点击 **Save Settings**

3. 调整录制设置（可选）：
   - Video Quality：建议选择 **Medium**
   - Keep Recordings：默认 **3 days**

4. 点击 **💾 Save Settings**

---

## 🎬 开始使用

配置完成后，Dayflow 会自动：

1. **开始录制** 📹
   - 每秒捕获 1 帧屏幕
   - 每 15 秒保存一个视频片段
   - 系统锁定/睡眠时自动暂停

2. **AI 分析** 🤖
   - 每 15 分钟自动分析录制内容
   - 识别不同的活动
   - 自动分类和生成摘要
   - 创建延时视频（20x 速度）

3. **查看时间轴** 📊
   - 切换到 **Timeline** 视图
   - 查看今天的活动卡片
   - 点击活动展开详情
   - 播放延时视频回放

---

## 📁 数据存储位置

所有数据存储在：
```
%LOCALAPPDATA%\Dayflow\
├── config.json              # 配置文件
├── data\
│   └── dayflow.db           # SQLite 数据库
├── recordings\
│   └── YYYY-MM-DD\
│       └── chunks\          # 视频片段
└── timelapses\
    └── YYYY-MM-DD\          # 延时视频
```

---

## 🔧 常见问题

### ❌ 问题：ModuleNotFoundError: No module named 'dayflow'

**解决方案：**
1. 确保运行了 `setup_dev.bat`
2. 或者直接运行更新后的 `run.bat`（已自动设置 PYTHONPATH）

---

### ❌ 问题：FFmpeg not found

**现象：** 视频合并和延时功能不工作

**解决方案：**
1. 安装 FFmpeg（见上面"第二步"）
2. 重启应用

---

### ❌ 问题：Gemini API 调用失败

**检查清单：**
1. ✅ API Key 是否正确输入
2. ✅ 是否保存了设置
3. ✅ 网络是否正常
4. ✅ API Key 是否有效（在 Google AI Studio 检查）

---

### ❌ 问题：视频播放失败

**可能原因：**
- PyQt6-WebEngine 未安装
- 视频编码格式不支持

**解决方案：**
```bash
venv\Scripts\pip install PyQt6-WebEngine
```

---

### ❌ 问题：录制没有开始

**检查项：**
1. 查看系统托盘图标状态
2. 检查日志：`%LOCALAPPDATA%\Dayflow\logs\dayflow.log`
3. 确认屏幕录制权限（Windows 设置 → 隐私）

---

## 🎯 系统要求

- **操作系统：** Windows 10 或 Windows 11
- **Python：** 3.10 或更高版本
- **内存：** 建议 4GB 以上
- **磁盘：** 至少 500MB 可用空间（用于录制）
- **网络：** 需要访问 Google Gemini API

---

## 📖 更多文档

- **README.md** - 项目介绍
- **DEVELOPMENT.md** - 完整开发指南
- **PROJECT_SUMMARY.md** - 项目完成总结

---

## 🆘 获取帮助

如遇到其他问题：

1. 查看日志文件：
   ```
   %LOCALAPPDATA%\Dayflow\logs\dayflow.log
   ```

2. 查看 GitHub Issues（如果项目已发布）

3. 检查是否安装了所有依赖：
   ```bash
   venv\Scripts\pip list
   ```

---

## ✨ 快速命令参考

```bash
# 设置环境（首次）
setup_dev.bat

# 启动应用
run.bat

# 或者直接运行
venv\Scripts\python -m dayflow.main

# 查看已安装的包
venv\Scripts\pip list

# 重新安装依赖
venv\Scripts\pip install -r requirements.txt

# 运行测试
venv\Scripts\pytest

# 格式化代码
venv\Scripts\black src/
```

---

## 🎉 享受使用 Dayflow！

Dayflow 会帮你：
- 📹 自动记录每天的工作
- 🤖 智能分析和分类活动
- 📊 可视化时间分配
- 🎬 生成每日精彩回顾视频

让我们开始自动化你的时间轴吧！✨
