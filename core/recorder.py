"""
Dayflow Windows - 屏幕录制模块
使用 dxcam 实现低功耗 1FPS 录制
"""
import time
import logging
import threading
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, List, Dict

import dxcam
import cv2

import config
from core.types import VideoChunk, ChunkStatus
from core.window_tracker import get_tracker, WindowInfo
from core.activity_monitor_v2 import SmartAutoPauseRecorder

logger = logging.getLogger(__name__)


class ScreenRecorder:
    """
    屏幕录制器
    - 1 FPS 低功耗录制
    - 每 60 秒自动切片
    - H.264 编码，低码率
    """
    
    def __init__(
        self,
        frame_interval: float = None,
        chunk_duration: int = None,
        output_dir: Path = None,
        on_chunk_saved: Optional[Callable[[VideoChunk], None]] = None,
        output_idx: int = 0,
        enable_auto_pause: bool = None,
        storage = None,
        on_stop_recording: Optional[Callable[[], None]] = None,
        on_resume_recording: Optional[Callable[[], None]] = None,
    ):
        self.frame_interval = frame_interval or config.RECORD_FRAME_INTERVAL
        self.fps = 1.0 / self.frame_interval  # 计算FPS供VideoWriter使用
        self.chunk_duration = chunk_duration or config.CHUNK_DURATION_SECONDS
        self.output_dir = output_dir or config.CHUNKS_DIR
        self.on_chunk_saved = on_chunk_saved
        self.output_idx = max(0, int(output_idx or 0))
        self.on_stop_recording = on_stop_recording  # 停止录制回调
        self.on_resume_recording = on_resume_recording  # 恢复录制回调
        
        # 状态
        self._recording = False
        self._paused = False
        self._camera: Optional[dxcam.DXCamera] = None
        self._record_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 当前切片信息
        self._current_writer: Optional[cv2.VideoWriter] = None
        self._current_chunk_path: Optional[Path] = None
        self._current_chunk_start: Optional[datetime] = None
        self._frame_count = 0
        self._prev_chunk_end_time: Optional[datetime] = None  # 上一个切片的结束时间
        self._recording_start_time: Optional[datetime] = None  # 本次录制开始时间（用于第一个切片）
        
        # 窗口追踪
        self._window_tracker = get_tracker()
        self._current_window_records: List[Dict] = []  # 当前切片的窗口记录
        
        # 活跃度感知
        self._auto_pause_recorder: Optional[SmartAutoPauseRecorder] = None
        self._enable_auto_pause = enable_auto_pause if enable_auto_pause is not None else config.ENABLE_AUTO_PAUSE
        
        # 保存storage引用
        self._storage = storage
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def is_recording(self) -> bool:
        return self._recording
    
    @property
    def is_paused(self) -> bool:
        return self._paused
    
    def start(self):
        """开始录制
        
        返回:
            datetime: 录制开始时间
        """
        if self._recording:
            logger.warning("录制已在进行中")
            return None
        
        start_time = datetime.now()
        self._recording_start_time = start_time  # 记录本次录制开始时间
        self._prev_chunk_end_time = None  # 重置上一个切片结束时间，确保第一张切片使用录制开始时间
        logger.info(f"开始屏幕录制... (显示器 output_idx={self.output_idx}), _prev_chunk_end_time已重置为None")
        
        # 初始化 dxcam（带降级重试，避免部分机器/显示器组合直接灾难性失败）
        self._camera = self._create_camera_with_fallback()
        
        self._recording = True
        self._paused = False
        self._stop_event.clear()
        
        # 注意：不再启动活跃度感知，因为休息检测器现在由RecordingManager统一管理
        
        # 启动录制线程
        self._record_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self._record_thread.start()
        
        logger.info(f"录制已启动 - 帧间隔: {self.frame_interval}秒/帧 (FPS: {self.fps:.2f}), 切片时长: {self.chunk_duration}秒")
        return start_time
    
    def stop(self):
        """停止录制"""
        if not self._recording:
            logger.warning("录制未在进行中")
            return None
        
        logger.info("停止屏幕录制...")
        stop_time = self._stop_recording_without_pause_detector()
        logger.info("录制已停止")
        return stop_time

    def _stop_recording_without_pause_detector(self):
        """内部方法：仅停止视频录制（不停止休息检测器），返回停止时间
        
        此方法用于RecordingManager管理休息检测器时，只停止视频录制，
        而不停止休息检测器，这样休息检测器可以继续检测用户是否结束休息
        """
        # 首先记录停止时间（这是最精确的停止时间）
        stop_time = datetime.now()
        logger.info(f"停止录制，停止时间={stop_time.strftime('%H:%M:%S')}, 当前_prev_chunk_end_time={self._prev_chunk_end_time.strftime('%H:%M:%S') if self._prev_chunk_end_time else 'None'}")
        
        self._stop_event.set()
        self._recording = False
        
        # 注意：不停止活跃度感知（休息检测器），因为它由RecordingManager统一管理
        
        # 等待录制线程结束（缩短超时时间）
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=2)
            if self._record_thread.is_alive():
                logger.warning("录制线程未能在超时内停止")
        
        # 记录停止时间到窗口记录
        if self._current_window_records:
            elapsed = (stop_time - self._current_chunk_start).total_seconds() if self._current_chunk_start else 0
            self._current_window_records.append({
                "timestamp": elapsed,
                "event": "card_end",
                "card_end_time": stop_time.isoformat()
            })
        
        # 保存当前切片（传入停止时间，确保切片结束时间与停止时间一致）
        try:
            self._finalize_current_chunk(stop_time)
        except Exception as e:
            logger.error(f"保存切片时出错: {e}")
        
        # 释放 dxcam
        try:
            if self._camera:
                del self._camera
                self._camera = None
        except Exception as e:
            logger.error(f"释放相机时出错: {e}")
        
        return stop_time
    
    def pause(self):
        """暂停录制"""
        if self._recording and not self._paused:
            self._paused = True
            logger.info("录制已暂停")
            
            # 暂停时完成当前切片，避免数据丢失
            self._finalize_current_chunk()
    
    def resume(self):
        """恢复录制"""
        if self._recording and self._paused:
            self._paused = False
            logger.info("录制已恢复")
    
    def is_auto_paused(self) -> bool:
        """是否因闲置而自动暂停"""
        return self._auto_paused
    
    def get_idle_time(self) -> float:
        """获取闲置时间（秒）"""
        if self._auto_pause_recorder:
            return self._auto_pause_recorder.get_idle_time()
        return 0.0
    
    def is_user_active(self) -> bool:
        """检查用户是否活跃"""
        if self._auto_pause_recorder:
            return self._auto_pause_recorder.is_user_active()
        return True
    
    def _create_camera_with_fallback(self) -> dxcam.DXCamera:
        """创建 dxcam 相机，失败时尝试多种降级参数。"""
        attempts = [
            {"output_idx": self.output_idx, "output_color": "BGR"},
            {"output_idx": self.output_idx},
            {"device_idx": 0, "output_idx": self.output_idx, "output_color": "BGR"},
            {"device_idx": 0, "output_idx": self.output_idx},
            {},
        ]
        last_error = None

        for idx, kwargs in enumerate(attempts, start=1):
            try:
                logger.info(f"尝试初始化 dxcam ({idx}/{len(attempts)}): {kwargs}")
                camera = dxcam.create(**kwargs)
                # 部分环境 create 成功但首次 grab 才会炸，这里预抓一帧尽早暴露问题
                test_frame = camera.grab()
                if test_frame is None:
                    logger.warning("dxcam 初始化成功，但首次抓帧为空；继续使用并在录制循环中重试")
                logger.info("dxcam 初始化成功")
                return camera
            except Exception as e:
                last_error = e
                logger.warning(f"dxcam 初始化尝试失败 ({kwargs}): {e}")
                time.sleep(0.3)

        error_message = (
            "初始化屏幕录制失败。可能原因：显卡/显示器驱动异常、远程桌面环境、"
            "dxcam 与当前输出设备不兼容。建议重启应用、更新显卡驱动，或切换显示器后重试。"
        )
        logger.error(f"{error_message} 最后错误: {last_error}")
        raise RuntimeError(error_message) from last_error

    def _recording_loop(self):
        """录制主循环"""
        last_frame_time = 0
        last_window_info = None  # 缓存上次窗口信息
        
        while not self._stop_event.is_set():
            current_time = time.time()
            
            # 控制帧率 - 使用精确等待而非轮询
            time_to_wait = self.frame_interval - (current_time - last_frame_time)
            if time_to_wait > 0:
                self._stop_event.wait(min(time_to_wait, 0.5))  # 最多等待0.5秒，确保能响应停止信号
                continue
            
            # 暂停检查
            if self._paused:
                self._stop_event.wait(0.5)
                continue
            
            try:
                # 捕获屏幕
                frame = self._camera.grab()
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # 先采集窗口信息（在帧捕获时立即采集，确保时间对齐）
                frame_capture_time = datetime.now()
                window_info = self._window_tracker.get_active_window()
                
                # 检查是否需要创建新切片
                if self._should_create_new_chunk():
                    self._finalize_current_chunk()
                    self._create_new_chunk(frame.shape)
                    last_window_info = None  # 重置窗口缓存
                
                # 记录窗口信息（仅在窗口变化时记录，减少数据量）
                if self._current_chunk_start and window_info:
                    # 检查窗口是否变化
                    window_changed = (
                        last_window_info is None or
                        last_window_info.app_name != window_info.app_name or
                        last_window_info.window_title != window_info.window_title
                    )
                    
                    if window_changed:
                        elapsed = (frame_capture_time - self._current_chunk_start).total_seconds()
                        self._current_window_records.append({
                            "timestamp": elapsed,
                            "app_name": self._window_tracker.get_friendly_app_name(window_info),
                            "window_title": window_info.window_title,
                            "process_name": window_info.app_name
                        })
                        last_window_info = window_info
                
                # 写入帧
                if self._current_writer:
                    self._current_writer.write(frame)
                    self._frame_count += 1
                
                last_frame_time = current_time
                
            except Exception as e:
                logger.error(f"录制帧错误: {e}")
                time.sleep(1)
    
    def _should_create_new_chunk(self) -> bool:
        """检查是否需要创建新切片"""
        if self._paused:
            return False
        
        if self._current_chunk_start is None:
            return True
        
        elapsed = (datetime.now() - self._current_chunk_start).total_seconds()
        return elapsed >= self.chunk_duration
    
    def _create_new_chunk(self, frame_shape: tuple):
        """创建新的视频切片"""
        # 确保新切片的开始时间等于上一个切片的结束时间
        # 如果是第一个切片，使用录制开始时间（确保与休息卡片结束时间一致）
        if self._prev_chunk_end_time is not None:
            timestamp = self._prev_chunk_end_time
            logger.debug(f"使用_prev_chunk_end_time作为切片开始时间: {timestamp.strftime('%H:%M:%S')}")
        elif self._recording_start_time is not None:
            timestamp = self._recording_start_time
            logger.debug(f"使用_recording_start_time作为切片开始时间: {timestamp.strftime('%H:%M:%S')}")
        else:
            timestamp = datetime.now()
            logger.debug(f"使用当前时间作为切片开始时间: {timestamp.strftime('%H:%M:%S')}")
        
        filename = f"chunk_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
        self._current_chunk_path = self.output_dir / filename
        self._current_chunk_start = timestamp
        self._frame_count = 0
        self._current_window_records = []  # 重置窗口记录
        
        # 添加卡片开始时间到窗口记录（实时记录）
        self._current_window_records.append({
            "timestamp": 0.0,
            "event": "card_start",
            "card_start_time": timestamp.isoformat()
        })
        
        # 创建 VideoWriter
        height, width = frame_shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        self._current_writer = cv2.VideoWriter(
            str(self._current_chunk_path),
            fourcc,
            self.fps,
            (width, height)
        )
        
        logger.debug(f"创建新切片: {filename}")
    
    def _finalize_current_chunk(self, end_time: datetime = None):
        """完成当前切片
        
        Args:
            end_time: 切片结束时间，如果为None则使用当前时间
        """
        if self._current_writer is None:
            return
        
        self._current_writer.release()
        
        if self._current_chunk_path and self._current_chunk_path.exists():
            chunk_end_time = end_time if end_time else datetime.now()
            duration = (chunk_end_time - self._current_chunk_start).total_seconds()
            
            # 保存窗口记录到 JSON 文件
            window_records_path = None
            if self._current_window_records:
                window_records_path = self._current_chunk_path.with_suffix('.json')
                try:
                    with open(window_records_path, 'w', encoding='utf-8') as f:
                        json.dump(self._current_window_records, f, ensure_ascii=False, indent=2)
                    logger.debug(f"窗口记录已保存: {window_records_path.name}")
                except Exception as e:
                    logger.warning(f"保存窗口记录失败: {e}")
                    window_records_path = None
            
            # 记录结束时间供下一个切片使用
            self._prev_chunk_end_time = chunk_end_time
            logger.debug(f"更新_prev_chunk_end_time={chunk_end_time.strftime('%H:%M:%S')}")
            
            # 创建切片对象
            chunk = VideoChunk(
                file_path=str(self._current_chunk_path),
                start_time=self._current_chunk_start,
                end_time=chunk_end_time,
                duration_seconds=duration,
                status=ChunkStatus.PENDING,
                window_records_path=str(window_records_path) if window_records_path else None
            )
            
            logger.info(f"切片已保存: {self._current_chunk_path.name} ({duration:.1f}秒, {self._frame_count}帧, {len(self._current_window_records)}条窗口记录)")
            
            # 回调通知
            if self.on_chunk_saved:
                try:
                    self.on_chunk_saved(chunk)
                except Exception as e:
                    logger.error(f"切片保存回调错误: {e}")
        
        self._current_writer = None
        self._current_chunk_path = None
        self._current_chunk_start = None
        self._frame_count = 0
        self._current_window_records = []


