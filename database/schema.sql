-- Dayflow Windows - 数据库结构
-- SQLite 3

-- 视频切片表
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    duration_seconds REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    batch_id INTEGER,
    window_records_path TEXT,  -- 窗口记录 JSON 文件路径
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES analysis_batches(id)
);

-- 为已存在的数据库添加新字段（如果不存在）
-- SQLite 不支持 IF NOT EXISTS 语法，所以用 ALTER TABLE 会在字段已存在时报错，但不影响使用

-- 分析批次表
CREATE TABLE IF NOT EXISTS analysis_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_ids TEXT NOT NULL,  -- JSON array of chunk IDs
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    observations_json TEXT DEFAULT '[]',  -- 原始观察记录 JSON
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 时间轴卡片表
CREATE TABLE IF NOT EXISTS timeline_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    app_sites_json TEXT DEFAULT '[]',  -- JSON array of AppSite objects
    distractions_json TEXT DEFAULT '[]',  -- JSON array of Distraction objects
    productivity_score REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES analysis_batches(id)
);

-- 用户设置表
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 每日总结表
CREATE TABLE IF NOT EXISTS daily_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,  -- 日期字符串 (YYYY-MM-DD)
    event_summary TEXT,  -- 事件总结内容
    inspiration_summary TEXT,  -- 灵感总结内容
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_chunks_status ON chunks(status);
CREATE INDEX IF NOT EXISTS idx_chunks_start_time ON chunks(start_time);
CREATE INDEX IF NOT EXISTS idx_batches_status ON analysis_batches(status);
CREATE INDEX IF NOT EXISTS idx_cards_start_time ON timeline_cards(start_time);
CREATE INDEX IF NOT EXISTS idx_cards_category ON timeline_cards(category);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON daily_summaries(date);

-- 周总结表
CREATE TABLE IF NOT EXISTS weekly_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT NOT NULL,  -- 周开始日期 (YYYY-MM-DD)
    week_end TEXT NOT NULL,  -- 周结束日期 (YYYY-MM-DD)
    event_summary TEXT,  -- 周事件总结内容
    inspiration_summary TEXT,  -- 周灵感总结内容
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(week_start, week_end)
);

CREATE INDEX IF NOT EXISTS idx_weekly_summaries_week ON weekly_summaries(week_start, week_end);

-- 灵感卡片表
CREATE TABLE IF NOT EXISTS inspirations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    category TEXT DEFAULT '灵感',
    notes_json TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inspirations_timestamp ON inspirations(timestamp);
