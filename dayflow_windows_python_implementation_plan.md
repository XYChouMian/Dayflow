# Dayflow Windows Python 实现计划

## 项目概述

本文档详细分析了 Dayflow Mac 应用的项目构成，并提供了使用 Python 在 Windows 平台上构建功能等效版本的完整实施计划。

---

## 第一部分：Dayflow Mac 应用深度分析

### 1. 项目基本信息

**应用名称**: Dayflow
**平台**: macOS (最低版本 13.0+)
**开发语言**: Swift
**架构模式**: MVVM (Model-View-ViewModel) with SwiftUI
**数据库**: SQLite with GRDB Framework
**构建系统**: Xcode Project

### 2. 核心功能

Dayflow 是一个**自动时间轴生成工具**，其主要功能包括：

#### 2.1 屏幕录制系统
- **录制频率**: 1 FPS (每秒一帧)
- **分块策略**: 以 15 秒为单位的视频片段
- **自动管理**: 在睡眠/锁屏时自动暂停录制
- **多显示器支持**: 监测并适配多显示器环境
- **存储策略**: 自动删除 3 天前的录制数据

#### 2.2 AI 分析引擎
- **分析周期**: 每 15 分钟批量分析一次
- **AI 提供商**:
  - Google Gemini API (云端)
  - Ollama 本地模型 (隐私优先)
- **处理流程**:
  1. 合并 15 秒的视频片段成 15 分钟批次
  2. 使用 AI 转录和分析视频内容
  3. 生成活动卡片和摘要
  4. 创建延时视频 (20倍速)
  5. 存储结果到 SQLite 数据库

#### 2.3 时间轴可视化
- **活动卡片**: 显示每个活动的摘要和分类
- **延时视频**: 为每个活动生成快进视频回放
- **分类管理**: 可自定义的活动类别和颜色编码
- **日期导航**: 浏览历史时间轴数据

#### 2.4 附加功能
- **仪表板**: 生产力指标和趋势分析
- **日志功能**: 反思提示和活动亮点
- **干扰检测**: 识别非任务活动模式
- **导出功能**: 时间轴数据导出选项
- **自动更新**: 通过 Sparkle 框架实现后台更新

### 3. 技术架构

#### 3.1 核心依赖框架

| 框架/库 | 用途 | 说明 |
|--------|------|------|
| **Sparkle** | 自动更新 | macOS 应用更新框架 |
| **GRDB** | 数据库 | Swift SQLite 封装库 |
| **Sentry** | 错误追踪 | 崩溃报告和错误监控 |
| **PostHog** | 数据分析 | 用户行为分析服务 |
| **ScreenCaptureKit** | 屏幕录制 | macOS 原生屏幕捕获 API |
| **AVFoundation** | 视频处理 | 视频编码和操作框架 |

#### 3.2 应用架构组件

**录制管道 (Recording Pipeline)**:
- `ScreenRecorder`: 使用 ScreenCaptureKit 管理屏幕捕获
- `StorageManager`: 处理视频文件存储和数据库操作
- `ActiveDisplayTracker`: 监控多显示器环境的显示变化

**分析管道 (Analysis Pipeline)**:
- `AnalysisManager`: 协调每 15 分钟的批处理
- `LLMService`: 管理 AI 提供商集成 (Gemini/Ollama)
- `VideoProcessingService`: 合并视频片段并生成延时视频

**用户界面组件 (UI Components)**:
- `MainView`: 主时间轴界面和侧边栏导航
- `TimelineActivity`: 活动卡片，包含摘要和视频回放
- `SettingsView`: AI 提供商和偏好设置配置
- **引导流程**: 多步骤设置过程

**数据模型 (Data Models)**:
- `RecordingChunk`: 15 秒视频片段记录
- `TimelineActivity`: AI 生成的活动卡片
- `TimelineCategory`: 用户定义的活动分类
- 使用 GRDB 的 SQLite 数据库架构

#### 3.3 系统集成

**所需权限**:
- 屏幕和系统音频录制权限
- 登录项自动启动权限
- 网络访问权限（用于云端 AI 提供商）

