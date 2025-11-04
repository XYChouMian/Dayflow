# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application
```bash
# Simple run (uses virtual environment)
run.bat

# Poetry development run
poetry run dayflow

# Direct Python execution
python src/dayflow/main.py
```

### Development
```bash
# Install dependencies
poetry install

# Code formatting
poetry run black src/
poetry run ruff check src/

# Type checking
poetry run mypy src/

# Run tests
poetry run pytest
```

### Building
```bash
# Build Windows executable (requires PyInstaller installed separately)
poetry run python scripts/build.py
```

## Architecture Overview

Dayflow is a Windows time-tracking application built with PyQt6 that automatically records screen activity and uses AI to analyze and categorize user activities.

### Core Components

**Application Entry (`src/dayflow/main.py`)**
- `DayflowApp`: Main application coordinator that initializes and manages all subsystems
- Handles component lifecycle, error handling, and application shutdown

**Recording Engine (`src/dayflow/core/`)**
- `ScreenRecorder`: Continuous screen capture at 1 FPS using mss library
- `VideoProcessor`: Converts screenshots to videos using FFmpeg/OpenCV
- `StorageManager`: Manages file storage and cleanup (3-day retention policy)
- `PowerManager`: Handles system power events and pause/resume recording

**Analysis Engine (`src/dayflow/analysis/`)**
- `AnalysisManager`: Coordinates AI analysis of video recordings
- `llm_service.py`: Unified LLM service supporting multiple providers (Gemini, OpenAI, Ollama)
- Uses Chinese prompts and returns Chinese activity categories
- Categories activities: 工作(work), 会议(meeting), 休息(break), 效率(productivity), 学习(study), 娱乐(entertainment)

**Database Layer (`src/dayflow/models/`)**
- SQLAlchemy ORM with timeline activities, categories, and analysis results
- `get_session_direct()` utility for database access
- Automatic database initialization with `init_db()`

**UI Framework (`src/dayflow/ui/`)**
- **Theme System**: `theme.py` provides centralized styling with gradients, colors, and Chinese font support
- **Modern Dashboard**: `dashboard_view_new.py` with statistics cards and charts using matplotlib
- **Components**: Reusable widgets like `StatCard`, `ActivityCard` with category-colored borders
- All UI text localized to Chinese

**System Integration (`src/dayflow/services/`)**
- `SystemTrayIcon`: Windows system tray integration with Chinese tooltips
- Background recording service with pause/resume capabilities

### Key Architectural Patterns

**Configuration Management**
- `Config` class in `utils/config.py` manages all application settings
- Settings stored in Windows registry/local config files
- Secure API key storage via Windows Credential Manager

**Chinese Localization**
- Matplotlib configured for Chinese fonts: `mpl.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']`
- All UI elements, prompts, and AI responses in Chinese
- Category mapping supports both Chinese and English inputs

**Privacy-First Design**
- All recordings stored locally
- 3-day automatic data cleanup
- Optional local AI processing via Ollama
- No telemetry or data collection

**Modern UI Design**
- Gradient-based color scheme with category-specific colors
- Transparent chart backgrounds for better integration
- Responsive layout with proper spacing and typography
- Component-based architecture for maintainability

### Data Flow

1. **Recording**: `ScreenRecorder` captures screenshots → `VideoProcessor` creates videos → `StorageManager` stores files
2. **Analysis**: `AnalysisManager` picks up new recordings → `llm_service.py` analyzes with AI → results stored in database
3. **Display**: UI components query database → visualize activities with charts and timelines

### Important Implementation Notes

**Chinese Font Support**: Always configure matplotlib for Chinese fonts when creating charts:
```python
mpl.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
mpl.rcParams['axes.unicode_minus'] = False
```

**Theme Consistency**: Use `Theme` class for all styling:
```python
from dayflow.ui.theme import Theme
category_color = Theme.get_category_color(category_name)
```

**Database Sessions**: Always close sessions properly:
```python
session = get_session_direct()
try:
    # Database operations
    pass
finally:
    session.close()
```

**Error Handling**: Application uses comprehensive logging with `logger.error(exc_info=True)` for debugging

### File Structure Notes

- Main executable entry: `src/dayflow/main.py`
- Virtual environment setup: `run.bat` handles venv activation and PYTHONPATH
- Build script: `scripts/build.py` creates standalone Windows executable
- UI improvements documented in `UI_IMPROVEMENTS.md`
- Configuration in `pyproject.toml` with Poetry dependency management