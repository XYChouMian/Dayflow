"""
Dayflow Windows - 分析调度器
批量处理视频切片，调用 API 生成时间轴卡片
"""
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path

import config
from core.types import (
    VideoChunk, ChunkStatus,
    AnalysisBatch, BatchStatus,
    Observation, ActivityCard,
    AppSite
)
from core.llm_provider import DayflowBackendProvider
from database.storage import StorageManager

logger = logging.getLogger(__name__)


class AnalysisScheduler:
    """
    分析调度器
    - 定时扫描待分析的视频切片
    - 打包成批次发送给 API
    - 将结果存入数据库
    """
    
    def __init__(
        self,
        storage: Optional[StorageManager] = None,
        provider: Optional[DayflowBackendProvider] = None,
        batch_chunk_count: int = None,
        scan_interval_seconds: int = None
    ):
        self.storage = storage or StorageManager()
        self.provider = provider or DayflowBackendProvider()
        self.batch_chunk_count = batch_chunk_count or config.BATCH_CHUNK_COUNT
        self.scan_interval = scan_interval_seconds or config.ANALYSIS_INTERVAL_SECONDS
        
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 用于触发立即扫描的事件
        self._scan_event = threading.Event()
        
        # 事件循环（用于异步 API 调用）
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行")
            return
        
        logger.info("启动分析调度器...")
        
        self._running = True
        self._stop_event.clear()
        
        # 创建新的事件循环
        self._loop = asyncio.new_event_loop()
        
        # 启动调度线程
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        logger.info(f"调度器已启动 - 扫描间隔: {self.scan_interval}秒, 批次大小: {self.batch_chunk_count}个切片")
    
    def stop(self):
        """停止调度器"""
        if not self._running:
            return
        
        logger.info("停止分析调度器...")
        
        self._stop_event.set()
        self._running = False
        
        # 使用较短的超时时间，避免阻塞太久
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=2)
            if self._scheduler_thread.is_alive():
                logger.warning("调度器线程未能在超时内停止")
        
        # 安全关闭事件循环
        if self._loop:
            try:
                if self._loop.is_running():
                    self._loop.call_soon_threadsafe(self._loop.stop)
                if not self._loop.is_closed():
                    self._loop.close()
            except Exception as e:
                logger.warning(f"关闭事件循环时出错: {e}")
            self._loop = None
        
        logger.info("调度器已停止")
    
    def _scheduler_loop(self):
        """调度主循环"""
        asyncio.set_event_loop(self._loop)
        
        while not self._stop_event.is_set():
            try:
                # 扫描并处理，返回是否处理了内容
                processed = self._loop.run_until_complete(self._scan_and_process())
                
                # 每次循环都检查是否需要立即扫描
                if self._scan_event.is_set():
                    self._scan_event.clear()
                    # 如果触发立即扫描，不等待，直接继续下一次循环
                    continue
                
                # 只有没有处理任何内容时才等待定时间隔
                if not processed:
                    # 等待定时间隔，但每秒检查一次扫描事件
                    waited = 0
                    while waited < self.scan_interval:
                        sleep_time = min(1.0, self.scan_interval - waited)
                        self._stop_event.wait(sleep_time)
                        waited += sleep_time
                        
                        # 如果触发立即扫描，提前结束等待
                        if self._scan_event.is_set():
                            self._scan_event.clear()
                            break
            except Exception as e:
                logger.error(f"调度循环错误: {e}")
                self._stop_event.wait(self.scan_interval)
    
    async def _scan_and_process(self) -> bool:
        """扫描并处理待分析的切片
        
        Returns:
            bool: 是否处理了任何切片
        """
        # 获取待分析的切片
        pending_chunks = self.storage.get_pending_chunks()
        
        if not pending_chunks:
            logger.debug("没有待分析的切片")
            return False
        
        logger.info(f"发现 {len(pending_chunks)} 个待分析切片")
        
        # 将切片打包成批次
        batches = self._create_batches(pending_chunks)
        
        if not batches:
            logger.debug(f"待分析切片不足 {self.batch_chunk_count} 个，等待更多切片...")
            return False
        
        logger.info(f"已打包 {len(batches)} 个批次，开始处理...")
        
        for i, batch_chunks in enumerate(batches, 1):
            if self._stop_event.is_set():
                break
            
            try:
                logger.info(f"处理批次 {i}/{len(batches)} ({len(batch_chunks)} 个切片)")
                await self._process_batch(batch_chunks)
            except Exception as e:
                logger.error(f"处理批次 {i}/{len(batches)} 失败: {e}")
        
        return True
    
    def _create_batches(self, chunks: List[VideoChunk]) -> List[List[VideoChunk]]:
        """将切片分组为批次
        
        批次形成条件：
        - 切片数量达到配置的批次大小时形成一个批次
        - 遇到新的日期（跨日）时强制结束当前批次
        - 时间间隔不再作为批次形成的条件（避免用户休息时中断）
        """
        if not chunks:
            return []
        
        batches = []
        current_batch = []
        min_chunks = self.batch_chunk_count  # 最小切片数量
        last_date = None  # 记录上一个切片的日期
        
        for chunk in chunks:
            # 检查日期是否变化
            chunk_date = chunk.start_time.date() if chunk.start_time else None
            
            # 如果当前批次不为空，且遇到新的日期，强制结束当前批次
            if current_batch and last_date and chunk_date and chunk_date != last_date:
                logger.info(f"检测到日期变化：{last_date} -> {chunk_date}，强制结束当前批次（{len(current_batch)} 个切片）")
                batches.append(current_batch)
                current_batch = []
            
            current_batch.append(chunk)
            last_date = chunk_date
            
            # 只有当切片数量达到配置的大小时，才形成一个批次
            if len(current_batch) >= min_chunks:
                batches.append(current_batch)
                current_batch = []
                last_date = None  # 重置日期记录
        
        # 剩余切片暂时不形成批次，等待更多切片
        # 录制停止时会通过 analyze_remaining_chunks() 强制分析所有剩余切片
        
        return batches
    
    def trigger_scan(self):
        """立即触发扫描（在切片保存后调用，无需等待定时间隔）"""
        if self._running and self._loop and not self._stop_event.is_set():
            logger.debug("触发立即扫描")
            self._scan_event.set()
    
    async def _process_batch(self, chunks: List[VideoChunk]):
        """处理单个批次"""
        if not chunks:
            return
        
        # 创建批次记录
        batch = AnalysisBatch(
            chunk_ids=[c.id for c in chunks if c.id],
            start_time=chunks[0].start_time,
            end_time=chunks[-1].end_time,
            status=BatchStatus.PENDING
        )
        batch_id = self.storage.create_batch(batch)
        
        # 更新切片状态
        for chunk in chunks:
            if chunk.id:
                self.storage.update_chunk_status(chunk.id, ChunkStatus.PROCESSING, batch_id)
        
        try:
            # 更新批次状态为处理中
            self.storage.update_batch(batch_id, BatchStatus.PROCESSING)
            
            # 转录所有切片
            all_observations = []
            chunk_card_start_times = {}  # 存储每个切片的卡片开始时间
            all_window_records = []  # 存储所有窗口记录，用于计算app_sites时长
            
            for chunk in chunks:
                if not Path(chunk.file_path).exists():
                    logger.warning(f"切片文件不存在: {chunk.file_path}")
                    continue
                
                # 读取窗口记录
                window_records = None
                if chunk.window_records_path:
                    window_records_file = Path(chunk.window_records_path)
                    if window_records_file.exists():
                        try:
                            import json
                            with open(window_records_file, 'r', encoding='utf-8') as f:
                                window_records = json.load(f)
                            logger.debug(f"已加载 {len(window_records)} 条窗口记录")
                            
                            # 提取卡片开始时间
                            if isinstance(window_records, list) and len(window_records) > 0:
                                first_record = window_records[0]
                                if isinstance(first_record, dict) and first_record.get("event") == "card_start":
                                    card_start_time_str = first_record.get("card_start_time")
                                    if card_start_time_str:
                                        try:
                                            from datetime import datetime
                                            card_start_time = datetime.fromisoformat(card_start_time_str)
                                            chunk_card_start_times[chunk.id] = card_start_time
                                            logger.debug(f"从窗口记录提取卡片开始时间: {card_start_time}")
                                        except Exception as e:
                                            logger.warning(f"解析卡片开始时间失败: {e}")
                        except Exception as e:
                            logger.warning(f"读取窗口记录失败: {e}")
                
                observations = await self.provider.transcribe_video(
                    chunk.file_path,
                    chunk.duration_seconds,
                    window_records=window_records
                )
                
                # 保存窗口记录用于后续计算app_sites时长
                if window_records:
                    all_window_records.extend(window_records)
                
                # 调整时间戳（相对于批次开始时间）
                if chunk.start_time and batch.start_time:
                    offset = (chunk.start_time - batch.start_time).total_seconds()
                    for obs in observations:
                        obs.start_ts += offset
                        obs.end_ts += offset
                
                all_observations.extend(observations)
            
            if not all_observations:
                logger.warning(f"批次 {batch_id} 没有生成任何观察记录")
                self.storage.update_batch(batch_id, BatchStatus.COMPLETED, "[]")
                return
            
            # 获取上下文（最近且与当前批次时间相邻的卡片）
            # 只获取当前批次开始时间之前最近的一张卡片
            if batch.start_time:
                context_cards = self.storage.get_cards_before_time(
                    batch.start_time, 
                    limit=3
                )
            else:
                context_cards = []
            
            # 生成活动卡片
            cards = await self.provider.generate_activity_cards(
                all_observations,
                context_cards,
                start_time=batch.start_time
            )
            
            # 设置卡片开始时间和结束时间
            # 第一张卡片的开始时间 = 录制开始时间（仅当数据库中没有任何卡片时）
            # 其他卡片的开始时间 = 上一张卡片的结束时间
            # 每张卡片的结束时间 = 批次开始时间 + AI返回的相对时间（最后一张卡片使用chunk结束时间）
            
            # 检查是否是全局第一张卡片（数据库中没有任何卡片）
            recent_cards = self.storage.get_recent_cards(limit=1)
            is_first_card = len(recent_cards) == 0
            
            if is_first_card:
                # 第一张卡片：使用录制开始时间
                recording_start_time_str = self.storage.get_setting("recording_start_time", "")
                if recording_start_time_str:
                    try:
                        current_card_start_time = datetime.fromisoformat(recording_start_time_str)
                        logger.info(f"全局第一张卡片：使用录制开始时间 {current_card_start_time}")
                    except Exception as e:
                        logger.warning(f"解析录制开始时间失败: {e}，使用批次开始时间")
                        if batch.start_time:
                            current_card_start_time = batch.start_time
                        else:
                            logger.error("无法确定第一张卡片的开始时间，跳过此批次")
                            self.storage.update_batch(batch_id, BatchStatus.COMPLETED, "[]")
                            return
                elif batch.start_time:
                    current_card_start_time = batch.start_time
                    logger.info(f"全局第一张卡片：使用批次开始时间 {current_card_start_time}")
                else:
                    logger.error("无法确定第一张卡片的开始时间，跳过此批次")
                    self.storage.update_batch(batch_id, BatchStatus.COMPLETED, "[]")
                    return
            else:
                # 非第一张卡片：使用前一张卡片的结束时间
                last_card = recent_cards[-1]
                if last_card.end_time:
                    current_card_start_time = last_card.end_time
                    logger.info(f"非第一张卡片：使用前一张卡片的结束时间 {current_card_start_time}")
                elif batch.start_time:
                    current_card_start_time = batch.start_time
                    logger.warning(f"前一张卡片无结束时间，使用批次开始时间 {current_card_start_time}")
                else:
                    logger.error("无法确定卡片开始时间，跳过此批次")
                    self.storage.update_batch(batch_id, BatchStatus.COMPLETED, "[]")
                    return
            
            # 设置每张卡片的开始时间和结束时间
            for idx, card in enumerate(cards):
                # 设置卡片开始时间
                card.start_time = current_card_start_time
                logger.debug(f"卡片 {idx + 1} 开始时间: {card.start_time}")
                
                # 设置卡片结束时间
                if hasattr(card, '_relative_end') and card._relative_end is not None:
                    # AI返回了相对时间
                    if idx < len(cards) - 1:
                        # 非最后一张卡片：使用AI返回的相对时间
                        card._next_card_start_time = batch.start_time + timedelta(seconds=card._relative_end)
                        logger.debug(f"卡片 {idx + 1} 结束时间（从AI相对时间转换）: {card._relative_end}s -> {card._next_card_start_time}")
                    else:
                        # 最后一张卡片：强制使用最后一个chunk的结束时间（等于录制停止时间）
                        if chunks and chunks[-1].end_time:
                            card._next_card_start_time = chunks[-1].end_time
                            logger.debug(f"最后一张卡片：使用chunk结束时间 {card._next_card_start_time}（忽略AI相对时间 {card._relative_end}s）")
                        elif batch.end_time:
                            card._next_card_start_time = batch.end_time
                            logger.debug(f"最后一张卡片：使用批次结束时间 {card._next_card_start_time}（忽略AI相对时间 {card._relative_end}s）")
                        else:
                            logger.warning(f"最后一张卡片：无法确定结束时间，使用AI相对时间 {card._relative_end}s")
                            card._next_card_start_time = batch.start_time + timedelta(seconds=card._relative_end)
                else:
                    # AI没有返回相对时间，跳过此卡片
                    logger.warning(f"卡片 {idx + 1}：AI未返回结束时间，跳过此卡片")
                    continue
                
                # 为下一张卡片更新开始时间
                current_card_start_time = card._next_card_start_time
            
            # 根据窗口记录精确计算每张卡片的app_sites时长
            if all_window_records and batch.start_time:
                for idx, card in enumerate(cards):
                    if card.start_time and card._next_card_start_time:
                        app_durations = self._calculate_app_durations(
                            all_window_records, 
                            card.start_time, 
                            card._next_card_start_time,
                            batch.start_time
                        )
                        
                        # 更新卡片的app_sites
                        updated_app_sites = []
                        for app_site in card.app_sites:
                            app_name = app_site.name
                            duration = app_durations.get(app_name, 0)
                            updated_app_sites.append(AppSite(
                                name=app_name,
                                duration_seconds=duration
                            ))
                        
                        card.app_sites = updated_app_sites
                        logger.debug(f"卡片 {idx + 1} 应用时长计算完成: {app_durations}")
            
            # 验证卡片时间连续性
            valid_cards = []
            for idx, card in enumerate(cards):
                if not card.start_time or not card._next_card_start_time:
                    logger.warning(f"卡片 {idx + 1} 时间信息不完整（start_time={card.start_time}, end_time={card._next_card_start_time}），跳过此卡片")
                    continue
                if card._next_card_start_time <= card.start_time:
                    logger.warning(f"卡片 {idx + 1} 时间不合理（开始时间 {card.start_time} >= 结束时间 {card._next_card_start_time}），跳过此卡片")
                    continue
                valid_cards.append(card)
            
            logger.info(f"卡片时间验证通过：{len(valid_cards)}/{len(cards)} 张卡片")
            
            # 保存有效卡片
            for card in valid_cards:
                self.storage.save_card(card, batch_id)
            
            # 更新状态
            import json
            observations_json = json.dumps([o.to_dict() for o in all_observations])
            self.storage.update_batch(batch_id, BatchStatus.COMPLETED, observations_json)
            
            for chunk in chunks:
                if chunk.id:
                    self.storage.update_chunk_status(chunk.id, ChunkStatus.COMPLETED)
            
            logger.info(f"批次 {batch_id} 处理完成 - 生成 {len(valid_cards)} 张卡片")
            
            # 分析完成后删除视频切片文件（节省磁盘空间）
            if config.AUTO_DELETE_ANALYZED_CHUNKS:
                self._delete_chunk_files(chunks)
            
        except Exception as e:
            logger.error(f"批次 {batch_id} 处理失败: {e}")
            
            self.storage.update_batch(batch_id, BatchStatus.FAILED, error_message=str(e))
            
            for chunk in chunks:
                if chunk.id:
                    self.storage.update_chunk_status(chunk.id, ChunkStatus.FAILED)
            
            raise
    
    def _validate_and_fix_card_continuity(self, cards: List[ActivityCard], previous_card: Optional[ActivityCard] = None) -> None:
        """
        验证并修复卡片时间连续性
        
        验证规则：
        1. 每张卡片的结束时间必须晚于开始时间
        2. 每张卡片的结束时间必须早于或等于下一张卡片的开始时间
        3. 当前批次的第一张卡片必须与上一批次的最后一张卡片保持时间连续性
        
        修复规则：
        - 如果卡片结束时间 > 下一张卡片的开始时间，将结束时间修正为下一张卡片的开始时间
        - 如果卡片结束时间 <= 开始时间，删除该卡片（记录警告）
        - 如果上一张卡片的结束时间 > 当前卡片的开始时间，更新上一张卡片的结束时间
        
        Args:
            cards: 待验证和修复的卡片列表（会被原地修改）
            previous_card: 上一批次的最后一张卡片，用于验证批次边界的时间连续性
        """
        if not cards:
            return
        
        cards_to_remove = []
        
        # 验证当前批次的第一张卡片与上一批次最后一张卡片的连续性
        if previous_card and cards and len(cards) > 0:
            first_card = cards[0]
            
            # 检查previous_card的结束时间是否已设置
            if previous_card._next_card_start_time and first_card.start_time:
                if previous_card._next_card_start_time > first_card.start_time:
                    # 上一张卡片的结束时间晚于当前卡片的开始时间，存在时间重叠
                    logger.warning(
                        f"批次边界时间重叠：上一张卡片 ({previous_card.title}) 的结束时间 {previous_card._next_card_start_time} "
                        f"晚于当前批次第一张卡片 ({first_card.title}) 的开始时间 {first_card.start_time}，修正上一张卡片的结束时间"
                    )
                    
                    # 更新上一张卡片的结束时间
                    old_end_time = previous_card._next_card_start_time
                    previous_card._next_card_start_time = first_card.start_time
                    
                    # 计算修正后的持续时间
                    corrected_duration = (previous_card._next_card_start_time - previous_card.start_time).total_seconds() / 60
                    logger.info(
                        f"已修正上一张卡片 {previous_card.id} ({previous_card.title}) 的结束时间: "
                        f"{old_end_time} -> {previous_card._next_card_start_time} "
                        f"(持续时间: {corrected_duration:.1f}分钟)"
                    )
                    
                    # 更新数据库
                    if previous_card.id:
                        success = self.storage.update_card(
                            previous_card.id,
                            end_time=previous_card._next_card_start_time
                        )
                        if not success:
                            logger.error(f"更新上一张卡片 {previous_card.id} 的结束时间失败")
        
        for i, card in enumerate(cards):
            # 检查卡片的结束时间是否设置
            if card._next_card_start_time is None:
                logger.warning(f"卡片 {i+1} 的结束时间未设置，跳过验证")
                continue
            
            # 检查卡片的开始时间是否设置
            if card.start_time is None:
                logger.warning(f"卡片 {i+1} 的开始时间未设置，跳过验证")
                continue
            
            # 检查卡片结束时间是否晚于开始时间
            if card._next_card_start_time <= card.start_time:
                logger.warning(
                    f"卡片 {i+1} 的结束时间 ({card._next_card_start_time}) 不晚于开始时间 ({card.start_time})，"
                    f"标记为删除"
                )
                cards_to_remove.append(card)
                continue
            
            # 检查与下一张卡片的时间连续性
            if i < len(cards) - 1:
                next_card = cards[i + 1]
                if next_card.start_time is None:
                    logger.warning(f"卡片 {i+2} 的开始时间未设置，跳过连续性检查")
                    continue
                
                if card._next_card_start_time > next_card.start_time:
                    # 时间重叠，修正结束时间为下一张卡片的开始时间
                    logger.warning(
                        f"卡片 {i+1} 的结束时间 ({card._next_card_start_time}) "
                        f"晚于卡片 {i+2} 的开始时间 ({next_card.start_time})，存在时间重叠，修正结束时间"
                    )
                    
                    old_end_time = card._next_card_start_time
                    card._next_card_start_time = next_card.start_time
                    
                    # 计算修正后的持续时间
                    corrected_duration = (card._next_card_start_time - card.start_time).total_seconds() / 60
                    logger.info(
                        f"已修正卡片 {i+1} ({card.title}) 的结束时间: "
                        f"{old_end_time} -> {card._next_card_start_time} "
                        f"(持续时间: {corrected_duration:.1f}分钟)"
                    )
        
        # 移除需要删除的卡片
        for card in cards_to_remove:
            if card in cards:
                cards.remove(card)
    
    def analyze_remaining_chunks(self):
        """强制分析所有未分析的切片（录制停止时调用）
        
        此方法不等待凑够15个切片，直接分析所有待分析的切片
        确保录制结束时最后的工作也能被记录
        """
        logger.info("========== 开始强制分析剩余切片 ==========")
        
        # 获取所有待分析的切片
        pending_chunks = self.storage.get_pending_chunks()
        
        if not pending_chunks:
            logger.info("没有待分析的切片")
            return
        
        logger.info(f"发现 {len(pending_chunks)} 个待分析切片，开始强制分析")
        for i, chunk in enumerate(pending_chunks[:5]):  # 只打印前5个
            logger.info(f"  切片{i+1}: ID={chunk.id}, 开始={chunk.start_time.strftime('%H:%M:%S')}, 结束={chunk.end_time.strftime('%H:%M:%S')}, 时长={chunk.duration_seconds:.1f}秒")
        if len(pending_chunks) > 5:
            logger.info(f"  ... 还有 {len(pending_chunks)-5} 个切片")
        
        # 直接将所有切片作为一个批次处理
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._process_batch(pending_chunks))
                logger.info(f"========== 剩余切片分析完成，共处理 {len(pending_chunks)} 个切片 ==========")
            finally:
                if not loop.is_closed():
                    loop.close()
        except Exception as e:
            logger.error(f"强制分析剩余切片失败: {e}")
            raise
    
    def _calculate_app_durations(
        self,
        window_records: List[dict],
        card_start_time: datetime,
        card_end_time: datetime,
        batch_start_time: datetime
    ) -> dict:
        """
        根据窗口记录计算卡片时间范围内每个应用的时长
        
        Args:
            window_records: 窗口记录列表
            card_start_time: 卡片开始时间
            card_end_time: 卡片结束时间
            batch_start_time: 批次开始时间（用于计算相对时间）
            
        Returns:
            dict: 应用名称到时长的映射（单位：秒）
        """
        app_durations = {}
        
        if not window_records:
            return app_durations
        
        # 计算卡片时间范围（相对于批次开始时间）
        card_start_offset = (card_start_time - batch_start_time).total_seconds()
        card_end_offset = (card_end_time - batch_start_time).total_seconds()
        
        # 按时间排序窗口记录
        sorted_records = [r for r in window_records if "app_name" in r or "event" in r]
        
        for i in range(len(sorted_records)):
            current_record = sorted_records[i]
            
            # 跳过特殊事件记录
            if current_record.get("event") in ["card_start", "card_end"]:
                continue
            
            # 获取当前记录的app_name
            app_name = current_record.get("app_name")
            if not app_name:
                continue
            
            # 获取当前记录的时间戳
            current_timestamp = current_record.get("timestamp", 0)
            
            # 确定时间窗口的结束时间
            if i < len(sorted_records) - 1:
                next_record = sorted_records[i + 1]
                next_timestamp = next_record.get("timestamp", 0)
                
                # 如果下一条是特殊事件，跳到再下一条
                if next_record.get("event") in ["card_start", "card_end"] and i + 2 < len(sorted_records):
                    next_record = sorted_records[i + 2]
                    next_timestamp = next_record.get("timestamp", 0)
            else:
                # 最后一条记录，使用批次结束时间
                next_timestamp = sorted_records[-1].get("timestamp", 0)
                if next_timestamp <= current_timestamp:
                    # 如果没有下一条记录的时间戳，假设持续到卡片结束
                    next_timestamp = card_end_offset
            
            # 计算当前记录的持续时间
            duration = next_timestamp - current_timestamp
            
            # 检查时间窗口是否与卡片时间范围有重叠
            if next_timestamp <= card_start_offset or current_timestamp >= card_end_offset:
                # 没有重叠，跳过
                continue
            
            # 计算重叠部分
            overlap_start = max(current_timestamp, card_start_offset)
            overlap_end = min(next_timestamp, card_end_offset)
            overlap_duration = max(0, overlap_end - overlap_start)
            
            # 累加应用时长
            if app_name not in app_durations:
                app_durations[app_name] = 0
            app_durations[app_name] += overlap_duration
        
        return app_durations
    
    def _delete_chunk_files(self, chunks: List[VideoChunk]):
        """
        删除已分析完成的视频切片文件和窗口记录文件
        只在分析成功后调用，确保数据已保存到数据库
        """
        deleted_count = 0
        for chunk in chunks:
            try:
                # 删除视频文件
                chunk_path = Path(chunk.file_path)
                if chunk_path.exists():
                    chunk_path.unlink()
                    deleted_count += 1
                    logger.debug(f"已删除视频切片: {chunk_path.name}")
                
                # 删除窗口记录文件
                if chunk.window_records_path:
                    window_records_path = Path(chunk.window_records_path)
                    if window_records_path.exists():
                        window_records_path.unlink()
                        logger.debug(f"已删除窗口记录: {window_records_path.name}")
            except Exception as e:
                logger.warning(f"删除文件失败 {chunk.file_path}: {e}")
        
        if deleted_count > 0:
            logger.info(f"已清理 {deleted_count} 个视频切片文件")
    
    async def process_immediately(self):
        """立即处理所有待分析的切片（手动触发）"""
        await self._scan_and_process()


class AnalysisManager:
    """
    分析管理器
    整合调度器和手动触发功能
    """
    
    def __init__(self, storage: Optional[StorageManager] = None):
        self.storage = storage or StorageManager()
        self.scheduler = AnalysisScheduler(storage=self.storage)
    
    def start_scheduler(self):
        """启动自动调度"""
        self.scheduler.start()
    
    def stop_scheduler(self):
        """停止自动调度"""
        self.scheduler.stop()
    
    def analyze_now(self):
        """立即分析（同步）"""
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.scheduler.process_immediately())
        finally:
            loop.close()
    
    @property
    def is_running(self) -> bool:
        return self.scheduler.is_running