**后台服务**:
- 登录项注册实现自动启动
- 睡眠/唤醒监控用于录制暂停/恢复
- 状态栏集成提供快速访问
- Deep Link 支持 (`dayflow://` URL scheme)

#### 3.4 AI 处理流程

**两种处理模式**:

1. **Gemini (云端)模式**:
   - 直接上传视频进行分析
   - 仅需 2 次 LLM 调用
   - 速度更快，但需要网络连接

2. **本地模型模式**:
   - 逐帧提取和分析
   - 需要 30+ 次 LLM 调用
   - 完全本地处理，保护隐私

**处理步骤**:
1. 将 15 秒片段合并为 15 分钟批次
2. 转录和分析视频内容
3. 生成带摘要的活动卡片
4. 为每个活动创建延时视频
5. 将结果存储到 SQLite 数据库

### 4. 数据存储架构

**数据库表结构**:
- **RecordingChunks**: 存储视频片段元数据
- **TimelineActivities**: 存储 AI 生成的活动记录
- **TimelineCategories**: 存储用户定义的分类
- **Settings**: 存储应用配置和偏好

**文件存储**:
- 视频片段按日期组织存储
- 延时视频单独存储
- 自动清理策略（3 天保留期）

---

## 第二部分：Python Windows 版本实现计划

### 阶段 1: 核心屏幕录制系统 (2-3 周)

#### 1.1 屏幕捕获实现

**技术选型**:
- **主要方案**: `mss` (Multi-Screen Shot) - 快速跨平台截屏
- **备选方案**: `pyautogui` 或 `windows-capture`
- **视频编码**: `opencv-python` + `ffmpeg-python`

**核心功能**:
```python
# 关键组件
class ScreenRecorder:
    - capture_frame(): 1 FPS 帧捕获
    - save_chunk(): 15 秒片段保存为 MP4
    - pause_on_lock(): 监听系统锁屏事件
    - multi_monitor_support(): 检测和切换显示器
```

**实现细节**:
- 使用 `mss.mss()` 以 1 FPS 捕获屏幕
- 使用 `cv2.VideoWriter` 写入 MP4 格式 (H.264 编码)
- 每 15 秒创建一个视频文件
- 使用 `pywin32` 监听系统锁屏/解锁事件
- 使用 `win32api.EnumDisplayMonitors()` 检测多显示器

#### 1.2 存储管理系统

**技术选型**:
- **数据库**: SQLite with `sqlalchemy` ORM
- **文件管理**: 按日期组织的目录结构
- **清理策略**: 定时任务删除旧数据

**数据库架构**:
```python
# SQLAlchemy Models
class RecordingChunk(Base):
    id: Integer (Primary Key)
    start_time: DateTime
    end_time: DateTime
    file_path: String
    display_id: Integer
    file_size: Integer

class TimelineActivity(Base):
    id: Integer (Primary Key)
    start_time: DateTime
    end_time: DateTime
    title: String
    summary: Text
    category_id: Integer (Foreign Key)
    timelapse_path: String

class TimelineCategory(Base):
    id: Integer (Primary Key)
    name: String
    color: String
    icon: String
```

**文件组织结构**:
```
recordings/
├── 2025-11-03/
│   ├── chunks/
│   │   ├── 14:00:00.mp4
│   │   ├── 14:00:15.mp4
│   │   └── ...
│   └── timelapses/
│       ├── activity_001.mp4
│       └── ...
└── 2025-11-02/
    └── ...
```

#### 1.3 电源管理

**实现要点**:
- 使用 `psutil` 监控系统状态
- 使用 `pywin32` 监听 Windows 电源事件
- 自动暂停/恢复录制功能

```python
import win32api
import win32con
import win32gui

class PowerManager:
    def register_power_events():
        # 监听 WM_POWERBROADCAST 消息
        # PBT_APMSUSPEND: 系统睡眠
        # PBT_APMRESUMEAUTOMATIC: 系统唤醒
```

### 阶段 2: AI 分析集成 (2-3 周)

