# Dayflow Windows - Development Guide

## 项目完成状态

✅ **Phase 1: Core Recording System** (100%)
- Screen recorder with 1 FPS capture
- Video encoding (H.264, 15-second chunks)
- Multi-monitor support
- Power management (pause on lock/sleep)
- Storage manager with automatic cleanup

✅ **Phase 2: AI Analysis** (100%)
- LLM service abstraction layer
- Google Gemini integration
- Video processor (merge, timelapse)
- Analysis manager with 15-minute scheduling
- Activity categorization

✅ **Phase 3: User Interface** (100%)
- PyQt6 main window with sidebar navigation
- Timeline view with activity cards
- Video player with controls
- Dashboard with statistics and charts
- Journal view for daily reflections
- Settings interface with API key management

✅ **Phase 4: System Integration** (100%)
- System tray icon
- Windows startup management
- Auto-update system
- Notifications

## Quick Start

### 1. Install Dependencies

```bash
# Using pip (recommended for Python 3.13)
pip install -r requirements.txt

# Or using Poetry (for Python < 3.13)
poetry install
```

### 2. Install FFmpeg

Download from https://ffmpeg.org/ and add to system PATH

### 3. Configure API Key

Run the application and go to Settings to configure your Google Gemini API key:
- Get key from: https://makersuite.google.com/
- Enter in Settings > AI Provider Settings

### 4. Run Application

```bash
# Direct run
python src/dayflow/main.py

# Or via venv
./venv/Scripts/python src/dayflow/main.py
```

## Project Structure

```
dayflow-windows/
├── src/dayflow/                    # Main application code
│   ├── core/                       # Core functionality
│   │   ├── recorder.py            # ✅ Screen recording (1 FPS)
│   │   ├── storage.py             # ✅ File & database management
│   │   ├── video_processor.py    # ✅ Video merge & timelapse
│   │   └── power_manager.py      # ✅ Windows power events
│   ├── analysis/                   # AI analysis
│   │   ├── llm_service.py         # ✅ LLM abstraction
│   │   ├── gemini_service.py     # ✅ Gemini integration
│   │   └── analysis_manager.py   # ✅ Scheduled analysis
│   ├── models/                     # Database models
│   │   ├── database.py            # ✅ SQLAlchemy setup
│   │   ├── recording_chunk.py    # ✅ Video chunk model
│   │   ├── timeline_activity.py  # ✅ Activity model
│   │   └── category.py            # ✅ Category model
│   ├── ui/                         # User interface
│   │   ├── main_window.py         # ✅ Main window
│   │   ├── timeline_view.py       # ✅ Timeline display
│   │   ├── dashboard_view.py      # ✅ Statistics dashboard
│   │   ├── journal_view.py        # ✅ Daily journal
│   │   ├── settings_view.py       # ✅ Settings panel
│   │   └── widgets/               # UI components
│   │       ├── activity_card.py   # ✅ Activity display
│   │       ├── video_player.py    # ✅ Video playback
│   │       ├── category_badge.py  # ✅ Category tags
│   │       └── date_navigator.py  # ✅ Date picker
│   ├── services/                   # System services
│   │   ├── system_tray.py         # ✅ Tray icon
│   │   ├── startup_manager.py     # ✅ Startup config
│   │   └── update_manager.py      # ✅ Auto-updates
│   ├── utils/                      # Utilities
│   │   ├── config.py              # ✅ Configuration
│   │   ├── logger.py              # ✅ Logging
│   │   ├── security.py            # ✅ API key storage
│   │   └── notifications.py       # ✅ Notifications
│   └── main.py                     # ✅ Application entry
├── tests/                          # Test suite
├── resources/                      # Icons and config
├── scripts/                        # Build scripts
├── requirements.txt               # ✅ Dependencies
└── README.md                       # ✅ Documentation
```

## Key Features Implemented

### Recording System
- **1 FPS screen capture** using `mss` library
- **H.264 video encoding** with OpenCV
- **15-second chunks** for efficient storage
- **Multi-monitor detection** and recording
- **Automatic pause/resume** on lock/sleep
- **3-day retention** with automatic cleanup

