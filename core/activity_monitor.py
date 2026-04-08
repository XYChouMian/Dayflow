"""
活跃度感知模块 - 监测用户是否在线
通过监听键盘和鼠标事件来判断用户是否活跃
"""
import time
import logging
import threading
from typing import Optional, Callable
from datetime import datetime

try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logging.warning("pynput 未安装，活跃度监测功能将不可用")

logger = logging.getLogger(__name__)


class ActivityMonitor:
    """
    活跃度监测器
    - 监听键盘和鼠标事件
    - 判断用户是否活跃
    - 支持闲置阈值配置
    - 支持状态变化回调
    """
    
    def __init__(
        self,
        idle_threshold: int = 300,  # 闲置阈值（秒），默认5分钟
        on_active: Optional[Callable[[], None]] = None,
        on_idle: Optional[Callable[[], None]] = None
    ):
        """
        初始化活跃度监测器
        
        Args:
            idle_threshold: 闲置阈值（秒），超过此时间无操作视为闲置
            on_active: 用户变为活跃时的回调函数
            on_idle: 用户变为闲置时的回调函数
        """
        self.idle_threshold = idle_threshold
        self.on_active = on_active
        self.on_idle = on_idle
        
        # 状态
        self.last_action_time = time.time()
        self._is_active = True
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 监听器
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        
        # 状态变化锁
        self._state_lock = threading.Lock()
        
        if not PYNPUT_AVAILABLE:
            logger.error("pynput 未安装，无法启动活跃度监测")
    
    def _on_mouse_move(self, x, y):
        """鼠标移动事件"""
        self._update_activity()
    
    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        self._update_activity()
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """鼠标滚动事件"""
        self._update_activity()
    
    def _on_key_press(self, key):
        """键盘按键事件"""
        self._update_activity()
    
    def _update_activity(self):
        """更新活跃状态"""
        self.last_action_time = time.time()
        
        # 检查是否需要触发活跃回调
        with self._state_lock:
            if not self._is_active:
                self._is_active = True
                logger.info("用户变为活跃状态")
                if self.on_active:
                    try:
                        self.on_active()
                    except Exception as e:
                        logger.error(f"活跃回调执行失败: {e}")
    
    def _monitor_loop(self):
        """监测循环"""
        logger.info(f"活跃度监测已启动，闲置阈值: {self.idle_threshold}秒")
        
        while not self._stop_event.is_set():
            try:
                # 检查是否闲置
                idle_time = time.time() - self.last_action_time
                is_idle = idle_time >= self.idle_threshold
                
                # 检查是否需要触发闲置回调
                with self._state_lock:
                    if is_idle and self._is_active:
                        self._is_active = False
                        logger.info(f"用户变为闲置状态（闲置时间: {idle_time:.0f}秒）")
                        if self.on_idle:
                            try:
                                self.on_idle()
                            except Exception as e:
                                logger.error(f"闲置回调执行失败: {e}")
                
                # 等待一段时间再检查
                self._stop_event.wait(5)  # 每5秒检查一次
                
            except Exception as e:
                logger.error(f"活跃度监测错误: {e}")
                self._stop_event.wait(1)
        
        logger.info("活跃度监测已停止")
    
    def start(self):
        """启动活跃度监测"""
        if not PYNPUT_AVAILABLE:
            logger.error("无法启动活跃度监测：pynput 未安装")
            return False
        
        if self._monitoring:
            logger.warning("活跃度监测已在运行")
            return True
        
        try:
            # 启动鼠标监听器
            self._mouse_listener = mouse.Listener(
                on_move=self._on_mouse_move,
                on_click=self._on_mouse_click,
                on_scroll=self._on_mouse_scroll
            )
            self._mouse_listener.start()
            
            # 启动键盘监听器
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press
            )
            self._keyboard_listener.start()
            
            # 启动监测线程
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            
            self._monitoring = True
            logger.info("活跃度监测器已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动活跃度监测失败: {e}")
            self.stop()
            return False
    
    def stop(self):
        """停止活跃度监测"""
        if not self._monitoring:
            return
        
        logger.info("正在停止活跃度监测...")
        
        # 停止监听器
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        
        # 停止监测线程
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
        
        self._monitoring = False
        logger.info("活跃度监测已停止")
    
    def is_user_active(self) -> bool:
        """
        检查用户是否活跃
        
        Returns:
            bool: True 表示用户活跃，False 表示用户闲置
        """
        idle_time = time.time() - self.last_action_time
        return idle_time < self.idle_threshold
    
    def get_idle_time(self) -> float:
        """
        获取闲置时间
        
        Returns:
            float: 闲置时间（秒）
        """
        return time.time() - self.last_action_time
    
    def get_last_action_time(self) -> datetime:
        """
        获取最后一次操作时间
        
        Returns:
            datetime: 最后一次操作时间
        """
        return datetime.fromtimestamp(self.last_action_time)
    
    @property
    def is_monitoring(self) -> bool:
        """是否正在监测"""
        return self._monitoring


class AutoPauseRecorder:
    """
    自动暂停录制器
    - 集成活跃度监测
    - 用户闲置时自动暂停录制
    - 用户活跃时自动恢复录制
    """
    
    def __init__(
        self,
        recorder,
        idle_threshold: int = 300,  # 闲置阈值（秒）
        pause_threshold: int = 60,    # 暂停阈值（秒），闲置多久后暂停录制
        resume_threshold: int = 5    # 恢复阈值（秒），活跃多久后恢复录制
    ):
        """
        初始化自动暂停录制器
        
        Args:
            recorder: 录制器实例
            idle_threshold: 闲置阈值（秒）
            pause_threshold: 暂停阈值（秒），闲置多久后暂停录制
            resume_threshold: 恢复阈值（秒），活跃多久后恢复录制
        """
        self.recorder = recorder
        self.idle_threshold = idle_threshold
        self.pause_threshold = pause_threshold
        self.resume_threshold = resume_threshold
        
        # 活跃度监测器
        self.activity_monitor = ActivityMonitor(
            idle_threshold=idle_threshold,
            on_active=self._on_user_active,
            on_idle=self._on_user_idle
        )
        
        # 状态
        self._auto_paused = False
        self._last_active_time = time.time()
        self._last_idle_time = 0.0
    
    def _on_user_active(self):
        """用户变为活跃时的回调"""
        self._last_active_time = time.time()
        
        # 如果之前自动暂停了，尝试恢复录制
        if self._auto_paused:
            logger.info("检测到用户活跃，尝试恢复录制")
            self._auto_paused = False
            if self.recorder.is_paused:
                self.recorder.resume()
    
    def _on_user_idle(self):
        """用户变为闲置时的回调"""
        self._last_idle_time = time.time()
        
        # 如果录制器正在录制，暂停录制
        if self.recorder.is_recording and not self.recorder.is_paused:
            logger.info(f"检测到用户闲置（闲置时间: {self.activity_monitor.get_idle_time():.0f}秒），暂停录制")
            self._auto_paused = True
            self.recorder.pause()
    
    def start(self):
        """启动自动暂停功能"""
        logger.info("启动自动暂停录制功能")
        return self.activity_monitor.start()
    
    def stop(self):
        """停止自动暂停功能"""
        logger.info("停止自动暂停录制功能")
        self.activity_monitor.stop()
    
    def is_auto_paused(self) -> bool:
        """是否因闲置而自动暂停"""
        return self._auto_paused
    
    def get_idle_time(self) -> float:
        """获取闲置时间"""
        return self.activity_monitor.get_idle_time()
    
    def is_user_active(self) -> bool:
        """检查用户是否活跃"""
        return self.activity_monitor.is_user_active()