#### 2.1 AI 提供商支持

**支持的 AI 服务**:

1. **OpenAI GPT-4 Vision** (云端):
   - 使用 `openai` Python SDK
   - 上传视频或帧进行分析
   - 高质量分析结果

2. **Ollama 本地模型** (本地):
   - 使用 `requests` 调用本地 Ollama API
   - 支持 LLaVA、BakLLaVA 等视觉模型
   - 完全离线处理

3. **Google Gemini** (云端):
   - 使用 `google-generativeai` SDK
   - 视频直接分析能力
   - 与原 Mac 版保持一致

**LLM 服务抽象层**:
```python
from abc import ABC, abstractmethod

class LLMService(ABC):
    @abstractmethod
    def analyze_video(self, video_path: str) -> dict:
        pass

    @abstractmethod
    def analyze_frames(self, frames: list) -> dict:
        pass

class GeminiService(LLMService):
    # 实现 Gemini API 调用

class OllamaService(LLMService):
    # 实现 Ollama 本地调用

class OpenAIService(LLMService):
    # 实现 OpenAI GPT-4V 调用
```

#### 2.2 视频处理管道

**核心功能**:
```python
class VideoProcessor:
    def combine_chunks(chunk_paths: list) -> str:
        """合并 15 秒片段为 15 分钟视频"""
        # 使用 ffmpeg-python 合并视频

    def extract_frames(video_path: str, fps: float = 0.1) -> list:
        """提取关键帧用于本地模型分析"""
        # 使用 opencv 提取帧

    def create_timelapse(video_path: str, speedup: int = 20) -> str:
        """生成延时视频"""
        # 使用 ffmpeg 加速视频
```

**实现细节**:
- 使用 `ffmpeg-python` 的 concat demuxer 合并视频
- 使用 `cv2.VideoCapture` 提取帧
- 使用 `ffmpeg` 的 `setpts` 过滤器创建延时效果

#### 2.3 分析管理器

**批量处理逻辑**:
```python
class AnalysisManager:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.interval = 15  # 分钟

    def schedule_analysis(self):
        """每 15 分钟运行一次分析"""

    def process_batch(self, start_time: datetime, end_time: datetime):
        """处理一个时间批次"""
        # 1. 获取该时段的所有 chunks
        # 2. 合并为一个视频
        # 3. 调用 LLM 分析
        # 4. 解析生成的活动
        # 5. 创建延时视频
        # 6. 存储到数据库
```

**滑动窗口分析**:
- 使用 1 小时的上下文窗口
- 更准确的活动分割
- 处理跨时段的长时间活动

### 阶段 3: 用户界面开发 (3-4 周)

#### 3.1 GUI 框架选型

**推荐方案**: **PyQt6**

**优势**:
- 原生外观和性能
- 丰富的组件库
- 良好的视频播放支持 (QMediaPlayer)
- 成熟的开发生态

**备选方案**: **CustomTkinter** (更轻量但功能有限)

#### 3.2 主界面结构

**布局设计**:
```
┌─────────────────────────────────────────────┐
│  Dayflow - Windows                     [_][□][X]│
├──────────┬──────────────────────────────────┤
│          │  Timeline - November 3, 2025   │
│ Timeline │  [<] [>]                        │
│          ├──────────────────────────────────┤
│ Dashboard│ ┌─────────────────────────────┐ │
│          │ │ 14:00 - 14:45              │ │
│ Settings │ │ Code Review and Testing    │ │
│          │ │ [Video Preview]            │ │
│ Journal  │ │ 📝 Productivity            │ │
│          │ └─────────────────────────────┘ │
│          │ ┌─────────────────────────────┐ │
│          │ │ 14:45 - 15:20              │ │
│          │ │ Meeting with Team          │ │
│          │ │ [Video Preview]            │ │
│          │ │ 💼 Work                     │ │
│          │ └─────────────────────────────┘ │
└──────────┴──────────────────────────────────┘
```

