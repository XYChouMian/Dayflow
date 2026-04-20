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

def format_rest_duration(minutes: float) -> str:
    if minutes >= 60:
        hours = int(minutes // 60)
        remaining_minutes = int(minutes % 60)//1
        if remaining_minutes > 0:
            return f"{hours}小时{remaining_minutes}分钟"
        else:
            return f"{hours}小时"
    else:
        return f"{minutes:.1f}分钟"


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
        storage = None,                     # 数据存储
        on_stop_recording: Optional[Callable[[], None]] = None,  # 停止录制回调函数
        on_resume_recording: Optional[Callable[[], None]] = None  # 恢复录制回调函数
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
            on_stop_recording: 停止录制回调函数
            on_resume_recording: 恢复录制回调函数
        """
        self.recorder = recorder
        self.stop_check_interval = stop_check_interval
        self.stop_detection_duration = stop_detection_duration
        self.resume_wait_duration = resume_wait_duration
        self.resume_detection_duration = resume_detection_duration
        self._on_stop_recording = on_stop_recording  # 停止录制回调
        self._on_resume_recording = on_resume_recording  # 恢复录制回调
        
        # 监听器
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        
        # 活动记录
        self._last_activity_time = 0.0
        self._activity_events: deque = deque(maxlen=100)  # 保存最近100次活动
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 休息卡片更新线程
        self._rest_card_update_thread: Optional[threading.Thread] = None
        self._rest_card_update_stop_event = threading.Event()
        self._current_rest_card_id: Optional[int] = None
        
        # 状态机状态
        # IDLE: 初始状态
        # WAIT_FOR_CHECK: 等待60秒后开始检测
        # CHECK_10S: 进行10秒检测
        # CHECK_60S: 进行60秒二次检测
        # STOPPED: 录制停止状态，正在生成休息卡片
        # REST_MONITORING: 持续检测用户是否操作
        # REST_WAIT_30: 检测到操作后等待30秒
        # REST_DETECT_90: 进行90秒检测，确认用户是否结束休息
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
            self._activity_events.append({
                "time": current_time,
                "type": activity_type
            })
            
        logger.debug(f"检测到活动: {activity_type}")
    
    def _check_activity_since(self, start_time: float) -> bool:
        """检查从指定时间开始到现在是否有活动"""
        current_time = time.time()
        
        with self._activity_lock:
            for event in self._activity_events:
                if event['time'] >= start_time and event['time'] <= current_time:
                    return True
        return False
    
    def _state_idle(self):
        """IDLE状态处理：进入等待检测状态"""
        current_time = time.time()
        
        if self._stop_event.is_set():
            logger.info("停止事件已设置，退出IDLE状态")
            return
        
        logger.info("进入等待检测状态")
        self._state = "WAIT_FOR_CHECK"
        self._state_start_time = current_time
    
    def _state_wait_for_check(self):
        """WAIT_FOR_CHECK状态处理：等待60秒后开始10秒检测"""
        current_time = time.time()
        
        if self._stop_event.is_set():
            logger.info("停止事件已设置，退出WAIT_FOR_CHECK状态")
            return
        
        elapsed = current_time - self._state_start_time
        
        if elapsed >= 60:
            logger.info("60秒等待结束，开始10秒检测")
            self._state = "CHECK_10S"
            self._state_start_time = current_time
            return
        
        self._stop_event.wait(1)
    
    def _state_check_10s(self):
        """CHECK_10S状态处理：进行10秒检测"""
        current_time = time.time()
        
        if self._stop_event.is_set():
            logger.info("停止事件已设置，退出CHECK_10S状态")
            return
        
        elapsed = current_time - self._state_start_time
        
        if elapsed <= 10:
            if self._check_activity_since(self._state_start_time):
                logger.info(f"10秒检测窗口内检测到活动，用户正在工作，等待下次检测")
                self._state = "WAIT_FOR_CHECK"
                self._state_start_time = current_time
                return
        else:
            logger.info("10秒检测窗口内无活动，进入60秒二次检测")
            self._state = "CHECK_60S"
            self._state_start_time = current_time
            return
        
        self._stop_event.wait(0.1)
    
    def _state_check_60s(self):
        """CHECK_60S状态处理：进行60秒二次检测"""
        current_time = time.time()
        
        if self._stop_event.is_set():
            logger.info("停止事件已设置，退出CHECK_60S状态")
            return
        
        elapsed = current_time - self._state_start_time
        
        if self._check_activity_since(self._state_start_time):
            logger.info("60秒二次检测期间检测到活动，用户正在工作，回到等待检测状态")
            self._state = "WAIT_FOR_CHECK"
            self._state_start_time = current_time
            return
        
        if elapsed >= 60:
            logger.info("60秒二次检测期间无活动，判定用户正在休息，停止录制")
            
            # 调用停止录制回调（停止录制并分析视频），获取停止时间
            recording_stop_time = None
            if self._on_stop_recording:
                logger.info("调用停止录制回调，停止录制并分析视频")
                try:
                    recording_stop_time = self._on_stop_recording()
                except Exception as e:
                    logger.error(f"停止录制回调执行失败: {e}")
            
            # 记录休息开始时间（使用录屏实际停止时间）
            self._rest_start_time = recording_stop_time if recording_stop_time else datetime.now()
            logger.info(f"记录休息开始时间: {self._rest_start_time.strftime('%H:%M:%S')}")
            
            self._state = "STOPPED"
            self._state_start_time = current_time
            return
        
        self._stop_event.wait(0.1)
    
    def _state_stopped(self):
        """STOPPED状态处理：录制停止状态，创建休息卡片并启动更新线程"""
        
        if self._stop_event.is_set():
            logger.info("停止事件已设置，跳过STOPPED状态处理")
            return
        
        logger.info("创建休息卡片并启动更新线程")
        
        rest_card = self._create_rest_card()
        if rest_card:
            self._start_rest_card_update_thread()
        
        self._auto_paused = True
        logger.info("设置自动暂停状态为 True，UI 应显示'检测到用户正在休息'")
        
        self._state = "REST_MONITORING"
        self._state_start_time = time.time()
    
    def _state_rest_monitoring(self):
        """REST_MONITORING状态处理：持续检测用户是否操作"""
        current_time = time.time()
        
        if self._stop_event.is_set():
            logger.info("停止事件已设置，退出REST_MONITORING状态")
            return
        
        if self._check_activity_since(self._state_start_time):
            logger.info("检测到用户操作，可能结束休息，等待30秒")
            self._state = "REST_WAIT_30"
            self._state_start_time = current_time
            return
        
        self._stop_event.wait(0.1)
    
    def _state_rest_wait_30(self):
        """REST_WAIT_30状态处理：等待30秒后开始90秒检测"""
        if self._stop_event.is_set():
            logger.info("停止事件已设置，退出REST_WAIT_30状态")
            return
        
        current_time = time.time()
        elapsed = current_time - self._state_start_time
        
        if elapsed >= 30:
            logger.info("30秒等待结束，开始90秒检测")
            self._state = "REST_DETECT_90"
            self._state_start_time = current_time
            logger.info(f"状态转换: REST_WAIT_30 -> REST_DETECT_90 (elapsed={elapsed:.1f}秒)")
            return
            
        logger.debug(f"REST_WAIT_30状态: 已等待{elapsed:.1f}秒，还需{30-elapsed:.1f}秒")
        self._stop_event.wait(1)
    
    def _state_rest_detect_90(self):
        """REST_DETECT_90状态处理：进行90秒检测，确认用户是否结束休息"""
        current_time = time.time()
        
        if self._stop_event.is_set():
            logger.info("停止事件已设置，退出REST_DETECT_90状态")
            return
        
        elapsed = current_time - self._state_start_time
        
        if self._check_activity_since(self._state_start_time):
            logger.info("90秒检测期间检测到用户操作，判定用户结束休息")
            
            # 调用恢复录制回调（重新启动录制），获取录制开始时间
            recording_start_time = None
            if self._on_resume_recording:
                logger.info("调用恢复录制回调，重新启动录制")
                try:
                    recording_start_time = self._on_resume_recording()
                except Exception as e:
                    logger.error(f"恢复录制回调执行失败: {e}")
            
            # 停止休息卡片更新线程
            self._stop_rest_card_update_thread()
            
            # 更新休息卡片结束时间（使用录制实际开始时间）
            self._update_rest_card_end_time(recording_start_time)
            
            self._auto_paused = False
            logger.info("设置自动暂停状态为 False，UI 应显示'录制中'")
            
            self._state = "IDLE"
            self._state_start_time = current_time
            return
        
        if elapsed >= 90:
            logger.info("90秒检测期间无操作，判定为用户误触，回到休息监测状态")
            self._state = "REST_MONITORING"
            self._state_start_time = current_time
            return
        
        self._stop_event.wait(0.1)
    
    def _create_rest_card(self):
        """创建休息卡片"""
        if not self._rest_start_time:
            return None
            
        current_time = datetime.now()
        rest_duration = (current_time - self._rest_start_time).total_seconds() / 60  # 分钟
        
        # 获取上一张卡片，验证时间连续性
        previous_card = None
        if self._storage:
            previous_cards = self._storage.get_cards_before_time(
                self._rest_start_time,
                limit=1
            )
            if previous_cards:
                previous_card = previous_cards[0]
        
        # 如果上一张卡片存在，检查其结束时间是否晚于休息开始时间
        if previous_card and previous_card._next_card_start_time:
            if previous_card._next_card_start_time > self._rest_start_time:
                # 上一张卡片的结束时间晚于休息开始时间，存在时间重叠
                logger.warning(
                    f"休息卡片与上一张活动卡片时间重叠：上一张卡片 ({previous_card.title}) 的结束时间 {previous_card._next_card_start_time} "
                    f"晚于休息开始时间 {self._rest_start_time}，修正上一张卡片的结束时间"
                )
                
                # 更新上一张卡片的结束时间
                old_end_time = previous_card._next_card_start_time
                previous_card._next_card_start_time = self._rest_start_time
                
                # 计算修正后的持续时间
                corrected_duration = (previous_card._next_card_start_time - previous_card.start_time).total_seconds() / 60
                logger.info(
                    f"已修正上一张卡片 {previous_card.id} ({previous_card.title}) 的结束时间: "
                    f"{old_end_time} -> {previous_card._next_card_start_time} "
                    f"(持续时间: {corrected_duration:.1f}分钟)"
                )
                
                # 更新数据库
                if previous_card.id:
                    success = self._storage.update_card(
                        previous_card.id,
                        end_time=previous_card._next_card_start_time
                    )
                    if not success:
                        logger.error(f"更新上一张卡片 {previous_card.id} 的结束时间失败")
            
        rest_card = ActivityCard(
            category="休息",
            title="休息时间",
            summary=f"用户休息了 {format_rest_duration(rest_duration)}",
            start_time=self._rest_start_time,
            app_sites=[],
            productivity_score=0.0
        )
        rest_card._next_card_start_time = current_time
        
        if self._storage:
            try:
                card_id = self._storage.save_card(rest_card)
                rest_card.id = card_id
                self._current_rest_card_id = card_id
                logger.info(f"已创建休息卡片 ID={card_id}: {self._rest_start_time.strftime('%H:%M:%S')} - {current_time.strftime('%H:%M:%S')} ({rest_duration:.1f}分钟)")
                return rest_card
            except Exception as e:
                logger.error(f"保存休息卡片失败: {e}")
                return None
        return None
    
    def _update_rest_card_end_time(self, end_time: datetime = None):
        """更新休息卡片的结束时间（用户结束休息时调用）
        
        Args:
            end_time: 休息结束时间，如果为None则使用当前时间
        """
        if not self._current_rest_card_id or not self._rest_start_time:
            return
            
        current_time = end_time if end_time else datetime.now()
        rest_duration = (current_time - self._rest_start_time).total_seconds() / 60  # 分钟
        
        if self._storage:
            try:
                updated = self._storage.update_card(
                    self._current_rest_card_id,
                    end_time=current_time,
                    summary=f"用户休息了 {format_rest_duration(rest_duration)}"
                )
                if updated:
                    logger.info(f"已更新休息卡片结束时间: {self._rest_start_time.strftime('%H:%M:%S')} - {current_time.strftime('%H:%M:%S')} ({rest_duration:.1f}分钟)")
                    
                    # 验证与下一张卡片的时间连续性
                    # 获取休息结束时间之后的下一张卡片
                    next_cards = self._storage.get_cards_after_time(
                        current_time,
                        limit=1
                    )
                    if next_cards:
                        next_card = next_cards[0]
                        if current_time > next_card.start_time:
                            # 休息卡片的结束时间晚于下一张卡片的开始时间，修正休息卡片的结束时间
                            logger.warning(
                                f"休息卡片与下一张卡片时间重叠：休息卡片的结束时间 {current_time} "
                                f"晚于下一张卡片 ({next_card.title}) 的开始时间 {next_card.start_time}，修正休息卡片的结束时间"
                            )
                            success = self._storage.update_card(
                                self._current_rest_card_id,
                                end_time=next_card.start_time,
                                summary=f"用户休息了 {(next_card.start_time - self._rest_start_time).total_seconds() / 60:.1f}分钟"
                            )
                            if success:
                                logger.info(f"已修正休息卡片的结束时间: {current_time} -> {next_card.start_time}")
                    
                    # 清除卡片ID，表示休息结束
                    self._rest_start_time = None
                    self._current_rest_card_id = None
            except Exception as e:
                logger.error(f"更新休息卡片失败: {e}")
    
    def _update_rest_card_end_time_for_loop(self):
        """更新休息卡片的结束时间（后台更新循环调用，不清除卡片ID）"""
        if not self._current_rest_card_id or not self._rest_start_time:
            logger.debug(f"跳过更新休息卡片: _current_rest_card_id={self._current_rest_card_id}, _rest_start_time={self._rest_start_time}")
            return
            
        current_time = datetime.now()
        rest_duration = (current_time - self._rest_start_time).total_seconds() / 60  # 分钟
        
        logger.info(f"开始更新休息卡片 ID={self._current_rest_card_id}, 当前休息时长: {rest_duration:.1f}分钟")
        
        if self._storage:
            try:
                updated = self._storage.update_card(
                    self._current_rest_card_id,
                    end_time=current_time,
                    summary=f"用户休息了 {format_rest_duration(rest_duration)}"
                )
                if updated:
                    logger.info(f"已更新休息卡片结束时间: {self._rest_start_time.strftime('%H:%M:%S')} - {current_time.strftime('%H:%M:%S')} ({rest_duration:.1f}分钟)")
                else:
                    logger.warning(f"更新休息卡片失败，返回False")
            except Exception as e:
                logger.error(f"更新休息卡片失败: {e}")
    
    def _start_rest_card_update_thread(self):
        """启动休息卡片更新线程"""
        logger.info(f"准备启动休息卡片更新线程: _rest_card_update_thread={self._rest_card_update_thread}, is_alive={self._rest_card_update_thread.is_alive() if self._rest_card_update_thread else None}")
        
        if self._rest_card_update_thread and self._rest_card_update_thread.is_alive():
            logger.info("休息卡片更新线程已在运行，不重复启动")
            return
            
        logger.info(f"启动更新线程前的状态: _current_rest_card_id={self._current_rest_card_id}, _rest_start_time={self._rest_start_time}")
        self._rest_card_update_stop_event.clear()
        self._rest_card_update_thread = threading.Thread(target=self._rest_card_update_loop, daemon=True)
        self._rest_card_update_thread.start()
        logger.info("休息卡片更新线程已启动")
    
    def _stop_rest_card_update_thread(self):
        """停止休息卡片更新线程"""
        self._rest_card_update_stop_event.set()
        if self._rest_card_update_thread and self._rest_card_update_thread.is_alive():
            self._rest_card_update_thread.join(timeout=2)
        logger.info("休息卡片更新线程已停止")
    
    def _rest_card_update_loop(self):
        """休息卡片更新循环"""
        logger.info("休息卡片更新循环已启动")
        while not self._rest_card_update_stop_event.is_set():
            try:
                logger.debug(f"休息卡片更新循环检查: _current_rest_card_id={self._current_rest_card_id}, _rest_start_time={self._rest_start_time}")
                if self._current_rest_card_id and self._rest_start_time:
                    self._update_rest_card_end_time_for_loop()
                self._rest_card_update_stop_event.wait(60)  # 每60秒更新一次
            except Exception as e:
                logger.error(f"休息卡片更新循环错误: {e}")
                self._rest_card_update_stop_event.wait(10)
    
    def _pause_recording(self):
        """暂停录制"""
        if self.recorder.is_recording and not self.recorder.is_paused:
            logger.info("自动暂停录制")
            self.recorder.pause()
            self._auto_paused = True
        else:
            logger.info(f"录制器状态: 录制={self.recorder.is_recording}, 暂停={self.recorder.is_paused}, 不执行暂停")
    
    def _monitor_loop(self):
        """监测主循环"""
        logger.info("智能自动暂停录制器已启动")
        logger.info(f"  - 初始状态: {self._state}")
        
        self._state = "IDLE"
        self._state_start_time = time.time()
        
        while not self._stop_event.is_set():
            try:
                if self._state == "IDLE":
                    self._state_idle()
                elif self._state == "WAIT_FOR_CHECK":
                    self._state_wait_for_check()
                elif self._state == "CHECK_10S":
                    self._state_check_10s()
                elif self._state == "CHECK_60S":
                    self._state_check_60s()
                elif self._state == "STOPPED":
                    self._state_stopped()
                elif self._state == "REST_MONITORING":
                    self._state_rest_monitoring()
                elif self._state == "REST_WAIT_30":
                    self._state_rest_wait_30()
                elif self._state == "REST_DETECT_90":
                    self._state_rest_detect_90()
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
        
        # 立即设置停止事件，防止主监测线程继续执行状态机
        self._stop_event.set()
        
        # 清空回调，防止主监测线程中的状态机继续调用
        self._on_stop_recording = None
        self._on_resume_recording = None
        
        # 如果处于休息状态，创建休息卡片
        if self._rest_start_time:
            rest_end_time = datetime.now()
            rest_duration = (rest_end_time - self._rest_start_time).total_seconds() / 60  # 分钟
            
            # 创建休息卡片，不限制休息时间
            
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
                        summary=f"用户休息了 {format_rest_duration(merged_duration)}",
                        start_time=merged_start_time,
                        app_sites=[],
                        productivity_score=0.0
                    )
                    rest_card._next_card_start_time = rest_end_time
                    
                    # 验证与上一张卡片的时间连续性
                    if self._storage:
                        previous_cards = self._storage.get_cards_before_time(
                            merged_start_time,
                            limit=1
                        )
                        if previous_cards:
                            previous_card = previous_cards[0]
                            if previous_card._next_card_start_time and previous_card._next_card_start_time > merged_start_time:
                                # 上一张卡片的结束时间晚于休息开始时间，修正上一张卡片
                                logger.warning(
                                    f"合并休息卡片与上一张卡片时间重叠：上一张卡片 ({previous_card.title}) 的结束时间 {previous_card._next_card_start_time} "
                                    f"晚于休息开始时间 {merged_start_time}，修正上一张卡片的结束时间"
                                )
                                success = self._storage.update_card(
                                    previous_card.id,
                                    end_time=merged_start_time
                                )
                                if success:
                                    logger.info(f"已修正上一张卡片 {previous_card.id} 的结束时间: {previous_card._next_card_start_time} -> {merged_start_time}")
                    
                    if self._storage:
                        try:
                            card_id = self._storage.save_card(rest_card)
                            rest_card.id = card_id
                            self._current_rest_card_id = card_id
                            logger.info(f"已创建合并后的休息卡片 ID={card_id}: {merged_start_time.strftime('%H:%M:%S')} - {rest_end_time.strftime('%H:%M:%S')} ({merged_duration:.1f}分钟)")
                        except Exception as e:
                            logger.error(f"保存休息卡片失败: {e}")
                
                    # 更新休息开始时间为合并后的开始时间，用于更新循环
                    self._rest_start_time = merged_start_time
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
                        summary=f"用户休息了 {format_rest_duration(rest_duration)}",
                        start_time=self._rest_start_time,
                        app_sites=[],
                        productivity_score=0.0
                    )
                    rest_card._next_card_start_time = rest_end_time
                    
                    # 验证与上一张卡片的时间连续性
                    if self._storage:
                        previous_cards = self._storage.get_cards_before_time(
                            self._rest_start_time,
                            limit=1
                        )
                        if previous_cards:
                            previous_card = previous_cards[0]
                            if previous_card._next_card_start_time and previous_card._next_card_start_time > self._rest_start_time:
                                # 上一张卡片的结束时间晚于休息开始时间，修正上一张卡片
                                logger.warning(
                                    f"创建休息卡片与上一张卡片时间重叠：上一张卡片 ({previous_card.title}) 的结束时间 {previous_card._next_card_start_time} "
                                    f"晚于休息开始时间 {self._rest_start_time}，修正上一张卡片的结束时间"
                                )
                                success = self._storage.update_card(
                                    previous_card.id,
                                    end_time=self._rest_start_time
                                )
                                if success:
                                    logger.info(f"已修正上一张卡片 {previous_card.id} 的结束时间: {previous_card._next_card_start_time} -> {self._rest_start_time}")
                    
                    if self._storage:
                        try:
                            card_id = self._storage.save_card(rest_card)
                            rest_card.id = card_id
                            self._current_rest_card_id = card_id
                            logger.info(f"已创建休息卡片 ID={card_id}: {self._rest_start_time.strftime('%H:%M:%S')} - {rest_end_time.strftime('%H:%M:%S')} ({rest_duration:.1f}分钟)")
                        except Exception as e:
                            logger.error(f"保存休息卡片失败: {e}")
            else:
                # 过去2分钟内没有卡片，直接创建休息卡片
                rest_card = ActivityCard(
                    category="休息",
                    title="休息时间",
                    summary=f"用户休息了 {format_rest_duration(rest_duration)}",
                    start_time=self._rest_start_time,
                    app_sites=[],
                    productivity_score=0.0
                )
                rest_card._next_card_start_time = rest_end_time
                
                if self._storage:
                    try:
                        card_id = self._storage.save_card(rest_card)
                        rest_card.id = card_id
                        self._current_rest_card_id = card_id
                        logger.info(f"已创建休息卡片 ID={card_id}: {self._rest_start_time.strftime('%H:%M:%S')} - {rest_end_time.strftime('%H:%M:%S')} ({rest_duration:.1f}分钟)")
                    except Exception as e:
                        logger.error(f"保存休息卡片失败: {e}")
            
            # 用户点击"停止追踪"时，不启动休息卡片更新线程
            # 休息卡片已经创建完成，不需要继续更新
        
        # 停止休息卡片更新线程（如果正在运行）
        self._stop_rest_card_update_thread()
        
        # 停止监听器
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        
        # 等待主监测线程完全停止（已在开始时设置了停止事件）
        # 增加超时时间到5秒，确保线程有足够时间停止
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.info("等待主监测线程停止...")
            self._monitor_thread.join(timeout=5)
            if self._monitor_thread.is_alive():
                logger.warning("主监测线程未能在5秒内停止")
            else:
                logger.info("主监测线程已停止")
        
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
