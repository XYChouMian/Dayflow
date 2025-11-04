"""System services and integrations."""

from dayflow.services.startup_manager import StartupManager
from dayflow.services.update_manager import UpdateManager
from dayflow.services.system_tray import SystemTrayIcon

__all__ = [
    "StartupManager",
    "UpdateManager",
    "SystemTrayIcon",
]