**组件实现**:
```python
class MainWindow(QMainWindow):
    def __init__(self):
        self.sidebar = Sidebar()
        self.timeline_view = TimelineView()
        self.dashboard_view = DashboardView()
        self.settings_view = SettingsView()

class TimelineView(QWidget):
    def __init__(self):
        self.date_navigator = DateNavigator()
        self.activity_list = ActivityListWidget()

class ActivityCard(QWidget):
    """单个活动卡片"""
    - title_label: QLabel
    - summary_text: QTextEdit
    - video_player: QMediaPlayer
    - category_badge: CategoryBadge
```

#### 3.3 关键 UI 组件

**活动卡片组件**:
- 时间范围显示
- 活动标题和摘要
- 嵌入式视频播放器
- 分类标签和颜色
- 展开/折叠功能

**视频播放器**:
```python
class VideoPlayer(QWidget):
    def __init__(self):
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.play_button = QPushButton("▶")
        self.progress_slider = QSlider(Qt.Horizontal)
```

**日期导航器**:
```python
class DateNavigator(QWidget):
    def __init__(self):
        self.prev_button = QPushButton("<")
        self.date_label = QLabel()
        self.next_button = QPushButton(">")
        self.calendar_button = QPushButton("📅")
```

#### 3.4 设置界面

**配置选项**:
- AI 提供商选择 (Gemini/Ollama/OpenAI)
- API 密钥配置
- 录制偏好设置
  - 录制质量
  - 保留天数
  - 排除应用程序
- 分类管理
  - 创建/编辑/删除分类
  - 颜色选择器
- 隐私设置
  - 本地处理优先
  - 数据保留策略

### 阶段 4: 高级功能实现 (2-3 周)

#### 4.1 仪表板功能

**显示内容**:
- **今日统计**:
  - 总工作时间
  - 各分类时间分布
  - 生产力评分

- **趋势图表**:
  - 每周活动时间对比
  - 分类时间趋势
  - 干扰检测统计

**技术实现**:
```python
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

class DashboardView(QWidget):
    def __init__(self):
        self.stats_widget = StatsWidget()
        self.chart_widget = ChartWidget()

    def generate_productivity_chart(self):
        """使用 matplotlib 生成图表"""
```

#### 4.2 日志功能

**核心特性**:
- 每日反思提示
- 活动亮点自动提取
- AI 生成的日志问题
- Markdown 编辑器

```python
class JournalView(QWidget):
    def __init__(self):
        self.date_selector = QDateEdit()
        self.editor = MarkdownEditor()
        self.highlights = HighlightsPanel()

    def generate_reflection_prompts(self, date: datetime):
        """基于当天活动生成反思问题"""
```

#### 4.3 系统集成

**Windows 启动项**:
```python
import winreg

class StartupManager:
    def add_to_startup():
        """添加到 Windows 启动项"""
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_WRITE
        )
        winreg.SetValueEx(key, "Dayflow", 0, winreg.REG_SZ, exe_path)
```

**系统托盘**:
```python
class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self):
        self.menu = QMenu()
        self.menu.addAction("显示主窗口")
        self.menu.addAction("暂停录制")
        self.menu.addAction("今日统计")
        self.menu.addAction("退出")
```

**通知系统**:
```python
from plyer import notification

def show_notification(title: str, message: str):
    """显示 Windows 通知"""
    notification.notify(
        title=title,
        message=message,
        app_icon='icon.ico',
        timeout=5
    )
```

#### 4.4 自动更新系统

**实现方案**:
- 使用 GitHub Releases 托管更新
- 版本检查 API
- 自动下载和安装

```python
class UpdateManager:
    def check_for_updates(self) -> dict:
        """检查 GitHub Releases"""

    def download_update(self, url: str):
        """下载更新包"""

    def install_update(self, installer_path: str):
        """安装更新并重启应用"""
```

### 阶段 5: 优化和完善 (1-2 周)

#### 5.1 性能优化

**多线程处理**:
```python
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

class BackgroundWorker:
    def __init__(self):
        self.recording_thread = Thread(target=self.recording_loop)
        self.analysis_thread = Thread(target=self.analysis_loop)
        self.executor = ThreadPoolExecutor(max_workers=4)
```

