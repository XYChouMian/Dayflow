<div align="center">

# 🕐 Dayflow for Windows

**AI-Powered Time Tracking - Automatically Record, Intelligently Analyze, Visualize Your Day**

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](https://www.microsoft.com/windows)

English | [简体中文](README.md)

</div>

---

## 💡 Project Origin

This project is inspired by [Dayflow by JerryZLiu](https://github.com/JerryZLiu/Dayflow), an excellent time-tracking application for macOS. Since the original project only supports macOS and cannot be used on Windows, I developed this version from scratch for the Windows platform, following the core concepts of the original project.

This project uses different technology stacks and implementation approaches, specifically optimized for Windows systems, aiming to provide Windows users with an equally excellent automated time-tracking experience.

---

## 📖 Overview

Dayflow is an automated time-tracking application designed for Windows. It runs silently in the background, automatically recording your screen activity and using AI to intelligently analyze and categorize your work, helping you:

- 📊 **Understand Time Allocation** - Visualize where your time goes
- 🤖 **AI-Powered Analysis** - Automatically identify and categorize different activities
- 🎬 **Replay Highlights** - Generate time-lapse videos to quickly review your day
- 🔒 **Privacy First** - All data stored locally with automatic 3-day cleanup

---

## ✨ Key Features

### 🎯 Automated Recording
- **Seamless Capture** - 1 FPS low-frequency recording without affecting system performance
- **Smart Pause** - Automatically stops recording when system is locked or asleep
- **Chunked Videos** - Save video chunks every 15 seconds for easy analysis

### 🧠 AI-Powered Analysis
- **Multi-Model Support** - Supports Google Gemini, OpenAI, Ollama, and more
- **Automatic Categorization** - Identifies work, meetings, breaks, study, entertainment, and other activity types
- **Chinese Optimized** - AI prompts and results fully optimized for Chinese users
- **Scheduled Analysis** - Automatically analyzes new recordings every 15 minutes

### 📈 Visual Dashboard
- **Modern Interface** - Gradient color scheme with card-based design
- **Activity Timeline** - Intuitive display of daily activity flow
- **Statistical Charts** - matplotlib-powered data visualization
- **Time-lapse Playback** - 20x speed playback to quickly review your day

### 🔐 Privacy & Security
- **Local Storage** - All data stored locally, never uploaded to cloud
- **Auto Cleanup** - Automatically delete old recordings after 3 days to save space
- **Encrypted Credentials** - API keys securely stored via Windows Credential Manager
- **Optional Local AI** - Supports Ollama local models, no internet required

---

## 🚀 Quick Start

### System Requirements

- **OS**: Windows 10 or Windows 11
- **Python**: 3.10 or higher
- **RAM**: 4GB+ recommended
- **Disk Space**: At least 500MB (for recording storage)
- **FFmpeg**: Required (for video processing)

### Installation

#### 1️⃣ Clone Repository

```bash
git clone https://github.com/yourusername/dayflow.git
cd dayflow
```

#### 2️⃣ Setup Development Environment

Double-click `setup_dev.bat` or run in command line:

```bash
setup_dev.bat
```

This will automatically create a virtual environment and install all dependencies.

#### 3️⃣ Install FFmpeg

**Option 1: Using Chocolatey (Recommended)**
```bash
choco install ffmpeg
```

**Option 2: Manual Installation**
1. Download FFmpeg: https://ffmpeg.org/download.html#build-windows
2. Extract to directory (e.g., `C:\ffmpeg`)
3. Add `bin` directory to system PATH environment variable

**Verify Installation:**
```bash
ffmpeg -version
```

#### 4️⃣ Launch Application

Double-click `run.bat` or run in command line:

```bash
run.bat
```

---

## ⚙️ Configuration

### Initial Setup

1. After launching the application, navigate to **Settings** view

2. Configure AI Provider:
   - **Google Gemini** (Recommended)
     - Get API Key: https://makersuite.google.com/app/apikey
   - **OpenAI**
     - Get API Key: https://platform.openai.com/api-keys
   - **Ollama** (Local)
     - Install Ollama: https://ollama.ai/
     - Download model: `ollama pull llama2`

3. Adjust Recording Settings (Optional):
   - **Video Quality**: Low / Medium / High
   - **Keep Recordings**: 1-7 days
   - **Analysis Interval**: Analysis frequency

4. Click **💾 Save Settings** to save configuration

### Configuration Files Location

All configuration and data stored at:
```
%LOCALAPPDATA%\Dayflow\
├── config.json          # Application config
├── data\
│   └── dayflow.db       # SQLite database
├── recordings\          # Recording chunks
│   └── YYYY-MM-DD\
└── timelapses\          # Time-lapse videos
    └── YYYY-MM-DD\
```

---

## 🎯 Usage Guide

### Basic Workflow

1. **Launch App** - Double-click `run.bat` or launch from system tray
2. **Auto Record** - Dayflow automatically starts recording in background
3. **AI Analysis** - Automatically analyzes recorded content every 15 minutes
4. **View Results** - Check analysis results in Timeline or Dashboard view
5. **Review Videos** - Click activity cards to play time-lapse videos

### System Tray Functions

Right-click system tray icon:
- **Open Dayflow** - Show main window
- **Pause/Resume Recording** - Manually control recording
- **Exit** - Close application

### Keyboard Shortcuts

- `Ctrl+Q` - Exit application
- `F5` - Refresh current view

---

## 🏗️ Architecture

### Tech Stack

**Frontend Framework**
- PyQt6 - Modern GUI framework
- matplotlib - Data visualization
- PyQt6-WebEngine - Video playback

**Backend Core**
- SQLAlchemy - ORM database management
- APScheduler - Task scheduling
- mss - High-performance screen capture

**Video Processing**
- OpenCV - Image processing
- FFmpeg - Video encoding and merging

**AI Integration**
- google-generativeai - Gemini API
- openai - OpenAI API
- requests - Ollama API

**System Integration**
- pywin32 - Windows API integration
- psutil - System monitoring
- keyring - Secure credential storage

### Project Structure

```
dayflow/
├── src/
│   └── dayflow/
│       ├── main.py              # Application entry
│       ├── core/                # Core recording engine
│       │   ├── screen_recorder.py
│       │   ├── video_processor.py
│       │   └── storage_manager.py
│       ├── analysis/            # AI analysis engine
│       │   ├── analysis_manager.py
│       │   └── llm_service.py
│       ├── models/              # Database models
│       ├── ui/                  # UI components
│       │   ├── main_window.py
│       │   ├── dashboard_view.py
│       │   ├── timeline_view.py
│       │   └── widgets/
│       ├── services/            # System services
│       └── utils/               # Utility functions
├── tests/                       # Test files
├── resources/                   # Resource files
├── scripts/                     # Build scripts
└── archive/                     # Archived docs
```

### Data Flow

```
Screen Capture → Video Chunks → AI Analysis → Database Storage → UI Display
       ↓              ↓              ↓              ↓              ↓
     1 FPS        15s/chunk      Gemini AI       SQLite         PyQt6
```

---

## 🛠️ Development Guide

### Development Environment Setup

```bash
# Install Poetry (optional, recommended)
pip install poetry

# Install dependencies with Poetry
poetry install

# Or use pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run Tests

```bash
# Using Poetry
poetry run pytest

# Or directly with pytest
venv\Scripts\pytest
```

### Code Formatting

```bash
# Format code
poetry run black src/

# Check code style
poetry run ruff check src/

# Type checking
poetry run mypy src/
```

### Build Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Run build script
poetry run python scripts/build.py
```

After building, the executable will be in the `dist/` directory.

---

## 🐛 Troubleshooting

<details>
<summary><strong>❌ ModuleNotFoundError: No module named 'dayflow'</strong></summary>

**Solution:**
1. Make sure you ran `setup_dev.bat`
2. Or use `run.bat` to launch (PYTHONPATH is automatically set)
</details>

<details>
<summary><strong>❌ FFmpeg not found</strong></summary>

**Solution:**
1. Install FFmpeg (see installation steps)
2. Confirm FFmpeg is added to system PATH
3. Restart application
</details>

<details>
<summary><strong>❌ API call failed</strong></summary>

**Checklist:**
- ✅ Is API Key correct?
- ✅ Is network connection working?
- ✅ Is API quota sufficient?
- ✅ Are settings saved?
</details>

<details>
<summary><strong>❌ Recording not starting</strong></summary>

**Troubleshooting steps:**
1. Check system tray icon status
2. Check logs: `%LOCALAPPDATA%\Dayflow\logs\dayflow.log`
3. Confirm screen recording permissions
</details>

For more issues, see [QUICKSTART.md](QUICKSTART.md)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork** this repository
2. Create feature branch: `git checkout -b feature/AmazingFeature`
3. Commit changes: `git commit -m 'Add some AmazingFeature'`
4. Push to branch: `git push origin feature/AmazingFeature`
5. Submit **Pull Request**

### Contribution Guidelines

- Follow existing code style (use Black formatter)
- Add necessary tests
- Update relevant documentation
- Run all tests before submitting

---

## 📄 License

This project is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

**In simple terms:**
- ✅ **Free to Use** - For personal learning, research, and non-commercial purposes
- ✅ **Modify and Share** - Improve and share your modified versions
- ❌ **No Commercial Use** - Cannot be used for commercial purposes or sold
- 🔒 **ShareAlike** - Modified works must use the same license

See the [LICENSE](LICENSE) file for full license terms.

---

## 🙏 Acknowledgments

### Special Thanks

- [Dayflow by JerryZLiu](https://github.com/JerryZLiu/Dayflow) - The inspiration for this project, an excellent time-tracking application for macOS

### Open Source Projects

Thanks to the following open-source projects:

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [FFmpeg](https://ffmpeg.org/) - Video processing
- [OpenCV](https://opencv.org/) - Computer vision
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI analysis
- [matplotlib](https://matplotlib.org/) - Data visualization

---

## 📞 Contact

- Submit Issues: [GitHub Issues](https://github.com/yourusername/dayflow/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/dayflow/discussions)

---

## 🗺️ Roadmap

- [ ] Multi-monitor recording support
- [ ] Additional AI model support
- [ ] Export functionality (PDF, Excel reports)
- [ ] Team collaboration features
- [ ] macOS and Linux support
- [ ] Browser extension integration

---

<div align="center">

**⭐ If this project helps you, please give it a Star!**

Made with ❤️ by Dayflow Team

</div>
