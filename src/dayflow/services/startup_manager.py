"""Windows startup management."""

import logging
import sys
from pathlib import Path
import winreg

logger = logging.getLogger(__name__)


class StartupManager:
    """Manage application startup with Windows."""

    APP_NAME = "Dayflow"
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

    @classmethod
    def is_enabled(cls) -> bool:
        """
        Check if application is set to start with Windows.

        Returns:
            True if startup is enabled
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.REGISTRY_PATH,
                0,
                winreg.KEY_READ,
            )

            try:
                winreg.QueryValueEx(key, cls.APP_NAME)
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)

        except Exception as e:
            logger.error(f"Error checking startup status: {e}")
            return False

    @classmethod
    def enable(cls) -> bool:
        """
        Enable application startup with Windows.

        Returns:
            True if successful
        """
        try:
            # Get executable path
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                exe_path = sys.executable
            else:
                # Running as script
                exe_path = sys.executable + " " + str(Path(__file__).parent.parent / "main.py")

            # Add to registry
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.REGISTRY_PATH,
                0,
                winreg.KEY_WRITE,
            )

            try:
                winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, exe_path)
                logger.info(f"Enabled startup: {exe_path}")
                return True
            finally:
                winreg.CloseKey(key)

        except Exception as e:
            logger.error(f"Error enabling startup: {e}", exc_info=True)
            return False

    @classmethod
    def disable(cls) -> bool:
        """
        Disable application startup with Windows.

        Returns:
            True if successful
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.REGISTRY_PATH,
                0,
                winreg.KEY_WRITE,
            )

            try:
                winreg.DeleteValue(key, cls.APP_NAME)
                logger.info("Disabled startup")
                return True
            except FileNotFoundError:
                # Already not in startup
                return True
            finally:
                winreg.CloseKey(key)

        except Exception as e:
            logger.error(f"Error disabling startup: {e}", exc_info=True)
            return False

    @classmethod
    def toggle(cls) -> bool:
        """
        Toggle startup enabled/disabled.

        Returns:
            New state (True = enabled, False = disabled)
        """
        if cls.is_enabled():
            cls.disable()
            return False
        else:
            cls.enable()
            return True
