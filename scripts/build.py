"""Build script for creating Windows executable."""

import subprocess
import sys
from pathlib import Path


def build_executable():
    """Build Windows executable using PyInstaller."""
    print("Building Dayflow Windows executable...")

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=Dayflow",
        "--windowed",  # No console window
        "--onefile",  # Single executable
        "--icon=resources/icons/app_icon.ico",
        "--add-data=resources;resources",
        "--hidden-import=PyQt6",
        "--hidden-import=cv2",
        "--hidden-import=sqlalchemy",
        "--hidden-import=google.generativeai",
        "--clean",
        "src/dayflow/main.py",
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print("\n✓ Build successful!")
        print("Executable created in: dist/Dayflow.exe")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(build_executable())