### AI Analysis
- **Google Gemini integration** for video analysis
- **15-minute batch processing** of recordings
- **Activity detection** and categorization
- **Timelapse video generation** (20x speed)
- **Context-aware analysis** using previous activities

### User Interface
- **Modern PyQt6 interface** with sidebar navigation
- **Timeline view** showing daily activities
- **Activity cards** with video playback
- **Dashboard** with productivity statistics
- **Settings** for API configuration
- **System tray** integration

### Data Management
- **SQLite database** for metadata
- **Organized file storage** by date
- **Automatic cleanup** of old recordings
- **Export functionality** for backups

## Configuration

Edit settings via the application UI or directly in:
```
%LOCALAPPDATA%\Dayflow\config.json
```

### Default Configuration

```json
{
  "recording": {
    "fps": 1,
    "chunk_duration_seconds": 15,
    "retention_days": 3,
    "video_quality": "medium"
  },
  "analysis": {
    "provider": "gemini",
    "analysis_interval_minutes": 15,
    "context_window_minutes": 60
  },
  "ui": {
    "theme": "light",
    "show_notifications": true
  }
}
```

## Data Storage

All data is stored locally in:
```
%LOCALAPPDATA%\Dayflow\
├── data\
│   └── dayflow.db          # SQLite database
├── recordings\
│   └── YYYY-MM-DD\
│       └── chunks\         # 15-second video chunks
└── timelapses\
    └── YYYY-MM-DD\         # Generated timelapse videos
```

## Building

### Create Executable

```bash
python scripts/build.py
```

This creates a standalone `.exe` file in the `dist/` directory.

**Note**: PyInstaller requires Python < 3.13. If using Python 3.13, install separately:
```bash
pip install pyinstaller
```

## Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_recorder.py

# With coverage
pytest --cov=dayflow --cov-report=html
```

## Development Workflow

1. **Make changes** to source code in `src/dayflow/`
2. **Test changes**:
   ```bash
   python src/dayflow/main.py
   ```
3. **Run tests**: `pytest`
4. **Format code**: `black src/`
5. **Check types**: `mypy src/`
6. **Build**: `python scripts/build.py`

## Troubleshooting

### FFmpeg not found
Download from https://ffmpeg.org/ and add to PATH

### API key not working
- Verify key in Settings
- Check Windows Credential Manager: `keyring.get_password("Dayflow", "gemini_api_key")`

### Recording not starting
- Check screen capture permissions
- Look for errors in logs: `%LOCALAPPDATA%\Dayflow\logs\dayflow.log`

### Video playback issues
- Ensure PyQt6-WebEngine is installed
- Check video codec support

## Architecture Notes

### Recording Pipeline
1. `ScreenRecorder` captures frames at 1 FPS
2. Frames buffered for 15 seconds
3. `VideoProcessor` encodes to H.264 MP4
4. `StorageManager` saves to database + filesystem

### Analysis Pipeline
1. `AnalysisManager` runs every 15 minutes
2. Merges 15-second chunks into 15-minute batch
3. `GeminiService` analyzes video
4. Extracts activity segments
5. Generates timelapse videos
6. Saves to database

### UI Architecture
- **Main Window**: Sidebar navigation + stacked views
- **Views**: Timeline, Dashboard, Journal, Settings
- **Widgets**: Reusable components (cards, players, etc.)
- **System Tray**: Background operation support

## Next Steps / TODOs

While the core application is complete, here are potential enhancements:

- [ ] Additional AI providers (Ollama, OpenAI fully tested)
- [ ] Application usage tracking (active window detection)
- [ ] Keyboard/mouse activity heatmaps
- [ ] Team collaboration features
- [ ] Mobile companion app
- [ ] Advanced search and filtering
- [ ] Custom activity rules
- [ ] Data export formats (CSV, JSON)
- [ ] Inno Setup installer script

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit pull request

## License

MIT License - see LICENSE file

## Support

- GitHub Issues: https://github.com/your-repo/issues
- Documentation: See README.md
