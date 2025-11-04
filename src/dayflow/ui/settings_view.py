"""Settings view - application configuration."""

import logging
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt

from dayflow.utils.config import Config
from dayflow.utils.security import SecureStorage

logger = logging.getLogger(__name__)


class SettingsView(QWidget):
    """Settings view for application configuration."""

    def __init__(self, config: Config):
        """
        Initialize settings view.

        Args:
            config: Application configuration
        """
        super().__init__()
        self.config = config
        self.setup_ui()
        self.load_settings()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title = QLabel("设置")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # AI Provider Settings
        ai_group = self._create_ai_settings_group()
        layout.addWidget(ai_group)

        # Recording Settings
        recording_group = self._create_recording_settings_group()
        layout.addWidget(recording_group)

        # Privacy Settings
        privacy_group = self._create_privacy_settings_group()
        layout.addWidget(privacy_group)

        # Save button
        save_btn = QPushButton("💾 保存设置")
        save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """
        )
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()

        scroll.setWidget(container)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_ai_settings_group(self) -> QGroupBox:
        """Create AI settings group."""
        group = QGroupBox("AI 提供商设置")
        group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #BDC3C7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """
        )

        form = QFormLayout(group)

        # Provider selection
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Gemini", "OpenAI", "Ollama"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        form.addRow("AI 提供商:", self.provider_combo)

        # Model selection
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash-lite",
        ])
        form.addRow("模型:", self.model_combo)

        # API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("输入 API 密钥...")
        form.addRow("API 密钥:", self.api_key_input)

        # Load API key button
        load_key_btn = QPushButton("加载已保存的密钥")
        load_key_btn.clicked.connect(self.load_api_key)
        form.addRow("", load_key_btn)

        # Analysis interval
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(5, 60)
        self.interval_spin.setSuffix(" 分钟")
        form.addRow("分析间隔:", self.interval_spin)

        return group

    def _create_recording_settings_group(self) -> QGroupBox:
        """Create recording settings group."""
        group = QGroupBox("录制设置")
        group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #BDC3C7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """
        )

        form = QFormLayout(group)

        # Video quality
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["低", "中", "高"])
        form.addRow("视频质量:", self.quality_combo)

        # Retention days
        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(1, 30)
        self.retention_spin.setSuffix(" 天")
        form.addRow("保留录制:", self.retention_spin)

        return group

    def _create_privacy_settings_group(self) -> QGroupBox:
        """Create privacy settings group."""
        group = QGroupBox("隐私设置")
        group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #BDC3C7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """
        )

        form = QFormLayout(group)

        info_label = QLabel(
            "• 所有录制内容都存储在您的本地计算机上\n"
            "• API 密钥安全存储在 Windows 凭据管理器中\n"
            "• 视频会在保留期后自动删除\n"
            "• 不会收集或向第三方发送任何数据"
        )
        info_label.setStyleSheet("color: #7F8C8D;")
        info_label.setWordWrap(True)
        form.addRow(info_label)

        return group

    def load_settings(self) -> None:
        """Load current settings."""
        try:
            # AI settings
            provider_map = {"gemini": 0, "openai": 1, "ollama": 2}
            self.provider_combo.setCurrentIndex(
                provider_map.get(self.config.analysis.provider.lower(), 0)
            )

            # Load model name
            model_name = getattr(self.config.analysis, "model_name", "gemini-2.5-flash")
            index = self.model_combo.findText(model_name)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)

            self.interval_spin.setValue(self.config.analysis.analysis_interval_minutes)

            # Recording settings
            quality_map = {"low": 0, "medium": 1, "high": 2}
            quality_index = quality_map.get(self.config.recording.video_quality.lower(), 1)
            self.quality_combo.setCurrentIndex(quality_index)

            self.retention_spin.setValue(self.config.recording.retention_days)

        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def load_api_key(self) -> None:
        """Load API key from secure storage."""
        provider = self.provider_combo.currentText().lower()
        key = SecureStorage.get_api_key(provider)

        if key:
            self.api_key_input.setText(key)
            QMessageBox.information(self, "成功", f"已加载 {provider} API 密钥")
        else:
            QMessageBox.warning(self, "未找到", f"没有找到 {provider} 的保存密钥")

    def save_settings(self) -> None:
        """Save current settings."""
        try:
            # Save AI settings
            provider = self.provider_combo.currentText().lower()
            self.config.set("analysis.provider", provider)
            self.config.set("analysis.model_name", self.model_combo.currentText())
            self.config.set(
                "analysis.analysis_interval_minutes", self.interval_spin.value()
            )

            # Save API key if provided
            api_key = self.api_key_input.text().strip()
            if api_key:
                SecureStorage.save_api_key(provider, api_key)
                logger.info(f"Saved API key for {provider}")

            # Save recording settings
            quality_text = self.quality_combo.currentText()
            quality_map = {"低": "low", "中": "medium", "高": "high"}
            quality = quality_map.get(quality_text, "medium")
            self.config.set("recording.video_quality", quality)
            self.config.set("recording.retention_days", self.retention_spin.value())

            QMessageBox.information(self, "成功", "设置保存成功！")
            logger.info("Settings saved")

        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")

    def _on_provider_changed(self, provider: str) -> None:
        """Update model list when provider changes."""
        self.model_combo.clear()

        if provider.lower() == "gemini":
            self.model_combo.addItems([
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash-lite",
            ])
        elif provider.lower() == "openai":
            self.model_combo.addItems([
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
            ])
        elif provider.lower() == "ollama":
            self.model_combo.addItems([
                "llama3.2-vision",
                "llava",
                "bakllava",
            ])
