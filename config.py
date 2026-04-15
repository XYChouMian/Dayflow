"""
Dayflow Windows - 配置文件
"""
import os
import sys
from pathlib import Path

# 版本信息
VERSION = "1.5.2"
GITHUB_REPO = "SeiShonagon520/Dayflow"

# API 配置 (OpenAI 兼容格式)
API_BASE_URL = os.getenv("DAYFLOW_API_URL", "https://open.bigmodel.cn/api/paas/v4")
API_KEY = os.getenv("DAYFLOW_API_KEY", "")
API_MODEL = os.getenv("DAYFLOW_API_MODEL", "glm-4-flash-250414")  # 支持视觉输入的模型（默认免费）
VISUAL_THINKING_MODE = os.getenv("DAYFLOW_VISUAL_THINKING_MODE", "disabled")  # 视觉模型思考模式
API_TIMEOUT = 300.0  # API 请求超时时间（秒），视觉模型处理图片需要较长时间

# 每日总结 API 配置
DAILY_SUMMARY_MODEL = os.getenv("DAYFLOW_DAILY_SUMMARY_MODEL", "glm-4-flash-250414")  # 每日总结模型（默认免费）
SUMMARY_THINKING_MODE = os.getenv("DAYFLOW_SUMMARY_THINKING_MODE", "enabled")  # 每日总结模型思考模式
DAILY_SUMMARY_TIMEOUT = 120.0  # 每日总结 API 请求超时时间（秒）

# 录屏配置
RECORD_FRAME_INTERVAL = 3.0  # 每帧间隔秒数（1秒1帧）
CHUNK_DURATION_SECONDS = 60  # 每60秒一个切片
VIDEO_BITRATE = "500k"  # 低码率
VIDEO_CODEC = "libx264"

# 分析配置
BATCH_CHUNK_COUNT = 10  # 每个批次的切片数量
ANALYSIS_INTERVAL_SECONDS = 60  # 扫描一次的间隔（秒）
# ANALYSIS_MAX_IDLE_INTERVAL = 300  # 无任务时最大扫描间隔（秒）

# 录制优化配置
WINDOW_TRACKING_ON_CHANGE_ONLY = True  # 仅在窗口变化时记录（减少数据量）
FRAME_CAPTURE_TIMEOUT = 2.0  # 帧捕获超时（秒）

# 存储清理配置
AUTO_DELETE_ANALYZED_CHUNKS = True  # 分析完成后自动删除视频切片（节省磁盘空间）

# 性能监控配置（开发/调试用）
ENABLE_PERFORMANCE_MONITOR = False  # 是否启用性能监控
PERFORMANCE_MONITOR_INTERVAL = 5.0  # 监控间隔（秒）

# 数据目录 - 使用更可靠的方式获取 AppData 路径
def _get_app_data_dir() -> Path:
    """获取应用数据目录"""
    # 优先使用 LOCALAPPDATA
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Dayflow"
    
    # 备选：使用 USERPROFILE
    user_profile = os.getenv("USERPROFILE")
    if user_profile:
        return Path(user_profile) / "AppData" / "Local" / "Dayflow"
    
    # 最后备选：使用 Path.home()
    return Path.home() / "AppData" / "Local" / "Dayflow"

APP_DATA_DIR = _get_app_data_dir()
CHUNKS_DIR = APP_DATA_DIR / "chunks"
DATABASE_PATH = APP_DATA_DIR / "dayflow.db"

# 打包时的应用目录
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

# 确保目录存在
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

# 打印数据目录路径（用于调试）
print(f"[Dayflow] 数据目录: {APP_DATA_DIR}")

# UI 配置
WINDOW_TITLE = "Dayflow"
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 600

# 健康提醒配置
HEALTH_REMINDER_WORK_THRESHOLD = 90  # 连续工作多少分钟后提醒休息
HEALTH_REMINDER_ENTERTAINMENT_THRESHOLD = 60  # 连续娱乐多少分钟后提醒
HEALTH_REMINDER_COOLDOWN = 15  # 提醒冷却时间（分钟）
HEALTH_REMINDER_CHECK_INTERVAL = 300000  # 检查间隔（毫秒，5分钟）

# 活跃度感知配置
ENABLE_AUTO_PAUSE = True  # 是否启用自动暂停功能
STOP_CHECK_INTERVAL = 60  # 停止检测间隔（秒），默认60秒
STOP_DETECTION_DURATION = 30  # 停止检测持续时间（秒），默认30秒
RESUME_WAIT_DURATION = 30  # 恢复等待持续时间（秒），默认30秒
RESUME_DETECTION_DURATION = 90  # 恢复检测持续时间（秒），默认90秒
