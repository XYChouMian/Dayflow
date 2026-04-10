"""
Dayflow Windows - 数据库管理
"""
import sqlite3
import json
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager

import config
from core.types import (
    VideoChunk, ChunkStatus,
    AnalysisBatch, BatchStatus,
    ActivityCard, AppSite, Distraction,
    InspirationCard
)
from database.connection_pool import ConnectionPool, PoolExhaustedError

logger = logging.getLogger(__name__)


class StorageManager:
    """SQLite 数据库管理器 - 使用连接池"""
    
    def __init__(self, db_path: Optional[Path] = None, use_pool: bool = True):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
            use_pool: 是否使用连接池（默认 True）
        """
        self.db_path = db_path or config.DATABASE_PATH
        self._use_pool = use_pool
        self._pool: Optional[ConnectionPool] = None
        self._local = threading.local()  # 线程本地存储（兼容模式）
        
        logger.info(f"数据库路径: {self.db_path}")
        
        if use_pool:
            self._pool = ConnectionPool(
                db_path=str(self.db_path),
                max_size=5,
                timeout=30.0,
                idle_timeout=300.0
            )
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库结构"""
        schema_path = Path(__file__).parent / "schema.sql"
        with self._get_connection() as conn:
            with open(schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            
            # 数据库迁移：为旧数据库添加新字段
            self._migrate_database(conn)
    
    def _migrate_database(self, conn):
        """数据库迁移 - 添加新字段"""
        try:
            # 检查 chunks 表是否有 window_records_path 字段
            cursor = conn.execute("PRAGMA table_info(chunks)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if "window_records_path" not in columns:
                conn.execute("ALTER TABLE chunks ADD COLUMN window_records_path TEXT")
                logger.info("数据库迁移: 添加 chunks.window_records_path 字段")
            
            # 检查 inspirations 表是否需要迁移（从 tags_json 到 category + notes_json）
            cursor = conn.execute("PRAGMA table_info(inspirations)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if "category" not in columns:
                # 添加 category 字段
                conn.execute("ALTER TABLE inspirations ADD COLUMN category TEXT DEFAULT '灵感'")
                logger.info("数据库迁移: 添加 inspirations.category 字段")
            
            if "notes_json" not in columns:
                # 添加 notes_json 字段
                conn.execute("ALTER TABLE inspirations ADD COLUMN notes_json TEXT DEFAULT '[]'")
                logger.info("数据库迁移: 添加 inspirations.notes_json 字段")
                
                # 如果旧数据有 tags_json 字段，将其数据迁移到 notes_json
                if "tags_json" in columns:
                    # 将 tags_json 的数据迁移到 notes_json
                    conn.execute("UPDATE inspirations SET notes_json = tags_json WHERE tags_json IS NOT NULL AND notes_json = '[]'")
                    logger.info("数据库迁移: 将 tags_json 数据迁移到 notes_json")
            
            # 检查 daily_summaries 表是否需要迁移（从 content 到 event_summary + inspiration_summary）
            cursor = conn.execute("PRAGMA table_info(daily_summaries)")
            columns_info = cursor.fetchall()
            columns = [row[1] for row in columns_info]
            columns_dict = {row[1]: row for row in columns_info}
            
            has_event_summary = "event_summary" in columns
            has_inspiration_summary = "inspiration_summary" in columns
            has_content = "content" in columns
            
            if not has_event_summary:
                # 添加 event_summary 字段
                conn.execute("ALTER TABLE daily_summaries ADD COLUMN event_summary TEXT")
                logger.info("数据库迁移: 添加 daily_summaries.event_summary 字段")
            
            if not has_inspiration_summary:
                # 添加 inspiration_summary 字段
                conn.execute("ALTER TABLE daily_summaries ADD COLUMN inspiration_summary TEXT")
                logger.info("数据库迁移: 添加 daily_summaries.inspiration_summary 字段")
            
            # 如果旧数据有 content 字段，将其数据迁移到 event_summary，然后删除 content 字段
            if has_content:
                # 检查 content 字段是否为 NOT NULL
                content_notnull = columns_dict.get("content", {}).get("notnull", 0) == 1
                
                # 将 content 的数据迁移到 event_summary
                conn.execute("UPDATE daily_summaries SET event_summary = content WHERE content IS NOT NULL")
                logger.info("数据库迁移: 将 content 数据迁移到 event_summary")
                
                # 重建表以删除 content 字段（SQLite 不支持直接删除列）
                conn.execute("""
                    CREATE TABLE daily_summaries_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL UNIQUE,
                        event_summary TEXT,
                        inspiration_summary TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 复制数据
                conn.execute("""
                    INSERT INTO daily_summaries_new (id, date, event_summary, inspiration_summary, created_at, updated_at)
                    SELECT id, date, event_summary, inspiration_summary, created_at, updated_at FROM daily_summaries
                """)
                
                # 删除旧表
                conn.execute("DROP TABLE daily_summaries")
                
                # 重命名新表
                conn.execute("ALTER TABLE daily_summaries_new RENAME TO daily_summaries")
                
                logger.info("数据库迁移: 已删除 daily_summaries.content 字段")
        except Exception as e:
            logger.debug(f"数据库迁移检查: {e}")
    
    def _get_cached_connection(self):
        """获取线程本地的缓存连接（兼容模式）"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
            # 使用 WAL 模式，但确保数据立即写入
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=FULL")  # 改为 FULL 确保数据写入
        return self._local.conn
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接上下文"""
        if self._use_pool and self._pool:
            # 使用连接池
            with self._pool.get_connection() as conn:
                yield conn
        else:
            # 兼容模式：使用缓存连接
            conn = self._get_cached_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def close(self):
        """关闭数据库连接"""
        if self._use_pool and self._pool:
            # 关闭连接池
            self._pool.close_all()
            self._pool = None
            logger.info("数据库连接池已关闭")
        else:
            # 兼容模式
            if hasattr(self._local, 'conn') and self._local.conn is not None:
                try:
                    # 最终 checkpoint 确保所有数据写入主数据库文件
                    self._local.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    self._local.conn.close()
                    logger.info("数据库连接已关闭")
                except Exception as e:
                    logger.error(f"关闭数据库连接失败: {e}")
                finally:
                    self._local.conn = None
    
    # ==================== Chunks ====================
    
    def save_chunk(self, chunk: VideoChunk) -> int:
        """保存视频切片"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chunks (file_path, start_time, end_time, duration_seconds, status, batch_id, window_records_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.file_path,
                    chunk.start_time.isoformat() if chunk.start_time else None,
                    chunk.end_time.isoformat() if chunk.end_time else None,
                    chunk.duration_seconds,
                    chunk.status.value,
                    chunk.batch_id,
                    chunk.window_records_path
                )
            )
            return cursor.lastrowid
    
    def get_pending_chunks(self, limit: int = 100) -> List[VideoChunk]:
        """获取待分析的切片"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM chunks 
                WHERE status = ? 
                ORDER BY start_time ASC 
                LIMIT ?
                """,
                (ChunkStatus.PENDING.value, limit)
            )
            return [self._row_to_chunk(row) for row in cursor.fetchall()]
    
    def get_chunk_by_id(self, chunk_id: int) -> Optional[VideoChunk]:
        """根据ID获取切片"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM chunks 
                WHERE id = ?
                """,
                (chunk_id,)
            )
            row = cursor.fetchone()
            return self._row_to_chunk(row) if row else None
    
    def update_chunk_status(self, chunk_id: int, status: ChunkStatus, batch_id: Optional[int] = None):
        """更新切片状态"""
        with self._get_connection() as conn:
            if batch_id is not None:
                conn.execute(
                    "UPDATE chunks SET status = ?, batch_id = ? WHERE id = ?",
                    (status.value, batch_id, chunk_id)
                )
            else:
                conn.execute(
                    "UPDATE chunks SET status = ? WHERE id = ?",
                    (status.value, chunk_id)
                )
    
    def _row_to_chunk(self, row: sqlite3.Row) -> VideoChunk:
        """将数据库行转换为 VideoChunk 对象"""
        # 安全获取 window_records_path（兼容旧数据库）
        window_records_path = None
        try:
            window_records_path = row["window_records_path"]
        except (IndexError, KeyError):
            pass
        
        return VideoChunk(
            id=row["id"],
            file_path=row["file_path"],
            start_time=datetime.fromisoformat(row["start_time"]) if row["start_time"] else None,
            end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
            duration_seconds=row["duration_seconds"],
            status=ChunkStatus(row["status"]),
            batch_id=row["batch_id"],
            window_records_path=window_records_path
        )
    
    # ==================== Batches ====================
    
    def create_batch(self, batch: AnalysisBatch) -> int:
        """创建分析批次"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_batches (chunk_ids, start_time, end_time, status, observations_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    json.dumps(batch.chunk_ids),
                    batch.start_time.isoformat() if batch.start_time else None,
                    batch.end_time.isoformat() if batch.end_time else None,
                    batch.status.value,
                    batch.observations_json
                )
            )
            return cursor.lastrowid
    
    def update_batch(self, batch_id: int, status: BatchStatus, 
                     observations_json: Optional[str] = None,
                     error_message: Optional[str] = None):
        """更新批次状态"""
        with self._get_connection() as conn:
            if status == BatchStatus.COMPLETED:
                conn.execute(
                    """
                    UPDATE analysis_batches 
                    SET status = ?, observations_json = ?, completed_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                    """,
                    (status.value, observations_json or "[]", batch_id)
                )
            elif status == BatchStatus.FAILED:
                conn.execute(
                    """
                    UPDATE analysis_batches 
                    SET status = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                    """,
                    (status.value, error_message, batch_id)
                )
            else:
                conn.execute(
                    "UPDATE analysis_batches SET status = ? WHERE id = ?",
                    (status.value, batch_id)
                )
    
    def get_pending_batches(self) -> List[AnalysisBatch]:
        """获取待处理的批次"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM analysis_batches WHERE status = ?",
                (BatchStatus.PENDING.value,)
            )
            return [self._row_to_batch(row) for row in cursor.fetchall()]
    
    def _row_to_batch(self, row: sqlite3.Row) -> AnalysisBatch:
        """将数据库行转换为 AnalysisBatch 对象"""
        return AnalysisBatch(
            id=row["id"],
            chunk_ids=json.loads(row["chunk_ids"]),
            start_time=datetime.fromisoformat(row["start_time"]) if row["start_time"] else None,
            end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
            status=BatchStatus(row["status"]),
            observations_json=row["observations_json"],
            error_message=row["error_message"]
        )
    
    # ==================== Timeline Cards ====================
    
    def save_card(self, card: ActivityCard, batch_id: Optional[int] = None) -> int:
        """保存时间轴卡片"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO timeline_cards 
                (batch_id, category, title, summary, start_time, end_time, 
                 app_sites_json, distractions_json, productivity_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch_id,
                    card.category,
                    card.title,
                    card.summary,
                    card.start_time.isoformat() if card.start_time else None,
                    card.end_time.isoformat() if card.end_time else None,  # 从属性获取
                    json.dumps([a.to_dict() for a in card.app_sites]),
                    json.dumps([d.to_dict() for d in card.distractions]),
                    card.productivity_score
                )
            )
            return cursor.lastrowid
    
    def get_cards_for_date(self, date: datetime) -> List[ActivityCard]:
        """获取指定日期的时间轴卡片"""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM timeline_cards 
                WHERE start_time >= ? AND start_time <= ?
                ORDER BY start_time ASC
                """,
                (start.isoformat(), end.isoformat())
            )
            return [self._row_to_card(row) for row in cursor.fetchall()]
    
    def get_cards_before_time(self, time: datetime, limit: int = 10) -> List[ActivityCard]:
        """获取指定时间之前的卡片（用作合并上下文）"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM timeline_cards 
                WHERE start_time < ?
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (time.isoformat(), limit)
            )
            cards = [self._row_to_card(row) for row in cursor.fetchall()]
            # 按开始时间升序排列，这样 context_cards[-1] 就是最近的一张卡片
            cards.reverse()
            return cards
    
    def get_recent_cards(self, limit: int = 10) -> List[ActivityCard]:
        """获取最近的卡片（用作上下文）"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM timeline_cards 
                ORDER BY end_time DESC 
                LIMIT ?
                """,
                (limit,)
            )
            return [self._row_to_card(row) for row in cursor.fetchall()]
    
    def _row_to_card(self, row: sqlite3.Row) -> ActivityCard:
        """将数据库行转换为 ActivityCard 对象"""
        card = ActivityCard(
            id=row["id"],
            category=row["category"],
            title=row["title"],
            summary=row["summary"],
            start_time=datetime.fromisoformat(row["start_time"]) if row["start_time"] else None,
            app_sites=[AppSite.from_dict(a) for a in json.loads(row["app_sites_json"] or "[]")],
            distractions=[Distraction.from_dict(d) for d in json.loads(row["distractions_json"] or "[]")],
            productivity_score=row["productivity_score"]
        )
        
        # 将数据库中的end_time设置到_next_card_start_time字段
        if row["end_time"]:
            card._next_card_start_time = datetime.fromisoformat(row["end_time"])
        
        return card
    
    def update_card(self, card_id: int, category: str = None, title: str = None, 
                    summary: str = None, productivity_score: float = None, 
                    end_time: datetime = None) -> bool:
        """更新时间轴卡片"""
        try:
            with self._get_connection() as conn:
                # 构建动态更新语句
                updates = []
                params = []
                
                if category is not None:
                    updates.append("category = ?")
                    params.append(category)
                if title is not None:
                    updates.append("title = ?")
                    params.append(title)
                if summary is not None:
                    updates.append("summary = ?")
                    params.append(summary)
                if productivity_score is not None:
                    updates.append("productivity_score = ?")
                    params.append(productivity_score)
                if end_time is not None:
                    updates.append("end_time = ?")
                    params.append(end_time.isoformat())
                
                if not updates:
                    return False
                
                params.append(card_id)
                sql = f"UPDATE timeline_cards SET {', '.join(updates)} WHERE id = ?"
                conn.execute(sql, params)
                logger.info(f"已更新卡片 {card_id}")
                return True
        except Exception as e:
            logger.error(f"更新卡片失败 {card_id}: {e}")
            return False
    
    def delete_card(self, card_id: int) -> bool:
        """删除时间轴卡片"""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM timeline_cards WHERE id = ?", (card_id,))
                logger.info(f"已删除卡片 {card_id}")
                return True
        except Exception as e:
            logger.error(f"删除卡片失败 {card_id}: {e}")
            return False
    
    # ==================== Daily Summaries ====================
    
    def save_daily_summary(self, date: datetime, event_summary: Optional[str] = None, inspiration_summary: Optional[str] = None) -> int:
        """
        保存每日总结
        
        Args:
            date: 日期
            event_summary: 事件总结内容（可选）
            inspiration_summary: 灵感总结内容（可选）
            
        Returns:
            总结记录的 ID
        """
        date_str = date.strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO daily_summaries (date, event_summary, inspiration_summary)
                VALUES (?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    event_summary = COALESCE(?, event_summary),
                    inspiration_summary = COALESCE(?, inspiration_summary),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (date_str, event_summary, inspiration_summary, event_summary, inspiration_summary)
            )
            
            row_id = cursor.lastrowid
            
            if row_id == 0:
                cursor = conn.execute("SELECT id FROM daily_summaries WHERE date = ?", (date_str,))
                row = cursor.fetchone()
                if row:
                    row_id = row["id"]
            
            logger.info(f"已保存每日总结 {date_str}, ID: {row_id}")
            return row_id
    
    def get_daily_summary(self, date: datetime) -> tuple[Optional[str], Optional[str]]:
        """
        获取指定日期的每日总结
        
        Args:
            date: 日期
            
        Returns:
            (event_summary, inspiration_summary) 元组，如果不存在则返回 (None, None)
        """
        date_str = date.strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT event_summary, inspiration_summary FROM daily_summaries WHERE date = ?",
                (date_str,)
            )
            row = cursor.fetchone()
            if row:
                return row["event_summary"], row["inspiration_summary"]
            return None, None
    
    def daily_summary_exists(self, date: datetime) -> bool:
        """
        检查指定日期是否已有每日总结
        
        Args:
            date: 日期
            
        Returns:
            如果存在返回 True，否则返回 False
        """
        date_str = date.strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM daily_summaries WHERE date = ?",
                (date_str,)
            )
            return cursor.fetchone() is not None
    
    # ==================== Weekly Summaries ====================
    
    def save_weekly_summary(self, week_start: datetime, week_end: datetime, event_summary: Optional[str] = None, inspiration_summary: Optional[str] = None) -> int:
        """
        保存周总结
        
        Args:
            week_start: 周开始日期
            week_end: 周结束日期
            event_summary: 周事件总结内容（可选）
            inspiration_summary: 周灵感总结内容（可选）
            
        Returns:
            总结记录的 ID
        """
        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end_str = week_end.strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO weekly_summaries (week_start, week_end, event_summary, inspiration_summary)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(week_start, week_end) DO UPDATE SET
                    event_summary = COALESCE(?, event_summary),
                    inspiration_summary = COALESCE(?, inspiration_summary),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (week_start_str, week_end_str, event_summary, inspiration_summary, event_summary, inspiration_summary)
            )
            
            row_id = cursor.lastrowid
            
            if row_id == 0:
                cursor = conn.execute(
                    "SELECT id FROM weekly_summaries WHERE week_start = ? AND week_end = ?",
                    (week_start_str, week_end_str)
                )
                row = cursor.fetchone()
                if row:
                    row_id = row["id"]
            
            logger.info(f"已保存周总结 {week_start_str} 至 {week_end_str}, ID: {row_id}")
            return row_id
    
    def get_weekly_summary(self, week_start: datetime, week_end: datetime) -> tuple[Optional[str], Optional[str]]:
        """
        获取指定周的周总结
        
        Args:
            week_start: 周开始日期
            week_end: 周结束日期
            
        Returns:
            (event_summary, inspiration_summary) 元组，如果不存在则返回 (None, None)
        """
        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end_str = week_end.strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT event_summary, inspiration_summary FROM weekly_summaries WHERE week_start = ? AND week_end = ?",
                (week_start_str, week_end_str)
            )
            row = cursor.fetchone()
            if row:
                return row["event_summary"], row["inspiration_summary"]
            return None, None
    
    def weekly_summary_exists(self, week_start: datetime, week_end: datetime) -> bool:
        """
        检查指定周是否已有周总结
        
        Args:
            week_start: 周开始日期
            week_end: 周结束日期
            
        Returns:
            如果存在返回 True，否则返回 False
        """
        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end_str = week_end.strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM weekly_summaries WHERE week_start = ? AND week_end = ?",
                (week_start_str, week_end_str)
            )
            return cursor.fetchone() is not None
    
    # ==================== Inspirations ====================
    
    def save_inspiration(self, card: InspirationCard) -> int:
        """
        保存灵感卡片
        
        Args:
            card: 灵感卡片对象
            
        Returns:
            插入的记录ID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO inspirations (content, timestamp, category, notes_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    card.content,
                    card.timestamp.isoformat() if card.timestamp else datetime.now().isoformat(),
                    card.category,
                    json.dumps(card.notes)
                )
            )
            return cursor.lastrowid
    
    def update_inspiration(self, card: InspirationCard):
        """
        更新灵感卡片
        
        Args:
            card: 灵感卡片对象
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE inspirations
                SET content = ?, timestamp = ?, category = ?, notes_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    card.content,
                    card.timestamp.isoformat() if card.timestamp else datetime.now().isoformat(),
                    card.category,
                    json.dumps(card.notes),
                    card.id
                )
            )
    
    def delete_inspiration(self, inspiration_id: int):
        """
        删除灵感卡片
        
        Args:
            inspiration_id: 灵感卡片ID
        """
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM inspirations WHERE id = ?",
                (inspiration_id,)
            )
    
    def get_inspirations_by_date(self, date: datetime) -> List[InspirationCard]:
        """
        获取指定日期的灵感卡片列表
        
        Args:
            date: 日期
            
        Returns:
            灵感卡片列表
        """
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_of_day = datetime(date.year, date.month, date.day, 23, 59, 59)
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, content, timestamp, category, notes_json
                FROM inspirations
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp DESC
                """,
                (start_of_day.isoformat(), end_of_day.isoformat())
            )
            
            cards = []
            for row in cursor.fetchall():
                card = InspirationCard(
                    id=row["id"],
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    category=row["category"],
                    notes=json.loads(row["notes_json"])
                )
                cards.append(card)
            
            return cards
    
    def get_all_inspirations(self) -> List[InspirationCard]:
        """
        获取所有灵感卡片
        
        Returns:
            所有灵感卡片列表（按时间倒序）
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, content, timestamp, category, notes_json
                FROM inspirations
                ORDER BY timestamp DESC
                """
            )
            
            cards = []
            for row in cursor.fetchall():
                card = InspirationCard(
                    id=row["id"],
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    category=row["category"],
                    notes=json.loads(row["notes_json"])
                )
                cards.append(card)
            
            return cards
    
    # ==================== Settings ====================
    
    def get_setting(self, key: str, default: str = "") -> str:
        """获取设置值 - 使用独立连接确保读取最新数据"""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            conn.close()
            value = row["value"] if row else default
            logger.debug(f"读取设置 {key}: {'已找到' if row else '使用默认值'}")
            return value
        except Exception as e:
            logger.error(f"读取设置失败 {key}: {e}")
            return default
    
    def set_setting(self, key: str, value: str):
        """设置值 - 使用独立连接确保立即写入"""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
                """,
                (key, value, value)
            )
            conn.commit()
            # 强制 checkpoint 确保 WAL 数据写入主文件
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
            logger.info(f"已保存设置 {key}")
        except Exception as e:
            logger.error(f"保存设置失败 {key}: {e}")
