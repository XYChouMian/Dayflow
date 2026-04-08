"""
活跃度感知模块 v2 - 智能闲置检测
改进点：
1. 多维度检测：键盘/鼠标 + 窗口焦点 + CPU使用率
2. 滑动窗口检测：允许一定时间的思考间歇
3. 自适应阈值：根据使用模式调整闲置判断
4. 智能判断：结合多个因素判断是否真正闲置
"""
import time
import logging
import threading
from typing import Optional, Callable, Dict, List
from datetime import datetime, timedelta
from collections import deque

try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logging.warning("pynput 未安装，活跃度监测功能将不可用")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil 未安装，CPU使用率检测将不可用")

from core.types import ActivityCard

try:
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logging.warning("win32gui 未安装，窗口焦点检测将不可用")

logger = logging.getLogger(__name__)


class SmartActivityMonitor:
    """
    智能活跃度监测器
    - 多维度检测：键盘/鼠标 + 窗口焦点 + CPU使用率
    - 滑动窗口检测：允许一定时间的思考间歇
    - 自适应阈值：根据使用模式调整闲置判断
    """
    
    def __init__(
        self,
        idle_threshold: int = 900,  # 闲置阈值（秒），默认15分钟（更宽容）
        thinking_window: int = 300,  # 思考窗口（秒），允许5分钟无操作
        min_activity_count: int = 3,  # 思考窗口内最少需要几次操作
        cpu_threshold: float = 15.0,  # CPU使用率阈值（%），超过此值认为活跃
        enable_cpu_check: bool = True,  # 是否启用CPU检测
        enable_window_check: bool = True,  # 是否启用窗口焦点检测
        on_active: Optional[Callable[[], None]] = None,
        on_idle: Optional[Callable[[], None]] = None
    ):
        """
        初始化智能活跃度监测器
        
        Args:
            idle_threshold: 闲置阈值（秒），超过此时间无操作视为闲置
            thinking_window: 思考窗口（秒），允许一定时间无操作
            min_activity_count: 思考窗口内最少需要几次操作
            cpu_threshold: CPU使用率阈值（%）
            enable_cpu_check: 是否启用CPU检测
            enable_window_check: 是否启用窗口焦点检测
            on_active: 用户变为活跃时的回调函数
            on_idle: 用户变为闲置时的回调函数
        """
        self.idle_threshold = idle_threshold
        self.thinking_window = thinking_window
        self.min_activity_count = min_activity_count
        self.cpu_threshold = cpu_threshold
        self.enable_cpu_check = enable_cpu_check and PSUTIL_AVAILABLE
        self.enable_window_check = enable_window_check and WIN32_AVAILABLE
        self.on_active = on_active
        self.on_idle = on_idle
        
        # 活动记录（滑动窗口）
        self._activity_events: deque = deque(maxlen=100)  # 保存最近100次活动
        
        # 状态
        self.last_action_time = time.time()
        self._is_active = True
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 监听器
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        
        # 窗口焦点
        self._last_window = None
        self._window_change_time = time.time()
        
        # CPU使用率
        self._last_cpu_check = time.time()
        self._cpu_usage = 0.0
        
        # 状态变化锁
        self._state_lock = threading.Lock()
        
        # 可用性检查
        self._check_availability()
    
    def _check_availability(self):
        """检查依赖是否可用"""
        if not PYNPUT_AVAILABLE:
            logger.error("pynput 未安装，活跃度监测功能将不可用")
        
        if not PSUTIL_AVAILABLE:
            logger.warning("psutil 未安装，CPU使用率检测将不可用")
        
        if not WIN32_AVAILABLE:
            logger.warning("win32gui 未安装，窗口焦点检测将不可用")
    
    def _on_mouse_move(self, x, y):
        """鼠标移动事件"""
        self._record_activity("mouse_move")
    
    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        self._record_activity("mouse_click")
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """鼠标滚动事件"""
        self._record_activity("mouse_scroll")
    
    def _on_key_press(self, key):
        """键盘按键事件"""
        self._record_activity("key_press")
    
    def _record_activity(self, activity_type: str):
        """
        记录活动事件
        
        Args:
            activity_type: 活动类型
        """
        current_time = time.time()
        
        # 记录活动
        self._activity_events.append({
            'time': current_time,
            'type': activity_type
        })
        
        # 更新最后操作时间
        self.last_action_time = current_time
        
        # 检查是否需要触发活跃回调
        with self._state_lock:
            if not self._is_active:
                self._is_active = True
                logger.info(f"用户变为活跃状态（活动类型: {activity_type}）")
                if self.on_active:
                    try:
                        self.on_active()
                    except Exception as e:
                        logger.error(f"活跃回调执行失败: {e}")
    
    def _check_window_focus(self) -> bool:
        """
        检查窗口焦点变化
        
        Returns:
            bool: 是否检测到窗口焦点变化
        """
        if not self.enable_window_check:
            return False
        
        try:
            current_window = win32gui.GetForegroundWindow()
            
            if current_window != self._last_window:
                # 窗口焦点变化
                if self._last_window is not None:
                    logger.debug(f"检测到窗口焦点变化")
                    self._record_activity("window_focus_change")
                
                self._last_window = current_window
                self._window_change_time = time.time()
                return True
        except Exception as e:
            logger.debug(f"窗口焦点检测失败: {e}")
        
        return False
    
    def _check_cpu_usage(self) -> float:
        """
        检查CPU使用率
        
        Returns:
            float: CPU使用率（%）
        """
        if not self.enable_cpu_check:
            return 0.0
        
        try:
            # 每10秒检查一次CPU使用率
            if time.time() - self._last_cpu_check >= 10:
                self._cpu_usage = psutil.cpu_percent(interval=1)
                self._last_cpu_check = time.time()
                
                logger.debug(f"CPU使用率: {self._cpu_usage:.1f}%")
                
                # 如果CPU使用率高，记录为活跃
                if self._cpu_usage >= self.cpu_threshold:
                    self._record_activity("high_cpu_usage")
            
            return self._cpu_usage
        except Exception as e:
            logger.debug(f"CPU使用率检测失败: {e}")
            return 0.0
    
    def _count_recent_activities(self, window_seconds: int) -> int:
        """
        统计最近一段时间内的活动次数
        
        Args:
            window_seconds: 时间窗口（秒）
        
        Returns:
            int: 活动次数
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        count = 0
        for event in self._activity_events:
            if event['time'] >= cutoff_time:
                count += 1
        
        return count
    
    def _is_thinking(self) -> bool:
        """
        判断用户是否在思考（基于滑动窗口）
        
        Returns:
            bool: 是否在思考
        """
        # 统计思考窗口内的活动次数
        activity_count = self._count_recent_activities(self.thinking_window)
        
        # 如果活动次数达到阈值，说明用户在工作（可能是在思考）
        is_thinking = activity_count >= self.min_activity_count
        
        if is_thinking:
            logger.debug(f"检测到思考状态（{self.thinking_window}秒内有{activity_count}次操作）")
        
        return is_thinking
    
    def _is_truly_idle(self) -> bool:
        """
        判断用户是否真正闲置（结合多种因素）
        
        Returns:
            bool: 是否真正闲置
        """
        idle_time = time.time() - self.last_action_time
        
        # 如果闲置时间较短，不算真正闲置
        if idle_time < self.idle_threshold:
            return False
        
        # 超过闲置阈值，检查是否在思考
        # 如果在思考，不算闲置
        if self._is_thinking():
            logger.debug(f"闲置时间超过阈值（{idle_time:.0f}秒），但在思考窗口内有活动")
            return False
        
        # 超过闲置阈值且不在思考，判定为闲置
        logger.debug(f"判定为真正闲置（闲置时间: {idle_time:.0f}秒）")
        return True
    
    def _monitor_loop(self):
        """监测循环"""
        logger.info(f"智能活跃度监测已启动")
        logger.info(f"  - 闲置阈值: {self.idle_threshold}秒")
        logger.info(f"  - 思考窗口: {self.thinking_window}秒")
        logger.info(f"  - 最少活动次数: {self.min_activity_count}")
        logger.info(f"  - CPU阈值: {self.cpu_threshold}%")
        logger.info(f"  - CPU检测: {'启用' if self.enable_cpu_check else '禁用'}")
        logger.info(f"  - 窗口检测: {'启用' if self.enable_window_check else '禁用'}")
        
        while not self._stop_event.is_set():
            try:
                # 检查窗口焦点变化
                if self.enable_window_check:
                    self._check_window_focus()
                
                # 检查CPU使用率
                if self.enable_cpu_check:
                    self._check_cpu_usage()
                
                # 判断是否真正闲置
                is_idle = self._is_truly_idle()
                idle_time = time.time() - self.last_action_time
                recent_activities = self._count_recent_activities(self.thinking_window)
                
                # 定期输出状态日志
                logger.debug(f"监测状态 - 闲置时间: {idle_time:.0f}秒, 近期活动: {recent_activities}次, 当前状态: {'闲置' if is_idle else '活跃'}")
                
                # 检查是否需要触发闲置回调
                with self._state_lock:
                    if is_idle and self._is_active:
                        self._is_active = False
                        idle_time = time.time() - self.last_action_time
                        logger.info(f"用户变为闲置状态（闲置时间: {idle_time:.0f}秒，近期活动: {recent_activities}次）")
                        if self.on_idle:
                            try:
                                self.on_idle()
                            except Exception as e:
                                logger.error(f"闲置回调执行失败: {e}")
                    
                    elif not is_idle and not self._is_active:
                        self._is_active = True
                        logger.info(f"用户变为活跃状态（闲置时间: {idle_time:.0f}秒，近期活动: {recent_activities}次）")
                        if self.on_active:
                            try:
                                self.on_active()
                            except Exception as e:
                                logger.error(f"活跃回调执行失败: {e}")
                
                # 等待一段时间再检查
                # 根据闲置阈值动态调整检查间隔，确保及时检测闲置
                check_interval = min(5, self.idle_threshold / 10)  # 最多5秒，或闲置阈值的1/10
                self._stop_event.wait(check_interval)
                
            except Exception as e:
                logger.error(f"活跃度监测错误: {e}")
                self._stop_event.wait(1)
        
        logger.info("智能活跃度监测已停止")
    
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
            logger.info("智能活跃度监测器已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动活跃度监测失败: {e}")
            self.stop()
            return False
    
    def stop(self):
        """停止活跃度监测"""
        if not self._monitoring:
            return
        
        logger.info("正在停止智能活跃度监测...")
        
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
        logger.info("智能活跃度监测已停止")
    
    def is_user_active(self) -> bool:
        """
        检查用户是否活跃
        
        Returns:
            bool: True 表示用户活跃，False 表示用户闲置
        """
        return self._is_active and not self._is_truly_idle()
    
    def get_idle_time(self) -> float:
        """
        获取闲置时间
        
        Returns:
            float: 闲置时间（秒）
        """
        return time.time() - self.last_action_time
    
    def get_activity_count(self, window_seconds: int = 300) -> int:
        """
        获取最近一段时间内的活动次数
        
        Args:
            window_seconds: 时间窗口（秒）
        
        Returns:
            int: 活动次数
        """
        return self._count_recent_activities(window_seconds)
    
    def get_last_action_time(self) -> datetime:
        """
        获取最后一次操作时间
        
        Returns:
            datetime: 最后一次操作时间
        """
        return datetime.fromtimestamp(self.last_action_time)
    
    def get_status(self) -> Dict:
        """
        获取监测状态信息
        
        Returns:
            Dict: 状态信息
        """
        return {
            'is_active': self._is_active,
            'is_thinking': self._is_thinking(),
            'idle_time': self.get_idle_time(),
            'activity_count': self.get_activity_count(),
            'cpu_usage': self._cpu_usage,
            'enable_cpu_check': self.enable_cpu_check,
            'enable_window_check': self.enable_window_check
        }
    
    @property
    def is_monitoring(self) -> bool:
        """是否正在监测"""
        return self._monitoring


class SmartAutoPauseRecorder:
    """
    智能自动暂停录制器 - 新版本
    
    停止逻辑：
    - 每分钟进行一次持续10秒的检测
    - 如果10秒内用户有操作，说明现在用户正在工作，等待1分钟后进行下一次
    - 否则，持续检测用户是否有操作，如果持续50秒用户没有操作，则录屏停止（从此刻开始休息）
    - 如果30秒内用户有操作，则不停止
    
    开始逻辑：
    - 保持检测键鼠操作
    - 当用户有操作时，记录开始操作的时间并停止检测，等待30秒后，开始检测，持续30秒
    - 如果期间再次检测到用户操作，则说明用户开始工作，录屏开始
    - 否则录屏不开始，等待10秒钟后进入下一次检测
    """
    
    def __init__(
        self,
        recorder,
        stop_check_interval: int = 60,      # 停止检测间隔（秒）
        stop_detection_duration: int = 30,  # 停止检测持续时间（秒）
        resume_wait_duration: int = 30,     # 恢复等待持续时间（秒）
        resume_detection_duration: int = 30,  # 恢复检测持续时间（秒）
        storage = None                      # 数据存储
    ):
        """
        初始化智能自动暂停录制器
        
        Args:
            recorder: 录制器实例
            stop_check_interval: 停止检测间隔（秒），默认60秒
            stop_detection_duration: 停止检测持续时间（秒），默认30秒
            resume_wait_duration: 恢复等待持续时间（秒），默认30秒
            resume_detection_duration: 恢复检测持续时间（秒），默认30秒
            storage: 数据存储实例
        """
        self.recorder = recorder
        self.stop_check_interval = stop_check_interval
        self.stop_detection_duration = stop_detection_duration
        self.resume_wait_duration = resume_wait_duration
        self.resume_detection_duration = resume_detection_duration
        
        # 监听器
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        
        # 活动记录
        self._last_activity_time = 0.0
        self._activity_detected_in_window = False
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 状态机状态
        # IDLE: 初始状态
        # STOP_10S_CHECK: 每60秒进入一次，进行10秒检测
        # STOP_WAIT_60: 10秒内有操作，等待60秒后再次检测
        # STOP_MONITORING: 10秒内无操作，持续监测，30秒内有操作不停止，50秒无操作停止
        # STOPPED: 录制停止状态
        # RESUME_MONITORING: 监测键鼠操作
        # RESUME_WAIT_30: 检测到操作后等待30秒
        # RESUME_DETECT_30: 检测30秒，期间有操作开始录制
        # RESUME_WAIT_10: 30秒内无操作，等待10秒后再次监测
        self._state = "IDLE"
        self._state_start_time = 0.0
        self._auto_paused = False
        
        # 休息卡片记录
        self._rest_start_time: Optional[datetime] = None
        
        # 活动锁
        self._activity_lock = threading.Lock()
        
        # 数据存储
        self._storage = storage
    
    def _on_mouse_move(self, x, y):
        """鼠标移动事件"""
        self._record_activity("mouse_move")
    
    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        self._record_activity("mouse_click")
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """鼠标滚动事件"""
        self._record_activity("mouse_scroll")
    
    def _on_key_press(self, key):
        """键盘按键事件"""
        self._record_activity("key_press")
    
    def _record_activity(self, activity_type: str):
        """记录活动事件"""
        current_time = time.time()
        
        with self._activity_lock:
            self._last_activity_time = current_time
            self._activity_detected_in_window = True
            
        logger.debug(f"检测到活动: {activity_type}")
    
    def _check_recent_activity(self, window_seconds: float) -> bool:
        """检查最近一段时间内是否有活动"""
        current_time = time.time()
        with self._activity_lock:
            if self._last_activity_time > 0 and (current_time - self._last_activity_time) <= window_seconds:
                return True
        return False
    
    def _reset_activity_window(self):
        """重置活动检测窗口"""
        with self._activity_lock:
            self._activity_detected_in_window = False
    
    def _state_idle(self):
        """IDLE状态处理"""
        current_time = time.time()
        
        # 进入停止检测状态
        logger.info("进入停止检测状态")
        self._state = "STOP_10S_CHECK"
        self._state_start_time = current_time
        self._reset_activity_window()
    
    def _state_stop_10s_check(self):
        """STOP_10S_CHECK状态处理：进行10秒检测"""
        current_time = time.time()
        elapsed = current_time - self._state_start_time
        
        # 在10秒检测窗口内
        if elapsed <= 10:
            # 检查10秒内是否有活动
            if self._check_recent_activity(10):
                logger.info(f"10秒检测窗口内检测到活动，用户正在工作，等待60秒后再次检测")
                self._state = "STOP_WAIT_60"
                self._state_start_time = current_time
                return
        else:
            # 10秒内无活动，进入持续监测状态
            logger.info("10秒检测窗口内无活动，进入持续监测状态")
            self._state = "STOP_MONITORING"
            self._state_start_time = current_time
            self._reset_activity_window()
            return
        
        # 继续检测
        self._stop_event.wait(0.1)
    
    def _state_stop_wait_60(self):
        """STOP_WAIT_60状态处理：等待60秒后再次进行10秒检测"""
        current_time = time.time()
        elapsed = current_time - self._state_start_time
        
        # 等待60秒后再次检测
        if elapsed >= self.stop_check_interval:
            logger.info("60秒等待结束，再次进行10秒检测")
            self._state = "STOP_10S_CHECK"
            self._state_start_time = current_time
            self._reset_activity_window()
            return
        
        self._stop_event.wait(1)
    
    def _state_stop_monitoring(self):
        """STOP_MONITORING状态处理：持续监测"""
        current_time = time.time()
        elapsed = current_time - self._state_start_time
        
        # 检查是否有活动
        if elapsed <= 30:
            # 在30秒检测窗口内，如果有活动则不停止
            if self._check_recent_activity(1):
                logger.info(f"持续监测窗口（{elapsed:.0f}秒）内检测到活动，用户仍在工作，等待60秒后再次检测")
                self._state = "STOP_WAIT_60"
                self._state_start_time = current_time
                return
        else:
            # 超过30秒，检查是否达到50秒无操作
            if elapsed >= 50:
                logger.info(f"持续监测窗口（{elapsed:.0f}秒）内无活动，停止录制")
                self._pause_recording()
                self._state = "STOPPED"
                self._state_start_time = current_time
                return
        
        self._stop_event.wait(0.1)
    
    def _state_stopped(self):
        """STOPPED状态处理：录制停止状态，进入恢复监测"""
        current_time = time.time()
        
        # 进入恢复监测状态
        logger.info("进入恢复监测状态")
        self._state = "RESUME_MONITORING"
        self._state_start_time = current_time
        self._reset_activity_window()
    
    def _state_resume_monitoring(self):
        """RESUME_MONITORING状态处理：监测键鼠操作"""
        current_time = time.time()
        
        # 检测是否有活动
        if self._check_recent_activity(1):
            logger.info("检测到键鼠操作，等待30秒后开始检测")
            self._state = "RESUME_WAIT_30"
            self._state_start_time = current_time
            self._reset_activity_window()
            return
        
        self._stop_event.wait(0.1)
    
    def _state_resume_wait_30(self):
        """RESUME_WAIT_30状态处理：等待30秒后开始检测"""
        current_time = time.time()
        elapsed = current_time - self._state_start_time
        
        # 等待30秒
        if elapsed >= self.resume_wait_duration:
            logger.info("30秒等待结束，开始30秒检测")
            self._state = "RESUME_DETECT_30"
            self._state_start_time = current_time
            self._reset_activity_window()
            return
        
        self._stop_event.wait(1)
    
    def _state_resume_detect_30(self):
        """RESUME_DETECT_30状态处理：检测30秒，期间有操作开始录制"""
        current_time = time.time()
        elapsed = current_time - self._state_start_time
        
        # 在30秒检测窗口内
        if elapsed <= self.resume_detection_duration:
            # 检测是否有活动
            if self._check_recent_activity(1):
                logger.info(f"检测窗口（{elapsed:.0f}秒）内检测到活动，用户开始工作，开始录制")
                self._resume_recording()
                self._state = "IDLE"
                self._state_start_time = current_time
                return
        else:
            # 30秒内无活动，等待10秒后再次监测
            logger.info("30秒检测窗口内无活动，等待10秒后再次监测")
            self._state = "RESUME_WAIT_10"
            self._state_start_time = current_time
            return
        
        self._stop_event.wait(0.1)
    
    def _state_resume_wait_10(self):
        """RESUME_WAIT_10状态处理：等待10秒后再次监测"""
        current_time = time.time()
        elapsed = current_time - self._state_start_time
        
        # 等待10秒
        if elapsed >= 10:
            logger.info("10秒等待结束，再次监测")
            self._state = "RESUME_MONITORING"
            self._state_start_time = current_time
            self._reset_activity_window()
            return
        
        self._stop_event.wait(1)
    
    def _pause_recording(self):
        """暂停录制"""
        if self.recorder.is_recording and not self.recorder.is_paused:
            logger.info("自动暂停录制")
            self.recorder.pause()
            self._auto_paused = True
            self._rest_start_time = datetime.now()
        else:
            logger.info(f"录制器状态: 录制={self.recorder.is_recording}, 暂停={self.recorder.is_paused}, 不执行暂停")
    
    def _resume_recording(self):
        """恢复录制"""
        if self.recorder.is_paused:
            logger.info("自动恢复录制")
            self.recorder.resume()
            self._auto_paused = False
            
            # 创建休息卡片
            if self._rest_start_time:
                rest_end_time = datetime.now()
                rest_duration = (rest_end_time - self._rest_start_time).total_seconds() / 60  # 分钟
                
                if rest_duration >= 1:  # 只记录休息时间超过1分钟的
                    # 回顾过去2分钟内的所有卡片
                    recent_cards = self._storage.get_recent_cards(limit=20)
                    two_minutes_ago = rest_end_time - timedelta(minutes=2)
                    
                    # 找到过去2分钟内的卡片
                    cards_in_last_2min = [
                        card for card in recent_cards
                        if card.end_time and card.end_time >= two_minutes_ago
                    ]
                    
                    if cards_in_last_2min:
                        logger.info(f"过去2分钟内发现 {len(cards_in_last_2min)} 张卡片")
                        
                        # 检查是否有休息卡片
                        rest_cards_in_range = [card for card in cards_in_last_2min if card.category == "休息"]
                        
                        if rest_cards_in_range:
                            # 合并休息卡片：找到最早的休息卡片
                            earliest_rest_card = min(rest_cards_in_range, key=lambda c: c.start_time)
                            merged_start_time = min(earliest_rest_card.start_time, self._rest_start_time)
                            merged_duration = (rest_end_time - merged_start_time).total_seconds() / 60
                            
                            # 删除旧的休息卡片
                            for card in rest_cards_in_range:
                                self._storage.delete_card(card.id)
                                logger.info(f"删除旧休息卡片 (ID: {card.id})")
                            
                            # 创建合并后的休息卡片
                            rest_card = ActivityCard(
                                category="休息",
                                title="休息时间",
                                summary=f"用户休息了 {merged_duration:.1f} 分钟",
                                start_time=merged_start_time,
                                app_sites=[],
                                distractions=[],
                                productivity_score=0.0
                            )
                            rest_card._next_card_start_time = rest_end_time
                            
                            if self._storage:
                                try:
                                    self._storage.save_card(rest_card)
                                    logger.info(f"已创建合并后的休息卡片: {merged_start_time.strftime('%H:%M:%S')} - {rest_end_time.strftime('%H:%M:%S')} ({merged_duration:.1f}分钟)")
                                except Exception as e:
                                    logger.error(f"保存休息卡片失败: {e}")
                        else:
                            # 没有休息卡片，检查是否有其他卡片（视为休息时的误触）
                            non_rest_cards = [card for card in cards_in_last_2min if card.category != "休息"]
                            if non_rest_cards:
                                # 删除这些误触卡片
                                for card in non_rest_cards:
                                    self._storage.delete_card(card.id)
                                    logger.info(f"删除休息时的误触卡片 (ID: {card.id}, 类别: {card.category})")
                            
                            # 创建新的休息卡片
                            rest_card = ActivityCard(
                                category="休息",
                                title="休息时间",
                                summary=f"用户休息了 {rest_duration:.1f} 分钟",
                                start_time=self._rest_start_time,
                                app_sites=[],
                                distractions=[],
                                productivity_score=0.0
                            )
                            rest_card._next_card_start_time = rest_end_time
                            
                            if self._storage:
                                try:
                                    self._storage.save_card(rest_card)
                                    logger.info(f"已创建休息卡片: {self._rest_start_time.strftime('%H:%M:%S')} - {rest_end_time.strftime('%H:%M:%S')} ({rest_duration:.1f}分钟)")
                                except Exception as e:
                                    logger.error(f"保存休息卡片失败: {e}")
                    else:
                        # 过去2分钟内没有卡片，直接创建休息卡片
                        rest_card = ActivityCard(
                            category="休息",
                            title="休息时间",
                            summary=f"用户休息了 {rest_duration:.1f} 分钟",
                            start_time=self._rest_start_time,
                            app_sites=[],
                            distractions=[],
                            productivity_score=0.0
                        )
                        rest_card._next_card_start_time = rest_end_time
                        
                        if self._storage:
                            try:
                                self._storage.save_card(rest_card)
                                logger.info(f"已创建休息卡片: {self._rest_start_time.strftime('%H:%M:%S')} - {rest_end_time.strftime('%H:%M:%S')} ({rest_duration:.1f}分钟)")
                            except Exception as e:
                                logger.error(f"保存休息卡片失败: {e}")
                else:
                    logger.info(f"休息时间不足1分钟 ({rest_duration:.1f}分钟)，不创建卡片")
                
                self._rest_start_time = None
        else:
            logger.info("录制器未暂停，不执行恢复")
    
    def _monitor_loop(self):
        """监测主循环"""
        logger.info("智能自动暂停录制器已启动")
        logger.info(f"  - 停止检测间隔: {self.stop_check_interval}秒")
        logger.info(f"  - 停止检测持续时间: {self.stop_detection_duration}秒")
        logger.info(f"  - 恢复等待持续时间: {self.resume_wait_duration}秒")
        logger.info(f"  - 恢复检测持续时间: {self.resume_detection_duration}秒")
        logger.info(f"  - 初始状态: {self._state}")
        
        self._state = "IDLE"
        self._state_start_time = time.time()
        
        while not self._stop_event.is_set():
            try:
                if self._state == "IDLE":
                    self._state_idle()
                elif self._state == "STOP_10S_CHECK":
                    self._state_stop_10s_check()
                elif self._state == "STOP_WAIT_60":
                    self._state_stop_wait_60()
                elif self._state == "STOP_MONITORING":
                    self._state_stop_monitoring()
                elif self._state == "STOPPED":
                    self._state_stopped()
                elif self._state == "RESUME_MONITORING":
                    self._state_resume_monitoring()
                elif self._state == "RESUME_WAIT_30":
                    self._state_resume_wait_30()
                elif self._state == "RESUME_DETECT_30":
                    self._state_resume_detect_30()
                elif self._state == "RESUME_WAIT_10":
                    self._state_resume_wait_10()
                else:
                    logger.warning(f"未知状态: {self._state}")
                    self._state = "IDLE"
                    self._state_start_time = time.time()
                
            except Exception as e:
                logger.error(f"监测循环错误: {e}")
                self._stop_event.wait(1)
        
        logger.info("智能自动暂停录制器已停止")
    
    def start(self):
        """启动智能自动暂停功能"""
        if not PYNPUT_AVAILABLE:
            logger.error("无法启动自动暂停：pynput 未安装")
            return False
        
        if self._monitoring:
            logger.warning("自动暂停已在运行")
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
            logger.info("智能自动暂停录制器已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动自动暂停失败: {e}")
            self.stop()
            return False
    
    def stop(self):
        """停止智能自动暂停功能"""
        if not self._monitoring:
            return
        
        logger.info("正在停止智能自动暂停录制器...")
        
        # 如果处于休息状态，创建休息卡片
        if self._rest_start_time:
            rest_end_time = datetime.now()
            rest_duration = (rest_end_time - self._rest_start_time).total_seconds() / 60  # 分钟
            
            if rest_duration >= 1:  # 只记录休息时间超过1分钟的
                # 回顾过去2分钟内的所有卡片
                recent_cards = self._storage.get_recent_cards(limit=20)
                two_minutes_ago = rest_end_time - timedelta(minutes=2)
                
                # 找到过去2分钟内的卡片
                cards_in_last_2min = [
                    card for card in recent_cards
                    if card.end_time and card.end_time >= two_minutes_ago
                ]
                
                if cards_in_last_2min:
                    logger.info(f"过去2分钟内发现 {len(cards_in_last_2min)} 张卡片")
                    
                    # 检查是否有休息卡片
                    rest_cards_in_range = [card for card in cards_in_last_2min if card.category == "休息"]
                    
                    if rest_cards_in_range:
                        # 合并休息卡片：找到最早的休息卡片
                        earliest_rest_card = min(rest_cards_in_range, key=lambda c: c.start_time)
                        merged_start_time = min(earliest_rest_card.start_time, self._rest_start_time)
                        merged_duration = (rest_end_time - merged_start_time).total_seconds() / 60
                        
                        # 删除旧的休息卡片
                        for card in rest_cards_in_range:
                            self._storage.delete_card(card.id)
                            logger.info(f"删除旧休息卡片 (ID: {card.id})")
                        
                        # 创建合并后的休息卡片
                        rest_card = ActivityCard(
                            category="休息",
                            title="休息时间",
                            summary=f"用户休息了 {merged_duration:.1f} 分钟",
                            start_time=merged_start_time,
                            app_sites=[],
                            distractions=[],
                            productivity_score=0.0
                        )
                        rest_card._next_card_start_time = rest_end_time
                        
                        if self._storage:
                            try:
                                self._storage.save_card(rest_card)
                                logger.info(f"已创建合并后的休息卡片: {merged_start_time.strftime('%H:%M:%S')} - {rest_end_time.strftime('%H:%M:%S')} ({merged_duration:.1f}分钟)")
                            except Exception as e:
                                logger.error(f"保存休息卡片失败: {e}")
                    else:
                        # 没有休息卡片，检查是否有其他卡片（视为休息时的误触）
                        non_rest_cards = [card for card in cards_in_last_2min if card.category != "休息"]
                        if non_rest_cards:
                            # 删除这些误触卡片
                            for card in non_rest_cards:
                                self._storage.delete_card(card.id)
                                logger.info(f"删除休息时的误触卡片 (ID: {card.id}, 类别: {card.category})")
                        
                        # 创建新的休息卡片
                        rest_card = ActivityCard(
                            category="休息",
                            title="休息时间",
                            summary=f"用户休息了 {rest_duration:.1f} 分钟",
                            start_time=self._rest_start_time,
                            app_sites=[],
                            distractions=[],
                            productivity_score=0.0
                        )
                        rest_card._next_card_start_time = rest_end_time
                        
                        if self._storage:
                            try:
                                self._storage.save_card(rest_card)
                                logger.info(f"已创建休息卡片: {self._rest_start_time.strftime('%H:%M:%S')} - {rest_end_time.strftime('%H:%M:%S')} ({rest_duration:.1f}分钟)")
                            except Exception as e:
                                logger.error(f"保存休息卡片失败: {e}")
                else:
                    # 过去2分钟内没有卡片，直接创建休息卡片
                    rest_card = ActivityCard(
                        category="休息",
                        title="休息时间",
                        summary=f"用户休息了 {rest_duration:.1f} 分钟",
                        start_time=self._rest_start_time,
                        app_sites=[],
                        distractions=[],
                        productivity_score=0.0
                    )
                    rest_card._next_card_start_time = rest_end_time
                    
                    if self._storage:
                        try:
                            self._storage.save_card(rest_card)
                            logger.info(f"已创建休息卡片: {self._rest_start_time.strftime('%H:%M:%S')} - {rest_end_time.strftime('%H:%M:%S')} ({rest_duration:.1f}分钟)")
                        except Exception as e:
                            logger.error(f"保存休息卡片失败: {e}")
            else:
                logger.info(f"休息时间不足1分钟 ({rest_duration:.1f}分钟)，不创建卡片")
            
            self._rest_start_time = None
        
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
        logger.info("智能自动暂停录制器已停止")
    
    def is_auto_paused(self) -> bool:
        """是否因闲置而自动暂停"""
        return self._auto_paused
    
    def get_idle_time(self) -> float:
        """获取闲置时间"""
        current_time = time.time()
        with self._activity_lock:
            if self._last_activity_time > 0:
                return current_time - self._last_activity_time
        return 0.0
    
    def is_user_active(self) -> bool:
        """检查用户是否活跃"""
        return not self._auto_paused
    
    def get_status(self) -> Dict:
        """
        获取状态信息
        
        Returns:
            Dict: 状态信息
        """
        return {
            'state': self._state,
            'auto_paused': self._auto_paused,
            'idle_time': self.get_idle_time(),
            'monitoring': self._monitoring
        }
