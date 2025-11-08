# FFmpeg 安装指南

Dayflow 需要 FFmpeg 来处理视频。这里提供了多种安装方法，选择最适合你的一种：

---

## ✅ 方法 1：一键自动安装（推荐，无需管理员）

**双击运行：**
```
install_ffmpeg.bat
```

这个脚本会：
1. ✅ 自动下载 FFmpeg
2. ✅ 解压到项目的 `tools/` 目录
3. ✅ 自动添加到用户 PATH（无需管理员权限）
4. ✅ 验证安装

⏱️ 耗时：约 2-3 分钟（取决于网速）

**运行后**：
- 重启命令行窗口
- 运行 `ffmpeg -version` 验证

---

## ✅ 方法 2：使用 Chocolatey（需要管理员）

1. **以管理员身份打开 PowerShell**：
   - 按 `Win + X`
   - 选择 "Windows PowerShell (管理员)"

2. **运行命令**：
   ```powershell
   choco install ffmpeg -y
   ```

3. **验证安装**：
   ```powershell
   ffmpeg -version
   ```

---

## ✅ 方法 3：使用 Winget（Windows 11 自带）

**打开 PowerShell 或 CMD**：
```bash
winget install ffmpeg
```

---

## ✅ 方法 4：手动下载安装

### 步骤 1：下载 FFmpeg

访问官网下载页面：
**https://ffmpeg.org/download.html#build-windows**

或直接下载：
**https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip**

### 步骤 2：解压

将下载的 `.zip` 文件解压到任意位置，例如：
```
C:\ffmpeg\
```

解压后的目录结构：
```
C:\ffmpeg\
├── bin\
│   ├── ffmpeg.exe
│   ├── ffplay.exe
│   └── ffprobe.exe
├── doc\
└── presets\
```

### 步骤 3：添加到 PATH

#### 方式 A：通过系统设置（推荐）

1. 右键点击"此电脑" → "属性"
2. 点击"高级系统设置"
3. 点击"环境变量"
4. 在"用户变量"中找到 `Path`，双击编辑
5. 点击"新建"，添加：`C:\ffmpeg\bin`
6. 点击"确定"保存所有窗口

#### 方式 B：使用命令行（快速）

**打开 CMD 或 PowerShell**：
```cmd
setx PATH "%PATH%;C:\ffmpeg\bin"
```

⚠️ **重要**：添加 PATH 后，需要**重启命令行窗口**才能生效！

### 步骤 4：验证安装

**打开新的命令行窗口**，运行：
```bash
ffmpeg -version
```

应该看到类似输出：
```
ffmpeg version 6.0 Copyright (c) 2000-2023 the FFmpeg developers
built with gcc 12.2.0 (Rev10, Built by MSYS2 project)
...
```

---

## 🔍 验证安装成功

无论使用哪种方法，安装后都应该验证：

```bash
# 查看版本信息
ffmpeg -version

# 查看 FFmpeg 位置
where ffmpeg
```

**预期输出**：
```
C:\ffmpeg\bin\ffmpeg.exe
# 或
C:\ProgramData\chocolatey\bin\ffmpeg.exe
# 或其他路径
```

---

## ❌ 常见问题

### 问题 1：`ffmpeg` 不是内部或外部命令

**原因**：FFmpeg 未添加到 PATH，或命令行窗口未重启

**解决方案**：
1. 确认已添加到 PATH
2. **关闭并重新打开**命令行窗口
3. 重新运行 `ffmpeg -version`

---

### 问题 2：权限被拒绝

**原因**：文件被占用或权限不足

**解决方案**：
1. 关闭所有使用 FFmpeg 的程序
2. 以管理员身份运行命令行
3. 或使用方法 1（无需管理员）

---

### 问题 3：下载速度慢

**解决方案**：
1. 使用方法 1 的自动安装脚本
2. 或使用国内镜像：
   - https://mirrors.tuna.tsinghua.edu.cn/ffmpeg/
   - https://npm.taobao.org/mirrors/ffmpeg/

---

## 📦 Dayflow 使用 FFmpeg 的功能

FFmpeg 在 Dayflow 中用于：

- ✅ **合并视频片段** - 将 15 秒的片段合并成 15 分钟批次
- ✅ **生成延时视频** - 创建 20x 速度的回放
- ✅ **提取视频帧** - 用于 AI 分析
- ✅ **视频裁剪** - 精确提取时间段

---

## 💡 推荐方案

| 方案 | 速度 | 难度 | 是否需要管理员 | 推荐度 |
|-----|------|------|---------------|--------|
| 方法 1 (自动脚本) | ⭐⭐⭐ | ⭐ | ❌ | ⭐⭐⭐⭐⭐ |
| 方法 2 (Chocolatey) | ⭐⭐⭐⭐ | ⭐⭐ | ✅ | ⭐⭐⭐⭐ |
| 方法 3 (Winget) | ⭐⭐⭐⭐ | ⭐ | ❌ | ⭐⭐⭐⭐ |
| 方法 4 (手动) | ⭐⭐ | ⭐⭐⭐ | ❌ | ⭐⭐⭐ |

**建议**：
- 💻 **不想折腾**：使用方法 1（一键安装）
- 🚀 **有管理员权限**：使用方法 2（Chocolatey）
- 🆕 **Windows 11 用户**：使用方法 3（Winget）
- 🔧 **喜欢手动控制**：使用方法 4（手动安装）

---

## ✅ 安装完成后

1. **重启命令行窗口**（重要！）
2. 运行 `ffmpeg -version` 验证
3. 双击 `run.bat` 启动 Dayflow
4. 享受自动化的时间轴记录！🎉

---

## 📞 需要帮助？

如果遇到问题：

1. 检查本文档的"常见问题"部分
2. 查看 Dayflow 日志：`%LOCALAPPDATA%\Dayflow\logs\dayflow.log`
3. 确认 FFmpeg 版本 >= 4.0

---

## 📄 相关文档

- **QUICKSTART.md** - Dayflow 快速开始指南
- **README.md** - 项目介绍
- **DEVELOPMENT.md** - 开发文档