**内存管理**:
- 视频流处理避免一次性加载
- 及时释放不用的帧数据
- 使用生成器处理大文件

**数据库优化**:
```sql
-- 添加索引
CREATE INDEX idx_chunks_start_time ON recording_chunks(start_time);
CREATE INDEX idx_activities_start_time ON timeline_activities(start_time);
CREATE INDEX idx_activities_category ON timeline_activities(category_id);
```

#### 5.2 错误处理和日志

**全局异常处理**:
```python
import logging
import traceback

logging.basicConfig(
    filename='dayflow.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def exception_handler(exc_type, exc_value, exc_traceback):
    """全局异常处理器"""
    logging.error("Uncaught exception",
                  exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = exception_handler
```

**错误恢复机制**:
- 录制中断自动重启
- 分析失败重试逻辑
- 数据库损坏恢复

#### 5.3 隐私和安全

**API 密钥安全存储**:
```python
import keyring

class SecureStorage:
    def save_api_key(self, service: str, key: str):
        """使用 Windows 凭据管理器存储"""
        keyring.set_password("Dayflow", service, key)

    def get_api_key(self, service: str) -> str:
        return keyring.get_password("Dayflow", service)
```

**本地处理优先**:
- 默认使用 Ollama 本地模型
- 仅在用户明确选择时使用云端服务
- 数据不上传第三方（除非用户选择云端 AI）

**数据加密**:
```python
from cryptography.fernet import Fernet

class DataEncryption:
    def encrypt_sensitive_data(self, data: str) -> bytes:
        """加密敏感数据"""

    def decrypt_sensitive_data(self, encrypted: bytes) -> str:
        """解密数据"""
```

---

## 第三部分：技术实现细节

### 1. Python 库和依赖清单

#### 核心依赖
```
# requirements.txt

# 屏幕录制和图像处理
mss==9.0.1                    # 快速屏幕捕获
opencv-python==4.8.1          # 图像和视频处理
Pillow==10.1.0                # 图像处理
ffmpeg-python==0.2.0          # FFmpeg Python 绑定

# 数据库
sqlalchemy==2.0.23            # ORM 框架
alembic==1.12.1               # 数据库迁移

# AI 集成
openai==1.3.5                 # OpenAI API
google-generativeai==0.3.1    # Google Gemini API
requests==2.31.0              # HTTP 客户端 (Ollama)

# GUI 框架
PyQt6==6.6.0                  # Qt 6 绑定
PyQt6-WebEngine==6.6.0        # Web 引擎组件
matplotlib==3.8.2             # 图表生成

# 系统集成
pywin32==306                  # Windows API
psutil==5.9.6                 # 系统监控
plyer==2.1.0                  # 跨平台通知

# 安全
cryptography==41.0.7          # 加密
keyring==24.3.0               # 密钥存储

# 工具
python-dateutil==2.8.2        # 日期处理
apscheduler==3.10.4           # 任务调度
```

### 2. 项目结构

