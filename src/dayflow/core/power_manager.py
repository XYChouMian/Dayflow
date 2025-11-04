"""Windows power management - monitor sleep/wake/lock events."""

import logging
import threading
from typing import Optional, Callable
import win32api
import win32con
import win32gui
import winerror

logger = logging.getLogger(__name__)


class PowerManager:
    """
    Monitors Windows power events (sleep, wake, lock, unlock).
    Integrates with ScreenRecorder to pause/resume recording.
    """

    # Windows power broadcast messages
    PBT_APMSUSPEND = 0x0004  # System is suspending
    PBT_APMRESUMEAUTOMATIC = 0x0012  # System resumed from suspend
    WM_POWERBROADCAST = 0x0218

    # Session change messages
    WM_WTSSESSION_CHANGE = 0x02B1
    WTS_SESSION_LOCK = 0x7  # Session locked
    WTS_SESSION_UNLOCK = 0x8  # Session unlocked

    def __init__(
        self,
        on_sleep: Optional[Callable[[], None]] = None,
        on_wake: Optional[Callable[[], None]] = None,
        on_lock: Optional[Callable[[], None]] = None,
        on_unlock: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize power manager.

        Args:
            on_sleep: Callback when system goes to sleep
            on_wake: Callback when system wakes up
            on_lock: Callback when session is locked
            on_unlock: Callback when session is unlocked
        """
        self.on_sleep = on_sleep
        self.on_wake = on_wake
        self.on_lock = on_lock
        self.on_unlock = on_unlock

        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.hwnd = None

    def start(self) -> None:
        """Start monitoring power events."""
        if self.is_monitoring:
            logger.warning("Power monitoring already active")
            return

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Power monitoring started")

    def stop(self) -> None:
        """Stop monitoring power events."""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        if self.hwnd:
            try:
                win32gui.DestroyWindow(self.hwnd)
            except Exception as e:
                logger.error(f"Error destroying window: {e}")

        if self.monitor_thread:
            self.monitor_thread.join(timeout=3.0)

        logger.info("Power monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop - creates hidden window to receive messages."""
        try:
            # Register window class
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = self._wnd_proc
            wc.lpszClassName = "DayflowPowerMonitor"
            wc.hInstance = win32api.GetModuleHandle(None)

            try:
                class_atom = win32gui.RegisterClass(wc)
            except Exception as e:
                if e.winerror != winerror.ERROR_CLASS_ALREADY_EXISTS:
                    raise
                class_atom = win32gui.RegisterClass(wc)

            # Create hidden window
            self.hwnd = win32gui.CreateWindow(
                class_atom,
                "Dayflow Power Monitor",
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                wc.hInstance,
                None,
            )

            logger.info(f"Power monitor window created: {self.hwnd}")

            # Message loop
            win32gui.PumpMessages()

        except Exception as e:
            logger.error(f"Error in power monitoring loop: {e}", exc_info=True)

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        """Window procedure to handle power messages."""
        try:
            if msg == self.WM_POWERBROADCAST:
                if wparam == self.PBT_APMSUSPEND:
                    logger.info("System suspending (sleep)")
                    if self.on_sleep:
                        self.on_sleep()
                elif wparam == self.PBT_APMRESUMEAUTOMATIC:
                    logger.info("System resuming (wake)")
                    if self.on_wake:
                        self.on_wake()

            elif msg == self.WM_WTSSESSION_CHANGE:
                if wparam == self.WTS_SESSION_LOCK:
                    logger.info("Session locked")
                    if self.on_lock:
                        self.on_lock()
                elif wparam == self.WTS_SESSION_UNLOCK:
                    logger.info("Session unlocked")
                    if self.on_unlock:
                        self.on_unlock()

        except Exception as e:
            logger.error(f"Error in window procedure: {e}", exc_info=True)

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


class IdleDetector:
    """Detect system idle time (no mouse/keyboard activity)."""

    def __init__(self, idle_threshold_seconds: int = 300):
        """
        Initialize idle detector.

        Args:
            idle_threshold_seconds: Seconds of inactivity to consider idle (default: 5 min)
        """
        self.idle_threshold = idle_threshold_seconds

    def get_idle_time(self) -> float:
        """
        Get system idle time in seconds.

        Returns:
            Seconds since last input
        """
        try:
            import ctypes

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_uint),
                    ("dwTime", ctypes.c_uint),
                ]

            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)

            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo)):
                millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
                return millis / 1000.0
            return 0.0

        except Exception as e:
            logger.error(f"Error getting idle time: {e}")
            return 0.0

    def is_idle(self) -> bool:
        """Check if system is currently idle."""
        return self.get_idle_time() >= self.idle_threshold
