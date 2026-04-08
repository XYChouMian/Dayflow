"""
健康提醒系统 - 优先级修复版本
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ReminderType(Enum):
    WORK_TOO_LONG = "work_too_long"
    ENTERTAINMENT_TOO_LONG = "entertainment_too_long"

@dataclass
class ReminderResult:
    type: ReminderType
    total_minutes: float
    message: str
    category: str

@dataclass
class ActivitySession:
    category: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    productivity_score: float
    
    @property
    def duration_minutes(self) -> float:
        """计算会话持续时间（分钟）"""
        if not self.start_time or not self.end_time:
            return 0.0
        
        duration = self.end_time - self.start_time
        return duration.total_seconds() / 60
    
    def is_work_activity(self) -> bool:
        """判断是否为工作活动"""
        return self.category in WORK_CATEGORIES
    
    def is_entertainment_activity(self) -> bool:
        """判断是否为娱乐活动"""
        return self.category in ENTERTAINMENT_CATEGORIES

# 活动类别定义
WORK_CATEGORIES = {
    "工作", "编程", "学习", "会议", "开发", "写作", 
    "Work", "Programming", "Study", "Meeting", "Development", "Writing"
}

ENTERTAINMENT_CATEGORIES = {
    "娱乐", "游戏", "社交", "休息", "视频", "音乐", 
    "Entertainment", "Game", "Social", "Break", "Video", "Music"
}

def _now_local() -> datetime:
    """获取当前本地时间"""
    return datetime.now()

class HealthReminder:
    def __init__(self, storage=None):
        self.storage = storage
        self.work_threshold_minutes = 90
        self.entertainment_threshold_minutes = 60
        self.cooldown_minutes = 15
        self.strength = "moderate"
        self.gap_threshold_minutes = 5
        self.session_gap_threshold_minutes = 5
        self.ignore_short_interruption_minutes = 3
        self._last_reminder_time = None
        self._config_loaded = False
        
        # 初始化后加载配置
        self._load_config()
    
    def _load_config(self):
        """从配置管理器加载配置"""
        if not self.storage:
            return
        
        try:
            # 从存储中读取配置
            work_threshold = self.storage.get_setting("health_work_threshold", "90")
            entertainment_threshold = self.storage.get_setting("health_entertainment_threshold", "60")
            cooldown = self.storage.get_setting("health_cooldown", "15")
            strength = self.storage.get_setting("health_strength", "moderate")
            enabled = self.storage.get_setting("health_reminder_enabled", "true") == "true"
            
            # 更新配置值
            self.work_threshold_minutes = int(work_threshold)
            self.entertainment_threshold_minutes = int(entertainment_threshold)
            self.cooldown_minutes = int(cooldown)
            self.strength = strength
            
            # 如果健康提醒被禁用，设置一个很大的阈值使其不会触发
            if not enabled:
                self.work_threshold_minutes = 999999
                self.entertainment_threshold_minutes = 999999
            
            self._config_loaded = True
            logger.info(f"健康提醒配置已加载: 工作={self.work_threshold_minutes}分钟, 娱乐={self.entertainment_threshold_minutes}分钟, 冷却={self.cooldown_minutes}分钟, 强度={self.strength}")
            
        except Exception as e:
            logger.error(f"加载健康提醒配置失败: {e}")
            # 使用默认值
            self.work_threshold_minutes = 90
            self.entertainment_threshold_minutes = 60
            self.cooldown_minutes = 15
            self.strength = "moderate"
    
    def update_config(self, work_threshold: int, entertainment_threshold: int, cooldown: int, strength: str):
        """更新配置并保存到存储"""
        if not self.storage:
            return
        
        try:
            # 保存到存储
            self.storage.set_setting("health_work_threshold", str(work_threshold))
            self.storage.set_setting("health_entertainment_threshold", str(entertainment_threshold))
            self.storage.set_setting("health_cooldown", str(cooldown))
            self.storage.set_setting("health_strength", strength)
            self.storage.set_setting("health_reminder_enabled", "true")
            
            # 更新本地配置
            self.work_threshold_minutes = work_threshold
            self.entertainment_threshold_minutes = entertainment_threshold
            self.cooldown_minutes = cooldown
            self.strength = strength
            
            # 重置提醒时间，使新配置立即生效
            self._last_reminder_time = None
            
            logger.info(f"健康提醒配置已更新: 工作={work_threshold}分钟, 娱乐={entertainment_threshold}分钟, 冷却={cooldown}分钟, 强度={strength}")
            
        except Exception as e:
            logger.error(f"更新健康提醒配置失败: {e}")
    
    def should_notify(self) -> Optional[Dict[str, str]]:
        """
        检查是否需要发送提醒
        
        Returns:
            None 或包含提醒信息的字典
        """
        try:
            cards = self.storage.get_recent_cards(limit=100)
            
            if not cards:
                logger.info("健康提醒检查: 没有活动卡片数据")
                return None
            
            if self._is_in_cooldown():
                effective_cooldown = self._get_effective_cooldown()
                elapsed = (_now_local() - self._last_reminder_time).total_seconds() / 60
                remaining = effective_cooldown - int(elapsed)
                logger.info(f"健康提醒检查: 在冷却期中，剩余 {remaining} 分钟")
                return None
            
            result = self.analyze_activities(cards)
            if result:
                return {
                    "type": result.type.value,
                    "title": self._get_title(result.type),
                    "message": result.message
                }
            else:
                logger.info("健康提醒检查: 当前活动未达到提醒阈值")
        except Exception as e:
            logger.error(f"检查健康提醒失败: {e}")
        
        return None
    
    def _is_in_cooldown(self) -> bool:
        """检查是否在冷却期"""
        if not self._last_reminder_time:
            return False
        
        effective_cooldown = self._get_effective_cooldown()
        elapsed = _now_local() - self._last_reminder_time
        return elapsed.total_seconds() < effective_cooldown * 60
    
    def _filter_recent_cards(self, cards: List[Any], hours: int = 6) -> List[Any]:
        """过滤最近几小时的卡片"""
        cutoff = _now_local() - timedelta(hours=hours)
        recent = []
        for card in cards:
            if hasattr(card, 'start_time') and card.start_time:
                # 移除时区信息以进行比较
                card_time = card.start_time
                if card_time.tzinfo is not None:
                    card_time = card_time.replace(tzinfo=None)
                if card_time >= cutoff:
                    recent.append(card)
        return recent
    
    def analyze_activities(self, cards: List[Any]) -> Optional[ReminderResult]:
        """分析活动并返回提醒结果"""
        try:
            logger.info(f"健康提醒分析: 输入卡片数量={len(cards)}")
            
            # 过滤最近6小时的卡片
            recent_cards = self._filter_recent_cards(cards, hours=6)
            logger.info(f"健康提醒分析: 最近6小时内有 {len(recent_cards)} 张卡片")
            
            if not recent_cards:
                logger.info("健康提醒分析: 最近6小时内没有活动卡片")
                return None
            
            sessions = self._build_sessions(recent_cards)
            logger.info(f"健康提醒分析: 构建了 {len(sessions)} 个活动会话")
            
            if not sessions:
                logger.info("健康提醒分析: 没有有效的活动会话")
                return None
            
            now = _now_local()
            current_session = self._get_current_session(sessions, now)
            
            # 优先检查娱乐会话，因为娱乐提醒通常更紧急
            # 按照优先级顺序检查：娱乐会话 > 工作会话 > 其他会话
            priority_order = []
            
            # 添加娱乐会话到优先级列表
            entertainment_sessions = [s for s in sessions if s.is_entertainment_activity()]
            priority_order.extend(entertainment_sessions)
            
            # 添加工作会话到优先级列表
            work_sessions = [s for s in sessions if s.is_work_activity()]
            priority_order.extend(work_sessions)
            
            # 添加其他会话到优先级列表
            other_sessions = [s for s in sessions if not s.is_entertainment_activity() and not s.is_work_activity()]
            priority_order.extend(other_sessions)
            
            # 检查优先级列表中的会话
            result = None
            for session in priority_order:
                logger.info(f"健康提醒分析: 检查会话类别={session.category}, 持续时间={session.duration_minutes:.0f}分钟")
                session_result = self._check_threshold(session)
                if session_result:
                    result = session_result
                    self._last_reminder_time = now
                    logger.info(f"健康提醒触发: {session_result.type.value}, 时长: {session_result.total_minutes:.0f}分钟")
                    break
            
            if result:
                return result
            
            # 如果没有触发提醒，记录当前会话状态
            if current_session:
                logger.info(f"健康提醒分析: 当前活动类别={current_session.category}, 已持续时长={current_session.duration_minutes:.0f}分钟")
                effective_work, effective_entertainment = self._get_effective_thresholds()
                if current_session.category in WORK_CATEGORIES:
                    logger.info(f"健康提醒分析: 工作时长 {current_session.duration_minutes:.0f}分钟未达到阈值 {effective_work}分钟")
                elif current_session.category in ENTERTAINMENT_CATEGORIES:
                    logger.info(f"健康提醒分析: 娱乐时长 {current_session.duration_minutes:.0f}分钟未达到阈值 {effective_entertainment}分钟")
            
            return result
            
        except Exception as e:
            logger.error(f"健康提醒分析失败: {e}")
            return None
    
    def _build_sessions(self, cards: List[Any]) -> List[ActivitySession]:
        """构建活动会话（改进的鲁棒性会话合并）"""
        if not cards:
            return []
        
        def normalize_time(dt):
            """移除时区信息"""
            if dt and dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt
        
        # 过滤和预处理卡片
        processed_cards = []
        for card in cards:
            if not hasattr(card, 'category') or not card.category:
                continue
            
            # 验证和修复时间戳
            start_time = self._validate_and_fix_time(
                getattr(card, 'start_time', None), 
                default_type='start'
            )
            end_time = self._validate_and_fix_time(
                getattr(card, 'end_time', None), 
                default_type='end',
                reference_time=start_time
            )
            
            if start_time and end_time:
                processed_cards.append({
                    'card': card,
                    'category': card.category,
                    'start_time': start_time,
                    'end_time': end_time,
                    'productivity_score': getattr(card, 'productivity_score', 0)
                })
        
        if not processed_cards:
            return []
        
        # 按开始时间排序
        sorted_cards = sorted(processed_cards, key=lambda c: c['start_time'])
        
        sessions = []
        current_session = None
        
        for card_data in sorted_cards:
            card = card_data['card']
            category = card_data['category']
            start_time = card_data['start_time']
            end_time = card_data['end_time']
            productivity_score = card_data['productivity_score']
            
            if current_session is None:
                current_session = ActivitySession(
                    category=category,
                    start_time=start_time,
                    end_time=end_time,
                    productivity_score=productivity_score
                )
            else:
                # 检查是否应该合并会话
                if self._should_merge_sessions(current_session, card_data):
                    current_session.end_time = end_time
                    # 计算平均生产力分数
                    avg_score = (current_session.productivity_score + productivity_score) / 2
                    current_session.productivity_score = avg_score
                else:
                    # 检查是否应该忽略短时间打断
                    if self._should_ignore_interruption(current_session, card_data):
                        current_session.end_time = end_time
                    else:
                        sessions.append(current_session)
                        current_session = ActivitySession(
                            category=category,
                            start_time=start_time,
                            end_time=end_time,
                            productivity_score=productivity_score
                        )
        
        if current_session:
            sessions.append(current_session)
        
        return sessions
    
    def _validate_and_fix_time(self, dt, default_type='start', reference_time=None):
        """验证和修复时间戳"""
        if not dt:
            if default_type == 'start' and reference_time:
                # 如果是开始时间缺失，使用参考时间的前5分钟
                return reference_time - timedelta(minutes=5)
            elif default_type == 'end' and reference_time:
                # 如果是结束时间缺失，使用参考时间的后5分钟
                return reference_time + timedelta(minutes=5)
            else:
                # 使用当前时间
                return _now_local()
        
        # 移除时区信息
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        
        # 检查时间合理性
        now = _now_local()
        if dt > now + timedelta(hours=24):
            # 如果时间在未来超过24小时，使用当前时间
            return now
        elif dt < now - timedelta(days=7):
            # 如果时间在过去超过7天，使用当前时间
            return now
        
        return dt
    
    def _should_merge_sessions(self, session: ActivitySession, card_data: dict) -> bool:
        """判断是否应该合并会话（修复版 - 防止游戏被合并到工作会话）"""
        card_category = card_data['category']
        card_start_time = card_data['start_time']
        card_end_time = card_data['end_time']
        
        # 如果类别相同，直接合并
        if session.category == card_category:
            return self._check_time_gap(session, card_data)
        
        # 如果是工作会话，不允许合并娱乐活动（防止游戏被合并到工作会话）
        if session.is_work_activity():
            # 只允许合并短暂的工作相关中断（如喝水、上厕所）
            if card_category in ENTERTAINMENT_CATEGORIES:
                # 娱乐活动不应该被合并到工作会话中
                return False
            # 允许短暂的工作相关中断（如短暂沟通）
            gap = (card_start_time - session.end_time).total_seconds() / 60
            return gap <= self.gap_threshold_minutes  # 严格限制为5分钟
        
        # 如果是娱乐会话，不允许合并工作活动
        if session.is_entertainment_activity():
            return False
        
        return False
    
    def _check_time_gap(self, session: ActivitySession, card_data: dict) -> bool:
        """检查时间间隔是否允许合并"""
        if not session.end_time or not card_data['start_time']:
            return False
        
        gap = (card_data['start_time'] - session.end_time).total_seconds() / 60
        return gap <= self.gap_threshold_minutes * 5  # 进一步扩大容错窗口
    
    def _should_ignore_interruption(self, session: ActivitySession, card_data: dict) -> bool:
        """判断是否应该忽略打断（改进版）"""
        card_category = card_data['category']
        card_start_time = card_data['start_time']
        card_end_time = card_data['end_time']
        
        # 工作期间的短暂打断
        if session.is_work_activity() and card_category in ENTERTAINMENT_CATEGORIES:
            gap = (card_start_time - session.end_time).total_seconds() / 60
            interruption_duration = (card_end_time - card_start_time).total_seconds() / 60
            
            # 扩大容错范围
            return (gap <= self.gap_threshold_minutes * 2 and 
                    interruption_duration <= self.ignore_short_interruption_minutes * 2)
        
        return False
    
    def _get_current_session(self, sessions: List[ActivitySession], now: datetime) -> Optional[ActivitySession]:
        """获取当前进行中的会话（改进版）"""
        if not sessions:
            return None
        
        # 获取最近的会话
        last_session = sessions[-1]
        
        # 如果会话还没有结束时间，说明是进行中的会话
        if not last_session.end_time:
            return last_session
        
        # 检查时间间隔
        gap = (now - last_session.end_time).total_seconds() / 60
        
        # 如果间隔很小，认为会话仍在进行中
        if gap <= self.session_gap_threshold_minutes:
            return last_session
        
        # 如果是工作会话，允许更大的时间间隔（比如短暂离开）
        if last_session.is_work_activity() and gap <= self.session_gap_threshold_minutes * 3:
            return last_session
        
        # 如果是娱乐会话，允许适度的间隔
        if last_session.is_entertainment_activity() and gap <= self.session_gap_threshold_minutes * 2:
            return last_session
        
        return None
    
    def _calculate_cumulative_session(self, sessions: List[ActivitySession], now: datetime) -> Optional[ActivitySession]:
        """计算累计会话时间"""
        if not sessions:
            return None
        
        # 获取最近的会话
        last_session = sessions[-1]
        
        # 如果是最近的活动，计算累计时间
        if (now - last_session.end_time).total_seconds() / 60 <= self.session_gap_threshold_minutes * 2:
            # 创建累计会话
            cumulative_session = ActivitySession(
                category=last_session.category,
                start_time=last_session.start_time,
                end_time=now,  # 使用当前时间作为结束时间
                productivity_score=last_session.productivity_score
            )
            return cumulative_session
        
        return None
    
    def _check_threshold(self, session: ActivitySession) -> Optional[ReminderResult]:
        """检查是否超过阈值"""
        duration = session.duration_minutes
        
        work_threshold, entertainment_threshold = self._get_effective_thresholds()
        
        if session.is_work_activity() and duration >= work_threshold:
            return ReminderResult(
                type=ReminderType.WORK_TOO_LONG,
                total_minutes=duration,
                message=self._generate_work_message(duration),
                category=session.category
            )
        
        if session.is_entertainment_activity() and duration >= entertainment_threshold:
            return ReminderResult(
                type=ReminderType.ENTERTAINMENT_TOO_LONG,
                total_minutes=duration,
                message=self._generate_entertainment_message(duration),
                category=session.category
            )
        
        return None
    
    def _get_effective_thresholds(self) -> tuple[int, int]:
        """根据强度获取有效的阈值"""
        if self.strength == "mild":
            return int(self.work_threshold_minutes * 1.5), int(self.entertainment_threshold_minutes * 1.5)
        elif self.strength == "strict":
            return int(self.work_threshold_minutes * 0.7), int(self.entertainment_threshold_minutes * 0.7)
        else:
            return self.work_threshold_minutes, self.entertainment_threshold_minutes
    
    def _get_effective_cooldown(self) -> int:
        """根据强度获取有效的冷却时间"""
        if self.strength == "mild":
            return int(self.cooldown_minutes * 1.5)
        elif self.strength == "strict":
            return int(self.cooldown_minutes * 0.7)
        else:
            return self.cooldown_minutes
    
    def _generate_work_message(self, minutes: float) -> str:
        """生成工作提醒消息"""
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        
        if hours > 0:
            time_str = f"{hours}小时{mins}分钟" if mins > 0 else f"{hours}小时"
        else:
            time_str = f"{mins}分钟"
        
        messages = [
            f"你已经连续工作了 {time_str}，该休息一下了！站起来活动活动，喝杯水吧。",
            f"专注工作 {time_str} 了，眼睛需要休息。看看远处，放松一下。",
            f"连续工作 {time_str}，建议起身走动几分钟，保持精力充沛。"
        ]
        
        import random
        return random.choice(messages)
    
    def _generate_entertainment_message(self, minutes: float) -> str:
        """生成娱乐提醒消息"""
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        
        if hours > 0:
            time_str = f"{hours}小时{mins}分钟" if mins > 0 else f"{hours}小时"
        else:
            time_str = f"{mins}分钟"
        
        messages = [
            f"你已经娱乐了 {time_str}，是不是该关注一下你的灵感了？",
            f"放松了 {time_str}，该回到工作状态了！",
            f"休息了 {time_str}，重新投入工作吧。"
        ]
        
        import random
        return random.choice(messages)
    
    def _get_title(self, reminder_type: ReminderType) -> str:
        """获取提醒标题"""
        if reminder_type == ReminderType.WORK_TOO_LONG:
            return "工作提醒"
        elif reminder_type == ReminderType.ENTERTAINMENT_TOO_LONG:
            return "娱乐提醒"
        else:
            return "健康提醒"