```
dayflow-windows/
├── src/
│   ├── __init__.py
│   ├── main.py                      # 应用入口
│   ├── core/
│   │   ├── __init__.py
│   │   ├── recorder.py              # 屏幕录制器
│   │   ├── storage.py               # 存储管理
│   │   ├── video_processor.py      # 视频处理
│   │   └── power_manager.py        # 电源管理
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── analysis_manager.py     # 分析管理器
│   │   ├── llm_service.py          # LLM 服务抽象
│   │   ├── gemini_service.py       # Gemini 实现
│   │   ├── ollama_service.py       # Ollama 实现
│   │   └── openai_service.py       # OpenAI 实现
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py             # 数据库配置
│   │   ├── recording_chunk.py      # 录制片段模型
│   │   ├── timeline_activity.py    # 活动模型
│   │   └── category.py             # 分类模型
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py          # 主窗口
│   │   ├── timeline_view.py        # 时间轴视图
│   │   ├── dashboard_view.py       # 仪表板视图
│   │   ├── journal_view.py         # 日志视图
│   │   ├── settings_view.py        # 设置视图
│   │   ├── widgets/
│   │   │   ├── activity_card.py    # 活动卡片
│   │   │   ├── video_player.py     # 视频播放器
│   │   │   ├── date_navigator.py   # 日期导航
│   │   │   └── category_badge.py   # 分类标签
│   │   └── styles/
│   │       └── theme.qss           # Qt 样式表
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py               # 配置管理
│   │   ├── logger.py               # 日志工具
│   │   ├── security.py             # 安全工具
│   │   └── notifications.py        # 通知工具
│   └── services/
│       ├── __init__.py
│       ├── startup_manager.py      # 启动项管理
│       ├── update_manager.py       # 更新管理
│       └── system_tray.py          # 系统托盘
├── resources/
│   ├── icons/
│   │   ├── app_icon.ico
│   │   └── tray_icon.ico
│   └── config/
│       └── default_settings.json
├── tests/
│   ├── __init__.py
│   ├── test_recorder.py
│   ├── test_analysis.py
│   └── test_storage.py
├── docs/
│   └── API.md
├── scripts/
│   ├── build.py                    # 打包脚本
│   └── setup_dev.py                # 开发环境设置
├── requirements.txt
├── requirements-dev.txt
├── setup.py
├── README.md
└── LICENSE
```

### 3. 数据库架构详细设计

```sql
-- 录制片段表
CREATE TABLE recording_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    file_path TEXT NOT NULL,
    display_id INTEGER DEFAULT 0,
    file_size INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(start_time, display_id)
);

-- 时间轴活动表
CREATE TABLE timeline_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    category_id INTEGER,
    timelapse_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES timeline_categories(id)
);

-- 分类表
CREATE TABLE timeline_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL,
    icon TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 设置表
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 日志条目表
CREATE TABLE journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    content TEXT,
    highlights TEXT,  -- JSON 格式的活动亮点
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_chunks_start_time ON recording_chunks(start_time);
CREATE INDEX idx_chunks_display ON recording_chunks(display_id);
CREATE INDEX idx_activities_start_time ON timeline_activities(start_time);
CREATE INDEX idx_activities_category ON timeline_activities(category_id);
CREATE INDEX idx_journal_date ON journal_entries(date);
```

### 4. API 集成示例

#### 4.1 Gemini API 集成
```python
import google.generativeai as genai

class GeminiService(LLMService):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')

    def analyze_video(self, video_path: str) -> dict:
        """分析视频并生成活动摘要"""
        video_file = genai.upload_file(video_path)

        prompt = """
        Analyze this screen recording and identify distinct activities.
        For each activity, provide:
        1. Start and end time
        2. A brief title (max 50 chars)
        3. A summary of what was being done
        4. Suggested category (Work, Meeting, Break, etc.)

        Format as JSON array.
        """

        response = self.model.generate_content([prompt, video_file])
        return self._parse_response(response.text)
```

#### 4.2 Ollama 本地模型集成
```python
import requests
import base64

class OllamaService(LLMService):
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "llava"  # 或 bakllava

    def analyze_frames(self, frames: list) -> dict:
        """分析提取的帧"""
        activities = []

        for frame in frames:
            # 将帧转为 base64
            _, buffer = cv2.imencode('.jpg', frame)
            image_b64 = base64.b64encode(buffer).decode('utf-8')

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": "What is happening in this screenshot?",
                    "images": [image_b64]
                }
            )

            activities.append(response.json())

        return self._combine_activities(activities)
```

#### 4.3 OpenAI GPT-4V 集成
```python
from openai import OpenAI
import base64

class OpenAIService(LLMService):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def analyze_frames(self, frames: list) -> dict:
        """使用 GPT-4V 分析帧"""
        # 准备图片
        images = []
        for frame in frames[:10]:  # 限制帧数以控制成本
            _, buffer = cv2.imencode('.jpg', frame)
            b64 = base64.b64encode(buffer).decode('utf-8')
            images.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}"
                }
            })

        response = self.client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze these screenshots and describe the activities."
                        },
                        *images
                    ]
                }
            ],
            max_tokens=1000
        )

        return self._parse_response(response.choices[0].message.content)
```