class RecordingManager:
    """
    录制管理器
    整合录制器、休息检测器和数据库存储
    """
    
    def __init__(self, storage_manager=None, scheduler=None):
        from database.storage import StorageManager
        self.storage = storage_manager or StorageManager()
        self.scheduler = scheduler  # 分析调度器，用于触发立即扫描
        try:
            output_idx = int(self.storage.get_setting("record_output_idx", "0"))
        except Exception:
            output_idx = 0
        self.recorder = ScreenRecorder(
            on_chunk_saved=self._on_chunk_saved,
            output_idx=output_idx,
            storage=self.storage,
            enable_auto_pause=False  # 不在ScreenRecorder中启用，由RecordingManager统一管理
        )
        
        # 休息检测器（由RecordingManager统一管理，与录制器分离）
        self._auto_pause_recorder: Optional[SmartAutoPauseRecorder] = None
        self._enable_auto_pause = config.ENABLE_AUTO_PAUSE
        
        # 录制管理器自己的自动暂停标志
        self._auto_paused = False
        
        # 分析调度器的原始启动状态（用于恢复）
        self._scheduler_was_running = False
    
    def _on_chunk_saved(self, chunk: VideoChunk):
        """切片保存回调 - 写入数据库"""
        try:
            chunk_id = self.storage.save_chunk(chunk)
            logger.info(f"切片已入库: ID={chunk_id}, 开始时间={chunk.start_time.strftime('%H:%M:%S')}, 结束时间={chunk.end_time.strftime('%H:%M:%S')}, 时长={chunk.duration_seconds:.1f}秒")
            
            # 立即触发分析调度器扫描，无需等待定时间隔
            if self.scheduler:
                logger.debug(f"触发分析调度器扫描（切片ID={chunk_id}）")
                self.scheduler.trigger_scan()
        except Exception as e:
            logger.error(f"切片入库失败: {e}")
    
    def start_recording(self):
        """开始录制
        
        这是一个可复用的方法，用于：
        1. 检查是否有未分析的视频（警告）
        2. 检查最后一张活动卡片是否为休息卡片，更新其结束时间
        3. 启动视频录制
        4. 启动休息检测器（如果启用）
        
        返回:
            datetime: 录制开始时间
        """
        logger.info("========== RecordingManager: start_recording ==========")
        logger.info("开始录制...")
        
        # 重置自动暂停标志（开始新录制时，不是自动暂停状态）
        self._auto_paused = False
        logger.info("重置 _auto_paused = False（开始新录制）")
        
        # 1. 检查是否有未分析的视频
        pending_chunks = self.storage.get_pending_chunks()
        if pending_chunks:
            logger.warning(f"发现 {len(pending_chunks)} 个未分析的视频切片！在开始录制时应该处于全部视频分析完成的状态")
        
        # 2. 检查最后一张活动卡片是否为休息卡片，更新其结束时间
        from datetime import datetime
        now = datetime.now()
        latest_cards = self.storage.get_cards_before_time(now, limit=1)
        if latest_cards:
            latest_card = latest_cards[0]
            if latest_card.category == "rest":
                logger.info(f"最后一张卡片是休息卡片，将更新其结束时间为录制开始时间")
                success = self.storage.update_card(
                    latest_card.id,
                    end_time=now
                )
                if success:
                    logger.info(f"已更新休息卡片 {latest_card.id} 的结束时间: {now.strftime('%H:%M:%S')}")
                else:
                    logger.error(f"更新休息卡片 {latest_card.id} 失败")
        
        # 3. 启动视频录制
        start_time = self.recorder.start()
        logger.info(f"recorder.start()返回: {start_time.strftime('%H:%M:%S') if start_time else 'None'}")
        
        # 保存录制开始时间到设置中，用于第一张卡片的时间设置
        if start_time:
            self.storage.set_setting("recording_start_time", start_time.isoformat())
            logger.info(f"已保存录制开始时间到设置: {start_time.strftime('%H:%M:%S')}")
        
        # 4. 启动分析调度器（强绑定：录制开始时启动分析）
        if self.scheduler and not self.scheduler.is_running:
            self._scheduler_was_running = False  # 记录原始状态为未运行
            self.scheduler.start()
            logger.info("分析调度器已启动（录制-分析强绑定）")
        elif self.scheduler and self.scheduler.is_running:
            self._scheduler_was_running = True  # 记录原始状态为已运行
            logger.info("分析调度器已在运行（录制-分析强绑定）")
        
        # 5. 启动休息检测器（与录制器分离管理）
        if self._enable_auto_pause:
            # 如果已有休息检测器实例，先停止它
            if self._auto_pause_recorder and self._auto_pause_recorder._monitoring:
                logger.info("检测到旧的休息检测器正在运行，先停止它")
                self._auto_pause_recorder.stop()
                self._auto_pause_recorder = None
            
            self._auto_pause_recorder = SmartAutoPauseRecorder(
                self.recorder,
                stop_check_interval=config.STOP_CHECK_INTERVAL,
                stop_detection_duration=config.STOP_DETECTION_DURATION,
                resume_wait_duration=config.RESUME_WAIT_DURATION,
                resume_detection_duration=config.RESUME_DETECTION_DURATION,
                storage=self.storage,
                on_stop_recording=self.stop_recording_and_analyze,
                on_resume_recording=self.resume_recording
            )
            if self._auto_pause_recorder.start():
                logger.info("休息检测器已启动")
            else:
                logger.warning("休息检测器启动失败，将使用普通录制模式")
                self._auto_pause_recorder = None
        
        return start_time
    
    def stop_recording(self):
        """停止录制"""
        self.stop_recording_and_analyze()
    
    def resume_recording(self):
        """恢复录制（重新启动录制）
        
        这是一个可复用的方法，用于：
        1. 检查是否有未分析的视频（警告）
        2. 检查最后一张活动卡片是否为休息卡片，更新其结束时间
        3. 启动视频录制
        4. 不启动休息检测器（因为它已经在运行）
        
        返回:
            datetime: 录制开始时间
        """
        logger.info("========== RecordingManager: resume_recording ==========")
        logger.info("重新启动录制...")
        
        # 1. 检查是否有未分析的视频
        pending_chunks = self.storage.get_pending_chunks()
        if pending_chunks:
            logger.warning(f"发现 {len(pending_chunks)} 个未分析的视频切片！在恢复录制时应该处于全部视频分析完成的状态")
        
        # 2. 检查最后一张活动卡片是否为休息卡片，更新其结束时间
        from datetime import datetime
        now = datetime.now()
        latest_cards = self.storage.get_cards_before_time(now, limit=1)
        if latest_cards:
            latest_card = latest_cards[0]
            if latest_card.category == "rest":
                logger.info(f"最后一张卡片是休息卡片，将更新其结束时间为录制开始时间")
                success = self.storage.update_card(
                    latest_card.id,
                    end_time=now
                )
                if success:
                    logger.info(f"已更新休息卡片 {latest_card.id} 的结束时间: {now.strftime('%H:%M:%S')}")
                else:
                    logger.error(f"更新休息卡片 {latest_card.id} 失败")
        
        # 3. 启动视频录制，不启动休息检测器（因为它已经在运行）
        # 清除自动暂停标志（从休息状态恢复录制）
        self._auto_paused = False
        logger.info("设置 _auto_paused = False（从休息状态恢复录制）")
        
        start_time = self.recorder.start()
        logger.info(f"recorder.start()返回: {start_time.strftime('%H:%M:%S') if start_time else 'None'}")
        return start_time

    def stop_recording_and_analyze(self):
        """停止录制并分析所有视频
        
        这是一个可复用的方法，用于：
        1. 停止视频录制
        2. 保存当前切片
        3. 立即分析所有视频，生成活动卡片
        4. 注意：不停止休息检测器，让它继续检测用户是否结束休息
        
        此方法可在以下场景调用：
        - 用户点击"停止追踪"按钮
        - 检测到用户休息时自动停止录制
        
        返回:
            datetime: 录制停止时间
        """
        if not self.recorder.is_recording:
            logger.warning("录制未在进行中，跳过停止")
            return None
        
        logger.info("========== stop_recording_and_analyze: 开始 ==========")
        
        # 设置自动暂停标志（此方法在休息检测器调用停止录制时被调用）
        self._auto_paused = True
        logger.info("设置 _auto_paused = True（进入休息状态）")
        
        # 1. 停止录制（保存当前切片），获取停止时间
        # 注意：只停止视频录制，不停止休息检测器
        logger.info("========== step 1: 停止录制 ==========")
        stop_time = self.recorder._stop_recording_without_pause_detector()
        logger.info(f"录制已停止，停止时间：{stop_time.strftime('%H:%M:%S')}")
        
        # 2. 分析所有剩余的视频切片
        logger.info("========== step 2: 分析所有剩余视频切片 ==========")
        
        # 如果 scheduler 未启动，临时创建一个实例来分析剩余切片
        scheduler = self.scheduler
        if scheduler is None:
            logger.info("分析调度器未启动，临时创建 AnalysisScheduler 实例来分析剩余切片")
            from core.analysis import AnalysisScheduler
            scheduler = AnalysisScheduler(storage=self.storage)
        
        try:
            logger.info("调用 scheduler.analyze_remaining_chunks()...")
            scheduler.analyze_remaining_chunks()
            logger.info("========== 所有视频切片分析完成 ==========")
        except Exception as e:
            logger.error(f"分析视频切片失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # 3. 检查最后一张活动卡片的时间等于停止录制的时间
        if stop_time:
            logger.info("========== step 3: 验证最后一张卡片时间 ==========")
            from datetime import timedelta
            latest_cards = self.storage.get_cards_before_time(stop_time + timedelta(seconds=1), limit=1)
            if latest_cards:
                latest_card = latest_cards[0]
                card_end_time = latest_card._next_card_start_time if latest_card._next_card_start_time else latest_card.start_time
                
                time_diff = abs((stop_time - card_end_time).total_seconds())
                logger.info(f"最后一张卡片: {latest_card.title}, 结束时间: {card_end_time.strftime('%H:%M:%S')}")
                logger.info(f"录制停止时间: {stop_time.strftime('%H:%M:%S')}, 时间差: {time_diff:.1f}秒")
                
                if time_diff > 5:
                    logger.warning(f"最后一张卡片的结束时间与录制停止时间不一致（相差{time_diff:.1f}秒），可能需要手动调整")
                else:
                    logger.info("最后一张卡片的结束时间与录制停止时间一致")
            else:
                logger.warning("未找到最后一张活动卡片")
        
        return stop_time
    
    def stop_tracking(self):
        """停止追踪（完全停止录制、休息检测和分析调度器）
        
        这是用户点击"停止追踪"按钮时调用的方法：
        1. 停止休息检测器
        2. 如果在录制中，停止录制并分析（等待所有分析完成）
        3. 停止分析调度器（如果是由此方法启动的）
        
        返回:
            datetime: 录制停止时间
        """
        logger.info("========== RecordingManager.stop_tracking() 开始 ==========")
        logger.info(f"  - is_recording: {self.is_recording}")
        logger.info(f"  - is_auto_paused: {self.is_auto_paused()}")
        logger.info(f"  - scheduler存在: {self.scheduler is not None}")
        if self.scheduler:
            logger.info(f"  - scheduler.is_running: {self.scheduler.is_running}")
        
        # 1. 停止休息检测器
        if self._auto_pause_recorder:
            logger.info("停止休息检测器...")
            self._auto_pause_recorder.stop()
            self._auto_pause_recorder = None
            logger.info("休息检测器已停止")
        else:
            logger.info("休息检测器未启动，跳过")
        
        # 2. 只有在录制中时才停止录制并分析
        # 休息状态下 is_recording = False，不需要再停止录制
        stop_time = None
        if self.is_recording:
            stop_time = self.stop_recording_and_analyze()
        else:
            logger.info("录制已停止（休息状态），跳过停止录制和分析步骤")
        
        # 3. 停止分析调度器（强绑定：录制停止时停止分析，但要等分析完成）
        if self.scheduler and self.scheduler.is_running and not self._scheduler_was_running:
            self.scheduler.stop()
            logger.info("分析调度器已停止（录制-分析强绑定）")
        elif self.scheduler and self.scheduler.is_running:
            logger.info("分析调度器继续运行（录制-分析强绑定：恢复到原始状态）")
        
        # 4. 重置自动暂停标志（用户手动停止，不是自动暂停）
        self._auto_paused = False
        logger.info("重置 _auto_paused = False（用户手动停止，不是自动暂停）")
        
        logger.info(f"========== 停止追踪完成，停止时间：{stop_time.strftime('%H:%M:%S') if stop_time else 'None'} ==========")
        return stop_time

    def pause_recording(self):
        """暂停录制"""
        self.recorder.pause()
    
    @property
    def is_recording(self) -> bool:
        return self.recorder.is_recording
    
    @property
    def is_paused(self) -> bool:
        return self.recorder.is_paused
    
    def is_auto_paused(self) -> bool:
        """是否因闲置而自动暂停"""
        return self._auto_paused
    
    def get_idle_time(self) -> float:
        """获取闲置时间（秒）"""
        return self.recorder.get_idle_time()
    
    def is_user_active(self) -> bool:
        """检查用户是否活跃"""
        return self.recorder.is_user_active()
