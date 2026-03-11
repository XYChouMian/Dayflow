<div align="center">

# ⏱️ Dayflow for Windows

**Intelligent Time Tracking & Productivity Analysis Tool**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-green?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)

*Silent Background Recording → AI Analysis → Visual Timeline*

[![Download](https://img.shields.io/badge/⬇️_Download-EXE-brightgreen?style=for-the-badge)](https://github.com/SeiShonagon520/Dayflow/releases)

[中文](README.md) | **English**

</div>

---

## 🎯 What is Dayflow?

**Dayflow** is an AI-powered intelligent time tracking tool. It silently records your screen in the background, uses vision AI to automatically identify what you're doing, and generates an intuitive timeline to help you understand where your time goes every day.

### 💡 Why Do You Need It?

- **Don't know where your time went?** → Dayflow auto-records, no manual tracking needed
- **Want to boost productivity?** → AI analyzes your work patterns, identifies distractions
- **Need a work log?** → Auto-generates daily activity reports
- **Remote work attendance?** → Objectively records work hours and content

### 🏆 Key Advantages

| Advantage | Description |
|-----------|-------------|
| **Zero Effort** | Set and forget, AI fully automates activity recognition |
| **Ultra Low Power** | 1 FPS recording + smart compression, < 1% CPU usage |
| **Privacy First** | Local data storage, videos auto-deleted after analysis |
| **Smart Categories** | AI auto-identifies: Work/Study/Entertainment/Social/Rest |
| **Productivity Score** | Efficiency rating for each activity, quantify your focus |

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎥 **Low-Power Recording** | 1 FPS ultra-low resource usage, runs silently in background |
| 🪟 **Window Tracking** | Uses Windows API to capture real app names and window titles |
| 🤖 **AI-Powered Analysis** | Vision LLM identifies screen activities and auto-categorizes |
| 📊 **Timeline Visualization** | Intuitive daily time allocation view at a glance |
| 💡 **Productivity Insights** | AI-driven efficiency assessment and improvement suggestions |
| 🔒 **Privacy First** | Local data storage, auto-cleanup after analysis |

### 🆕 Latest Features

| Feature | Description |
|---------|-------------|
| 🪟 **Window Tracking** | Auto-capture real app names via Windows API for more accurate AI recognition |
| 📊 **Web Dashboard** | Export beautiful HTML reports with interactive charts, shareable |
| 📧 **Email Reports** | Auto-send productivity reports with customizable send times |
| 📋 **Deep Analysis Report** | Professional behavior analysis, bottleneck detection, improvement strategies |
| 🤖 **AI Comments** | AI-generated personalized daily summary with friendly encouragement |
| 🔄 **Auto Update** | Check for updates, background download, one-click install |
| 🚀 **Auto Start** | Launch on system startup, minimize to tray automatically |
| 🪟 **Custom Title Bar** | VS Code style, built-in log viewer, minimize to tray |
| 📊 **Statistics Panel** | New stats page with time distribution and productivity trends |
| 📅 **Date Navigation** | View history with previous/next day and quick "Today" buttons |
| 📥 **CSV Export** | One-click export activity data to CSV for analysis |
| ⏸️ **Pause Recording** | Pause when handling private content, resume when done |
| 🎨 **Theme Switching** | IDE-style dark/light themes with auto-saved preferences |
| ⚙️ **Configurable Settings** | Customize email times, sample frames, API timeout, and more |
| 📦 **EXE Packaging** | Build standalone executable, no Python required |

### 📋 Changelog

#### v1.5.2 (2026-03)

**📊 Statistics Page Redesign**
- Brand new dashboard style with refined aesthetics
- Top metric cards: Total duration, average efficiency, deep work count, activity count
- Dual-column grid layout: Left charts + Right data panels
- Donut chart: Category time distribution with hover interaction
- Line chart upgrade: Gradient fill + Bezier curve smoothing
- Bar chart upgrade: Gradient colors + Background track
- Heatmap refined: More compact hourly efficiency display
- Week comparison: This week vs Last week data comparison
- Card shadow effects: More layered visual experience

**✏️ Card Editing Feature**
- Right-click menu to edit/delete activity cards
- Editable fields: Category, title, summary, efficiency score
- Click card to enter edit mode directly

#### v1.5.0 (2025-12)

**🪟 Window Tracking Enhancement**
- New Windows API window tracking, auto-captures real app names and window titles
- AI analysis combines window info for more accurate recognition

**🎨 UI Improvements**
- Activity cards now show left-side efficiency indicator (green/orange/gray)
- Deep work badge: 🔥 icon for activities 60+ minutes
- Sidebar selected state shows left blue indicator bar
- Recording status displays real-time duration (HH:MM:SS format)
- System tray tooltip shows recording status
- Empty state page with guide icon and text
- Page title typography optimization (28px/700)
- Settings page card spacing increased

**🤖 AI Prompt Optimization**
- Simplified transcription prompts, reduced redundant output
- Better utilization of window title info for recognition
- Optimized card generation prompts for better categorization
- Email comments more natural, less AI-like

**🔧 Data Processing Improvements**
- Window record time alignment optimization
- Batch boundary continuity handling
- Email merge logic optimization (5-minute gap threshold)

---

## 🖥️ UI Preview

### Timeline Page

![Dayflow Timeline](assets/Dayflow_index.png)

*Timeline: Displays daily activity cards with time range, app, summary, and productivity score*

### Statistics Page

![Dayflow Statistics](assets/Dayflow_Statistics.png)

*Statistics: Dashboard-style design with top metric cards + dual-column layout, including donut chart, trend chart, heatmap, week comparison, and more*

Statistics page features:

| Feature | Description |
|---------|-------------|
| 📊 **Metric Cards** | Total duration, avg efficiency, deep work count, activities with week comparison |
| 🍩 **Donut Chart** | Category time distribution visualization with hover details |
| 📈 **Trend Chart** | Productivity trend line chart with gradient fill + smooth curves |
| 📊 **Bar Chart** | Daily time distribution with stacked categories |
| 🔥 **Heatmap** | 24-hour efficiency distribution, quickly identify peak hours |
| ⚖️ **Week Compare** | This week vs Last week data comparison, spot trends |
| 🎯 **Daily Goal** | Set daily goals and track completion progress |
| 📱 **App Ranking** | Most used apps/websites usage time leaderboard |

### 📊 Web Dashboard

#### Date Selection

![Dashboard Date Selection](assets/Dayflow_Dashboard_Dialog.png)

*Date Range Selection: Supports Today, Yesterday, This Week, Last Week, This Month, Custom Range*

#### Dashboard Report

![Web Dashboard](assets/Dayflow_Dashboard_Report.png)

*Web Dashboard: Beautiful HTML report with interactive charts, viewable in browser or shareable*

The Web Dashboard feature lets you export your productivity data as a beautiful HTML report:

| Feature | Description |
|---------|-------------|
| 📈 **Overview Cards** | Total duration, average efficiency, deep work time, activity count |
| 🥧 **Time Distribution Pie** | Visual breakdown of time by category |
| 📊 **Hourly Efficiency Chart** | See efficiency changes throughout the day |
| 📅 **Weekly Trend Chart** | Last 7 days duration and efficiency trends |
| 🏆 **App Leaderboard** | Top 5 most used apps with usage time |
| 📋 **Activity Timeline** | Complete activity list with category filtering |
| 🎨 **Dark Theme** | Consistent with Dayflow desktop style |
| 📱 **Responsive Design** | Works on mobile, tablet, and desktop |

How to use:
1. Go to **Settings** → **Data Management**
2. Click **📊 Export Dashboard**
3. Select date range (Today/This Week/This Month/Custom)
4. Click **Export Report**, opens automatically in browser

> 💡 The exported HTML file is self-contained and can be shared directly with others - no software installation required.

### 📧 Email Report Feature

#### Settings Panel

![Email Settings](assets/Dayflow_Email_Settings.png)

*Email Push Settings: Configure QQ email address and authorization code, with test send support*

#### Email Report Examples

<div align="center">
<img src="assets/Dayflow_Email_Report_1.png" width="45%" alt="Report Example 1"/>
<img src="assets/Dayflow_Email_Report_2.png" width="45%" alt="Report Example 2"/>
</div>

*Daily Productivity Report: Time statistics, category distribution, and AI personalized feedback (different scenarios)*

#### Deep Analysis Report

![Deep Analysis Report](assets/Dayflow_Email_DeepAnalysis.png)

*Professional Analysis: Behavior pattern diagnosis, bottleneck identification, improvement strategies*

Each email contains two levels of analysis:

| Module | Content | Style |
|--------|---------|-------|
| 💬 **Daily Insight** | Interesting findings + quick tips | Friendly chat |
| 📋 **Professional Analysis** | Deep behavior analysis + strategies | Expert-level |

Professional analysis dimensions:

| Dimension | Description |
|-----------|-------------|
| 🔍 **Behavior Pattern** | Identify work type (Deep Work / Fragmented / Multi-tasking) |
| ⚠️ **Efficiency Bottlenecks** | Data-driven identification of low-efficiency periods |
| ✨ **Highlights** | Positive feedback supported by data |
| 📝 **Improvement Strategies** | 2-3 specific actionable suggestions |

#### Feature Highlights

| Feature | Description |
|---------|-------------|
| ⏰ **Scheduled Push** | Default 12:00 and 22:00, customizable send times |
| 🔄 **Smart Catch-up** | Auto-sends missed reports after sleep/shutdown |
| 📊 **Data Summary** | Total time, efficiency score, deep work sessions |
| 📈 **Category Stats** | Visual breakdown with efficiency comparison |
| 🎯 **Focus Analysis** | Longest focus, fragmentation ratio, hourly efficiency |
| 🤖 **Dual Analysis** | Friendly comment + Professional deep report |

### 🔄 Auto Update

![Auto Update](assets/Dayflow_AutoUpdate.png)

*Software Update: One-click check, background download, auto install*

Dayflow supports automatic update detection and installation:

| Feature | Description |
|---------|-------------|
| 🔍 **Check Updates** | One-click check for latest GitHub releases |
| ⬇️ **Background Download** | Multi-source download with mirror acceleration |
| 📊 **Download Progress** | Real-time progress bar display |
| 🚀 **One-Click Install** | Auto restart and install after download |
| 🔗 **Manual Download** | Fallback download links for restricted networks |

Update process:
1. Click **🔍 Check Updates** to detect new version
2. Click **⬇️ Download Update** when available
3. Click **🚀 Install Now** after download completes
4. App auto-restarts and completes update

### 🚀 Auto Start

![Auto Start](assets/Dayflow_AutoStart.png)

*Startup: Auto-launch on boot, silent minimize to tray*

| Feature | Description |
|---------|-------------|
| 🟢 **One-Click Toggle** | Quick enable/disable in settings |
| 🔇 **Silent Start** | Minimizes to tray on boot, no interruption |
| 📍 **Path Detection** | Auto-prompts to update path when EXE is moved |
| 🔒 **No Admin Required** | Uses user-level registry, no admin privileges needed |

> 💡 **Note**: Auto-start is only available in the packaged EXE version, not in development mode.

### Interface Guide

| Area | Function |
|------|----------|
| **Custom Title Bar** | VS Code style, drag to move, minimize to tray |
| **Left Sidebar** | Navigation: Timeline, Statistics, Settings, Recording |
| **Timeline Page** | Displays all activity cards for today, sorted by time |
| **Statistics Page** | View weekly/monthly time distribution and trends |
| **Settings Page** | API config, email, theme, auto-start, updates, logs |
| **System Tray** | Runs in tray when minimized, right-click menu for control |

### Activity Card Details

Each card contains:
- ⏰ **Time Range** - Start and end time of the activity
- 📁 **Category** - Work/Study/Coding/Meeting/Entertainment/Social/Rest
- 💻 **Application** - Main software used
- 📝 **Summary** - AI-generated activity description
- ⚡ **Productivity Score** - 0-100% efficiency rating

---

## 🚀 Quick Start

### Requirements

- Windows 10/11 (64-bit)
- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) (added to system PATH)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/SeiShonagon520/Dayflow.git
cd Dayflow

# 2. Create Conda environment (recommended)
conda create -n dayflow python=3.11 -y
conda activate dayflow

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app
python main.py
```

### Build as EXE (Optional)

To distribute to others without requiring Python installation:

```bash
# Install packaging tool
pip install pyinstaller

# Run build script
python build.py

# Or double-click build.bat
```

After building, the `dist/Dayflow/` folder can be copied and shared directly.

---

## 📖 User Guide

### 1️⃣ Configure API

1. Open the app, click **⚙️ Settings** on the left sidebar
2. Configure API settings:
   - **API URL**: OpenAI-compatible endpoint
   - **API Key**: Your API key
   - **Model**: Vision-capable model name
3. Click **Test Connection** to verify
4. Click **Save Config**

> 💡 Supports any OpenAI-compatible API: OpenAI, DeepSeek, Ollama (local), etc.

### 2️⃣ Start Recording

1. Click **▶ Start Recording**
2. The app records your screen at 1 FPS in the background
3. Video chunks are saved every 60 seconds
4. Automatically sent to cloud AI for analysis

### 3️⃣ View Timeline

- Analysis results appear on the home timeline
- Each card represents an activity period
- Includes: category, applications used, productivity score

### 4️⃣ Email Reports (Optional)

1. Go to **Settings** → **Email Push**
2. Enter your QQ email address and authorization code
3. Customize send times (default: 12:00 and 22:00)
4. Click **Save Config**
5. Click **Test Send** to verify

> 💡 Get auth code: QQ Mail → Settings → Account → POP3/SMTP Service → Generate Authorization Code

**Email Content**:
- 📊 Daily time statistics (total duration, efficiency score)
- 📈 Time distribution by category
- 💬 AI-generated personalized feedback and suggestions

**Smart Catch-up**: If your computer was asleep/off during scheduled send time, missed reports will be automatically sent when you start up (within 2 hours).

### 5️⃣ Auto Start (Optional)

1. Go to **Settings** → **Auto Start**
2. Click button to enable/disable
3. When enabled, app auto-launches and minimizes to tray on boot

> 💡 If you move the EXE file, the app will prompt you to update the startup path.

### 6️⃣ Check Updates (Optional)

1. Go to **Settings** → **Software Update**
2. Click **Check Updates**
3. Click **Download Update** when new version is found
4. Click **Install Now** after download completes

### 7️⃣ System Tray

- Click title bar ↓ button → Minimize to tray
- Click close × → Prompts to exit or minimize
- Double-click tray icon → Open main window
- Right-click tray → Control recording / Exit

---

## 📁 Project Structure

```
Dayflow/
├── 📄 main.py              # Entry point (supports --minimized)
├── ⚙️ config.py            # Configuration (includes version)
├── 📦 requirements.txt     # Dependencies
├── 🔨 build.py             # EXE build script
├── 🔨 build.bat            # One-click build batch
├── 🔄 updater.py           # Standalone update program
│
├── 🧠 core/                # Core logic
│   ├── types.py            # Data models
│   ├── recorder.py         # Screen capture (dxcam)
│   ├── window_tracker.py   # Window tracking (Windows API)
│   ├── llm_provider.py     # AI API integration
│   ├── analysis.py         # Analysis scheduler
│   ├── email_service.py    # Email reports + Deep analysis + Smart catch-up
│   ├── updater.py          # Version check + Multi-source download
│   ├── autostart.py        # Auto-start management
│   ├── config_manager.py   # Centralized config management
│   ├── log_manager.py      # Log rotation management
│   ├── stats_collector.py  # Statistics data collector
│   └── dashboard_exporter.py # Web dashboard export
│
├── 💾 database/            # Data layer
│   ├── schema.sql          # Table definitions
│   ├── storage.py          # SQLite management
│   └── connection_pool.py  # Database connection pool
│
├── 🎨 ui/                  # UI layer
│   ├── main_window.py      # Main window + Settings panel
│   ├── timeline_view.py    # Timeline component
│   ├── stats_view.py       # Statistics panel
│   ├── date_range_dialog.py # Date range selection dialog
│   └── themes.py           # Theme management
│
├── 📄 templates/           # HTML templates
│   └── dashboard.html      # Web dashboard template
│
└── 🖼️ assets/              # Resources
    └── icon.ico            # App icon
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DAYFLOW_API_URL` | API endpoint | `https://apis.iflow.cn/v1` |
| `DAYFLOW_API_KEY` | API key | (empty) |
| `DAYFLOW_API_MODEL` | AI model | `qwen3-vl-plus` |

### Data Directory

```
%LOCALAPPDATA%\Dayflow\
├── dayflow.db          # Database (activity records, settings)
├── dayflow.log         # Runtime logs
├── chunks/             # Video chunks (auto-deleted after analysis)
└── updates/            # Update file cache
    └── Dayflow_vX.X.X.exe  # Downloaded new version
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| GUI Framework | PySide6 (Qt6) |
| Screen Capture | dxcam (DirectX) |
| Video Processing | OpenCV |
| HTTP Client | httpx (HTTP/2) |
| Database | SQLite |
| AI Analysis | OpenAI-compatible API |

---

## 🔐 Security & Privacy

Dayflow takes user privacy seriously with multiple layers of protection:

### Data Storage

| Data Type | Location | Description |
|-----------|----------|-------------|
| Video Chunks | Local `%LOCALAPPDATA%\Dayflow\chunks\` | Temporary storage only |
| Analysis Results | Local `dayflow.db` | SQLite database |
| User Settings | Local database | API Key, email config, etc. |

### Privacy Protection Measures

| Measure | Description |
|---------|-------------|
| 📍 **Local First** | All raw screen recordings are stored locally only, full videos are never uploaded |
| 🗑️ **Auto Cleanup** | Video chunks are automatically deleted after AI analysis, saving disk space |
| 🖼️ **Minimal Transfer** | Only key frames (max 8 per chunk) are extracted and sent for AI analysis |
| ⏸️ **Pause Feature** | Pause recording anytime when handling sensitive content, resume when done |
| 🔒 **Local Database** | Analysis results are stored in local SQLite, never uploaded to cloud |

### Recommendations

- When handling banking, passwords, or sensitive information, click the **⏸️ Pause** button
- Click **▶ Resume** to continue recording when done
- Periodically check `%LOCALAPPDATA%\Dayflow\` to confirm data cleanup is working properly

> 💡 **Note**: Dayflow's design philosophy is "local recording + cloud analysis + local storage". Raw videos never leave your computer.

---

## 💡 Inspiration

This project is inspired by [Dayflow (macOS)](https://github.com/JerryZLiu/Dayflow). Since the original project only supports macOS, I developed this Windows version based on the same concept, allowing more users to experience AI-powered intelligent time tracking.

Thanks to the original author for the creativity and open-source spirit! 🙏

---

## 📄 License

[CC BY-NC-SA 4.0](LICENSE) © 2024-2025

This project is licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0**.
- ✅ Free to learn, modify, and share
- ✅ Please credit the original author when using or modifying
- ❌ Commercial use prohibited

---

## ⭐ Star History

<a href="https://star-history.com/#SeiShonagon520/Dayflow&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=SeiShonagon520/Dayflow&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=SeiShonagon520/Dayflow&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=SeiShonagon520/Dayflow&type=Date" />
 </picture>
</a>

---

<div align="center">

**If you find this useful, please give it a ⭐ Star!**

</div>
