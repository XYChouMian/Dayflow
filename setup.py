"""Setup script for Dayflow Windows."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="dayflow-windows",
    version="0.1.0",
    description="Automatic timeline generation tool for Windows",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Dayflow Team",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "mss>=9.0.1",
        "opencv-python>=4.8.1",
        "Pillow>=10.1.0",
        "ffmpeg-python>=0.2.0",
        "sqlalchemy>=2.0.23",
        "alembic>=1.12.1",
        "google-generativeai>=0.3.1",
        "openai>=1.3.5",
        "requests>=2.31.0",
        "PyQt6>=6.6.0",
        "PyQt6-WebEngine>=6.6.0",
        "matplotlib>=3.8.2",
        "pywin32>=306; platform_system=='Windows'",
        "psutil>=5.9.6",
        "plyer>=2.1.0",
        "cryptography>=41.0.7",
        "keyring>=24.3.0",
        "python-dateutil>=2.8.2",
        "apscheduler>=3.10.4",
    ],
    entry_points={
        "console_scripts": [
            "dayflow=dayflow.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