### 5. 开发时间线和里程碑

#### 第 1-3 周：屏幕录制系统
- **Week 1**:
  - ✅ 基础屏幕捕获实现
  - ✅ 视频编码和存储
  - ✅ 数据库架构设计
- **Week 2**:
  - ✅ 多显示器支持
  - ✅ 电源管理集成
  - ✅ 存储清理策略
- **Week 3**:
  - ✅ 性能优化
  - ✅ 单元测试
  - ✅ Bug 修复

**里程碑 1**: 稳定的录制系统，能够持续捕获屏幕并存储

#### 第 4-6 周：AI 分析集成
- **Week 4**:
  - ✅ LLM 服务抽象层
  - ✅ Gemini API 集成
  - ✅ 视频处理工具
- **Week 5**:
  - ✅ Ollama 本地模型集成
  - ✅ OpenAI GPT-4V 集成
  - ✅ 分析管理器实现
- **Week 6**:
  - ✅ 延时视频生成
  - ✅ 批量处理优化
  - ✅ 错误处理和重试

**里程碑 2**: 完整的 AI 分析管道，生成准确的活动卡片

#### 第 7-10 周：用户界面开发
- **Week 7**:
  - ✅ 主窗口框架
  - ✅ 侧边栏导航
  - ✅ 时间轴视图基础
- **Week 8**:
  - ✅ 活动卡片组件
  - ✅ 视频播放器集成
  - ✅ 日期导航
- **Week 9**:
  - ✅ 设置界面
  - ✅ 分类管理
  - ✅ UI 美化和主题
- **Week 10**:
  - ✅ 仪表板视图
  - ✅ 图表生成
  - ✅ 响应式布局

**里程碑 3**: 功能完整的用户界面，良好的用户体验

#### 第 11-13 周：高级功能
- **Week 11**:
  - ✅ 日志功能
  - ✅ AI 生成的反思提示
  - ✅ Markdown 编辑器
- **Week 12**:
  - ✅ 系统托盘集成
  - ✅ 启动项管理
  - ✅ 通知系统
- **Week 13**:
  - ✅ 自动更新系统
  - ✅ 导出功能
  - ✅ 集成测试

**里程碑 4**: 所有高级功能实现并集成

#### 第 14-15 周：优化和发布
- **Week 14**:
  - ✅ 性能优化
  - ✅ 内存泄漏修复
  - ✅ 数据库优化
  - ✅ 错误日志完善
- **Week 15**:
  - ✅ 安全审计
  - ✅ 用户文档
  - ✅ 安装程序打包
  - ✅ Beta 测试

**里程碑 5**: 生产就绪的应用，准备发布

### 6. 打包和分发

#### 使用 PyInstaller 打包
```python
# build.py
import PyInstaller.__main__

PyInstaller.__main__.run([
    'src/main.py',
    '--name=Dayflow',
    '--windowed',
    '--onefile',
    '--icon=resources/icons/app_icon.ico',
    '--add-data=resources;resources',
    '--hidden-import=PyQt6',
    '--hidden-import=cv2',
    '--clean',
])
```

#### 创建安装程序 (使用 Inno Setup)
```iss
; setup.iss
[Setup]
AppName=Dayflow for Windows
AppVersion=1.0.0
DefaultDirName={pf}\Dayflow
DefaultGroupName=Dayflow
OutputDir=dist
OutputBaseFilename=DayflowSetup
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\Dayflow.exe"; DestDir: "{app}"
Source: "resources\*"; DestDir: "{app}\resources"; Flags: recursesubdirs

[Icons]
Name: "{group}\Dayflow"; Filename: "{app}\Dayflow.exe"
Name: "{commondesktop}\Dayflow"; Filename: "{app}\Dayflow.exe"

[Run]
Filename: "{app}\Dayflow.exe"; Description: "Launch Dayflow"; Flags: nowait postinstall skipifsilent
```

