# Dayflow for Windows

> Automatic timeline generation tool - AI-powered screen recording and activity tracking

## Overview

Dayflow is an intelligent time-tracking application that automatically records your screen activity, analyzes it using AI, and generates a visual timeline of your day. This is the Windows port of the macOS Dayflow application.

## Features

- **Automatic Screen Recording**: Records your screen at 1 FPS in 15-second chunks
- **AI-Powered Analysis**: Uses Google Gemini (or other LLMs) to analyze and categorize your activities
- **Activity Timeline**: Visual timeline showing what you did throughout the day
- **Video Playback**: Timelapse videos of each activity (20x speed)
- **Privacy-First**: Optional local processing with Ollama, 3-day data retention
- **Dashboard**: Productivity metrics and trends visualization
- **Journal**: Daily reflection prompts and activity highlights

## Requirements

- Windows 10 or later
- Python 3.10+
- Poetry (for development)
- FFmpeg (for video processing)

## Installation

### For Users

Download the latest installer from [Releases](https://github.com/your-repo/releases).

### For Developers

1. Clone the repository:
```bash
git clone https://github.com/your-repo/dayflow-windows.git
cd dayflow-windows
```

2. Install Poetry:
```bash
pip install poetry
```

3. Install dependencies:
```bash
poetry install
```

4. Install FFmpeg:
- Download from https://ffmpeg.org/
- Add to system PATH

5. Run the application:
```bash
poetry run dayflow
```

## Configuration

### AI Providers

Dayflow supports multiple AI providers:

1. **Google Gemini** (Recommended)
   - Fast cloud-based analysis
   - Requires API key from https://makersuite.google.com/

2. **Ollama** (Privacy-focused)
   - Free local processing
   - Install from https://ollama.ai/
   - Requires LLaVA or similar vision model

3. **OpenAI GPT-4V**
   - High-quality analysis
   - Requires OpenAI API key

### Settings

Configure the application via Settings panel:
- AI provider and API keys
- Recording quality and retention
- Activity categories
- Privacy preferences

## Development

### Project Structure

```
dayflow-windows/
├── src/dayflow/          # Main application code
│   ├── core/             # Recording and video processing
│   ├── analysis/         # AI analysis engine
│   ├── models/           # Database models
│   ├── ui/               # PyQt6 user interface
│   ├── utils/            # Utilities
│   └── services/         # System services
├── resources/            # Icons and config
├── tests/                # Test suite
└── docs/                 # Documentation
```

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black src/
poetry run ruff check src/
```

### Building

```bash
poetry run python scripts/build.py
```

## Privacy & Security

- All recordings stored locally on your machine
- Optional cloud AI processing (can use local Ollama instead)
- Automatic cleanup after 3 days
- API keys stored in Windows Credential Manager
- No telemetry or data collection

## License

MIT License - see LICENSE file for details

## Credits

Inspired by the original Dayflow macOS application.

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-repo/issues
- Documentation: https://github.com/your-repo/wiki