---

## 第四部分：关键挑战和解决方案

### 1. 性能挑战

**挑战**: 持续 1 FPS 录制可能消耗大量资源

**解决方案**:
- 使用高效的 `mss` 库而非 `pyautogui`
- 使用硬件加速的视频编码 (H.264)
- 在后台线程中进行编码
- 实现帧缓冲队列

### 2. AI 成本控制

**挑战**: 云端 AI 分析成本可能很高

**解决方案**:
- 默认使用免费的 Ollama 本地模型
- 提供云端 AI 作为可选项
- 实现智能采样减少 API 调用
- 缓存分析结果

### 3. 跨显示器录制

**挑战**: Windows 多显示器环境复杂

**解决方案**:
- 使用 `mss` 的多显示器 API
- 监听显示器变化事件
- 为每个显示器单独录制
- 在分析时合并显示器数据

### 4. 隐私保护

**挑战**: 屏幕录制涉及敏感信息

**解决方案**:
- 优先使用本地 AI 模型
- 提供应用/窗口排除列表
- 短期数据保留（3 天）
- 完全本地存储
- 开源代码供审计

### 5. 视频存储空间

**挑战**: 长期录制占用大量磁盘空间

**解决方案**:
- 1 FPS 低帧率录制
- 高效的 H.264 编码
- 自动清理旧数据
- 可配置的保留期
- 压缩延时视频

---

## 第五部分：测试策略

### 1. 单元测试
```python
# tests/test_recorder.py
import unittest
from src.core.recorder import ScreenRecorder

class TestScreenRecorder(unittest.TestCase):
    def test_capture_frame(self):
        recorder = ScreenRecorder()
        frame = recorder.capture_frame()
        self.assertIsNotNone(frame)

    def test_save_chunk(self):
        recorder = ScreenRecorder()
        path = recorder.save_chunk(frames)
        self.assertTrue(os.path.exists(path))
```

### 2. 集成测试
- 端到端录制到分析流程
- 多显示器场景测试
- AI 提供商切换测试
- 数据库迁移测试

### 3. 性能测试
- 长时间运行稳定性测试
- 内存泄漏检测
- CPU/GPU 使用率监控
- 磁盘 I/O 性能测试

### 4. 用户验收测试
- 界面可用性测试
- 功能完整性验证
- 不同分辨率/DPI 测试
- Windows 10/11 兼容性

---

## 第六部分：未来扩展功能

### 1. 高级分析功能
- 应用使用时间统计
- 网站访问追踪
- 键盘/鼠标活动热力图
- 焦点应用识别

### 2. 团队功能
- 团队时间轴共享（可选）
- 协作活动识别
- 团队生产力报告
- 隐私保护的协作分析

### 3. 集成功能
- 日历集成（Outlook/Google Calendar）
- 项目管理工具集成（Jira/Trello）
- 时间追踪工具同步（Toggl/RescueTime）
- Slack 通知集成

### 4. 移动应用
- Android/iOS 配套应用
- 跨设备时间轴同步
- 移动端查看和分析
- 推送通知

---

## 总结

本实施计划为使用 Python 在 Windows 平台上重建 Dayflow 提供了全面的路线图。通过分阶段开发，从核心录制系统到高级分析功能，再到精美的用户界面，我们可以创建一个功能完整、性能优异的 Windows 原生应用。

**关键优势**:
- ✅ 完全使用 Python 生态系统，易于开发和维护
- ✅ 支持多种 AI 提供商，灵活性高
- ✅ 本地优先处理，保护用户隐私
- ✅ 现代化的 PyQt6 界面，良好的用户体验
- ✅ 开源友好，便于社区贡献

**预计投入**:
- **开发时间**: 10-15 周（单人全职）
- **成本**: 主要为 AI API 调用成本（可选）
- **维护**: 持续的 bug 修复和功能更新

该项目将为 Windows 用户带来与 Mac 版 Dayflow 相同的强大自动时间轴和生产力跟踪体验！
