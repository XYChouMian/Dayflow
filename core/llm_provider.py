"""
Dayflow Windows - API 交互层
使用 OpenAI 兼容格式调用心流 API
"""
import asyncio
import base64
import json
import logging
import re
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from urllib.parse import unquote

import httpx
import cv2

import config
from core.types import Observation, ActivityCard, AppSite

logger = logging.getLogger(__name__)

# 系统提示词
TRANSCRIBE_SYSTEM_PROMPT = """你是屏幕活动分析助手。根据截图和窗口信息，描述用户的具体行为。

返回 JSON 格式：
{
  "observations": [
    {"start_ts": 0, "end_ts": 10, "text": "编写 Python 代码，实现用户登录功能"}
  ]
}

规则：
- start_ts/end_ts 是相对秒数
- text 只描述行为（写什么代码、看什么内容、做什么操作），不要写应用名称
- 优先参考窗口标题里的文件名、网页标题、文档名、聊天对象来提高描述精度
- 如果能判断具体正在编辑/查看的文件或页面，请在 text 中自然体现
- 只返回 JSON"""

GENERATE_CARDS_SYSTEM_PROMPT = """你是时间管理助手。根据观察记录生成活动卡片。

【关键规则 - 必须严格遵守】

1. 时间范围限制：
   - end_ts 必须是正数，且必须 ≤ 总观察时长（观察记录中最晚的结束时间）
   - 不要随意扩展或缩短时间范围，严格根据观察记录的时间范围
   - 如果没有明显的时间间隔，合理分配时间给每张卡片

2. 时间连续性要求：
   - 多张卡片的 end_ts 必须**严格递增**
   - 卡片1的结束时间 < 卡片2的结束时间 < 卡片3的结束时间 < ...
   - 严禁出现时间重叠或倒序！
   - 每张卡片的持续时间至少 6 秒

3. 卡片数量建议：
   - 根据观察记录中活动的变化程度决定卡片数量
   - 如果是连续的相同活动，合并为1-2张卡片
   - 如果有多种活动类型，合理拆分（通常3-6张卡片）
   - 避免生成过多碎片化卡片（超过10张通常不合理）

4. 返回格式要求：
   - **只返回JSON，不要包含任何其他文字说明**
   - 不要使用 markdown 代码块（不要 ```json ... ```）
   - 直接返回纯JSON格式的文本

5. 只返回结束时间：
   - 只需要提供 end_ts（活动结束时间）
   - 活动的开始时间由系统根据视频录制时间点自动设置
   - 不要推断或设置 start_ts

【JSON 格式】
{
  "cards": [
    {
      "category": "编程",
      "title": "Dayflow 项目开发",
      "summary": "实现用户登录功能，编写单元测试",
      "end_ts": 5400,
      "app_sites": [{"name": "VS Code"}],
      "productivity_score": 85,
      "merge_with_previous": false,
      "updated_summary": null
    }
  ]
}

【示例说明】

示例1：单个活动
观察记录总时长：600秒
活动：整个时段都在写代码
应生成：1张卡片，end_ts = 600

示例2：两个活动
观察记录总时长：600秒
活动：前300秒写代码，后300秒查文档
应生成：2张卡片
- 卡片1: end_ts = 300
- 卡片2: end_ts = 600

示例3：多个活动
观察记录总时长：600秒
活动：100秒写代码 → 200秒会议 → 300秒文档
应生成：3张卡片
- 卡片1: end_ts = 100
- 卡片2: end_ts = 300
- 卡片3: end_ts = 600

【类别定义】
- 编程：写代码、调试、代码审查
- 工作：文档、邮件、项目管理、设计
- 学习：看教程、读文档、做笔记
- 会议：视频会议、语音通话
- 社交：聊天、社交媒体
- 娱乐：视频、游戏、音乐
- 休息：无明显活动
- 其他：无法归类

【productivity_score 评分标准】
- 90-100：高度专注的核心工作（编程、写作、设计）
- 70-89：一般工作（邮件、文档、会议）
- 50-69：低效工作（频繁切换、碎片化任务）
- 30-49：轻度娱乐（浏览、社交）
- 0-29：纯娱乐（游戏、视频）

【合并规则】
- 连续相同应用且相似活动 → 合并为一张卡片
- 同一时段内切换不同类型活动 → 拆分为多张卡片

【重要：合并卡片逻辑】
如果提供了"上一张卡片信息"，你需要判断当前活动是否应该：
1. 创建新卡片（merge_with_previous = false）- 当活动类型、应用或内容发生明显变化时
2. 合并到上一张卡片（merge_with_previous = true）- 当活动与上一张卡片是连续的相同类型活动时

当决定合并时：
- 设置 merge_with_previous = true
- 在 updated_summary 中提供合并后的完整描述，必须涵盖上一张卡片和当前卡片的所有活动内容
- 确保更新后的描述清晰、完整，不遗漏任何重要信息

合并判断标准：
- 相同应用且活动类型相似 → 合并
- 活动是延续性的（继续做同一件事） → 合并
- 活动有明显变化（换应用、换任务、换类型） → 新建卡片
- **时间间隔超过1小时 → 必须新建卡片，禁止合并**（跨天或长时间间隔的休息后应该重新开始）

【跨批次连续性】
- 如果"前序活动卡片"的最后一张与当前观察记录的开头是同类活动，考虑延续而非新建
- 检查前序卡片的 category 和 title，如果当前活动是其延续，title 和 category 应当完全相同

只返回JSON，不要包含任何其他文字！"""

DAILY_SUMMARY_SYSTEM_PROMPT = """你是时间管理助手。根据一天的活动记录生成总结报告。

请按以下结构生成总结：

1. 工作概览
- 简要描述今天的主要工作内容
- 统计工作时长和效率评分

2. 重点成果
- 列出今天完成的重要任务或进展
- 突出有价值的成果

3. 效率分析
- 分析专注时段和低效时段
- 识别影响效率的因素

4. 改进建议
- 针对今天的表现提出具体建议
- 推荐更好的时间管理方法

5. 明日规划
- 基于今天的进度，建议明天的重点工作

总结要求：
- 语言简洁明了，避免冗余
- 突出重点，使用要点形式
- 保持积极鼓励的语气
- 提供可操作的建议"""


INSPIRATION_SUMMARY_SYSTEM_PROMPT = """你是创意思考助手。根据一天记录的灵感卡片生成总结和延伸思考。

请按以下结构生成总结：

1. 灵感总结
- 总结今天记录的所有灵感
- 按类别（灵感、想法、待办等）进行归纳
- 提取核心观点和关键想法

2. 延伸思考
- 分析灵感之间的内在联系
- 探索灵感背后的深层意义
- 从不同角度对灵感进行拓展
- 提出可能的行动方案或实践建议
- 思考如何将灵感转化为实际成果

总结要求：
- 深度思考，挖掘灵感价值
- 创造性拓展，提供新的视角
- 理论联系实际，给出可行建议
- 语言富有启发性，激发更多思考"""


class DayflowBackendProvider:
    """
    心流 API 交互类 (OpenAI 兼容格式)
    使用 Chat Completions 接口进行视频分析
    """

    FILE_HINT_BLACKLIST = {
        "visual studio code", "trae", "cursor", "google chrome", "microsoft edge", "firefox",
        "wechat", "qq", "telegram", "discord", "notion", "obsidian", "typora",
        "microsoft word", "microsoft excel", "powerpoint", "outlook",
        "文件资源管理器", "windows terminal", "powershell", "cmd", "unknown"
    }
    
    def __init__(
        self,
        api_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        thinking_mode: Optional[str] = None,
        text_model: Optional[str] = None,
    ):
        self._api_base_url = api_base_url
        self._api_key = api_key
        self._model = model
        self._text_model = text_model
        self._timeout = timeout
        self._thinking_mode = thinking_mode
        
        self._client: Optional[httpx.AsyncClient] = None
        self._client_loop_id: Optional[int] = None
    
    @property
    def api_base_url(self) -> str:
        return (self._api_base_url or config.API_BASE_URL).rstrip("/")
    
    @property
    def api_key(self) -> str:
        return self._api_key or config.API_KEY
    
    @property
    def model(self) -> str:
        return self._model or config.API_MODEL
    
    @property
    def text_model(self) -> str:
        return self._text_model or config.DAILY_SUMMARY_MODEL
    
    @property
    def timeout(self) -> float:
        return self._timeout if self._timeout is not None else config.API_TIMEOUT
    
    @property
    def thinking_mode(self) -> str:
        return self._thinking_mode or config.VISUAL_THINKING_MODE
    
    @property
    def headers(self) -> dict:
        """请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建异步 HTTP 客户端"""
        try:
            current_loop = asyncio.get_running_loop()
            current_loop_id = id(current_loop)
        except RuntimeError:
            current_loop = None
            current_loop_id = None
        
        need_new_client = (
            self._client is None or 
            self._client.is_closed or
            self._client_loop_id != current_loop_id
        )
        
        if need_new_client:
            if self._client and not self._client.is_closed:
                try:
                    await self._client.aclose()
                except Exception:
                    pass
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self.headers
            )
            self._client_loop_id = current_loop_id
        
        return self._client
    
    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _extract_frames_from_video(self, video_path: str, max_frames: int = 10) -> List[str]:
        """
        从视频中提取关键帧并编码为 base64
        
        Args:
            video_path: 视频文件路径
            max_frames: 最大提取帧数
            
        Returns:
            List[str]: base64 编码的图片列表
        """
        frames_base64 = []
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"无法打开视频文件: {video_path}")
            return frames_base64
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            cap.release()
            return frames_base64
        
        # 均匀采样帧（不重复）
        actual_frames = min(max_frames, total_frames)
        frame_indices = [int(i * total_frames / actual_frames) for i in range(actual_frames)]
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            
            # 压缩图片以减少传输大小
            frame = cv2.resize(frame, (1280, 720))
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            base64_image = base64.b64encode(buffer).decode('utf-8')
            frames_base64.append(base64_image)
        
        cap.release()
        return frames_base64
    
    def _supports_thinking(self, model: str) -> bool:
        """检查模型是否支持 thinking 参数（仅 GLM-4.5 及以上）"""
        thinking_supported_models = [
            "glm-4.5", "glm-4.6", "glm-4.7", "glm-5",
            "glm-4.5v", "glm-4.6v", "glm-4.7v",
        ]
        model_lower = model.lower()
        return any(supported in model_lower for supported in thinking_supported_models)
    
    def _extract_message_content(self, message_content) -> str:
        """兼容不同 OpenAI/Gemini 兼容服务的 message.content 返回格式。"""
        if isinstance(message_content, str):
            return message_content

        if isinstance(message_content, list):
            parts = []
            for item in message_content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    # 常见兼容格式：{"type":"text","text":"..."}
                    text = item.get("text")
                    if text:
                        parts.append(text)
            return "\n".join(parts).strip()

        if message_content is None:
            return ""

        return str(message_content)

    def _extract_file_hint(self, window_title: Optional[str], app_name: Optional[str] = None) -> Optional[str]:
        """从窗口标题中提取较像“文件名/页面标题/文档名”的线索。"""
        if not window_title:
            return None

        title = unquote(str(window_title)).strip()
        if not title:
            return None

        # 常见编辑器/浏览器标题分隔符
        candidates = [seg.strip(" -—_|•·[]()") for seg in re.split(r"\s*[\-|—|_|·|•|:：]\s*", title) if seg.strip()]
        if not candidates:
            candidates = [title]

        app_name_norm = (app_name or "").strip().lower()

        scored = []
        for part in candidates:
            part_norm = part.strip().lower()
            if not part_norm:
                continue
            if len(part_norm) <= 1:
                continue
            if part_norm == app_name_norm:
                continue
            if part_norm in self.FILE_HINT_BLACKLIST:
                continue

            score = 0
            if re.search(r"\.[a-z0-9]{1,8}$", part_norm):
                score += 4  # 像文件名
            if any(ch in part for ch in ('/', '\\')):
                score += 3  # 像路径
            if re.search(r"[\u4e00-\u9fffA-Za-z0-9].{2,}", part):
                score += 1
            if len(part) >= 6:
                score += 1
            if 'github' in app_name_norm or 'code' in app_name_norm or 'cursor' in app_name_norm:
                score += 1

            scored.append((score, part.strip()))

        if not scored:
            return None

        best_score, best_part = max(scored, key=lambda x: x[0])
        if best_score < 2:
            return None

        return best_part[:200]

    async def _chat_completion(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        thinking_mode: Optional[str] = None
    ) -> str:
        """
        调用 Chat Completions API
        
        Args:
            messages: 消息列表
            model: 模型名称（可选，不传则使用默认模型）
            thinking_mode: 思考模式（可选，不传则使用默认思考模式）
            
        Returns:
            str: 模型返回的内容
        """
        client = await self._get_client()
        
        actual_model = model or self.model
        actual_thinking_mode = thinking_mode if thinking_mode is not None else self.thinking_mode
        
        request_body = {
            "model": actual_model,
            "messages": messages,
        }
        
        # thinking 参数仅 GLM-4.5 及以上模型支持
        if self._supports_thinking(actual_model):
            if actual_thinking_mode == "enabled":
                request_body["thinking"] = {"type": "enabled"}
            else:
                request_body["thinking"] = {"type": "disabled"}
        
        try:
            response = await client.post(
                f"{self.api_base_url}/chat/completions",
                json=request_body
            )
            response.raise_for_status()
            
            result = response.json()
            choices = result.get("choices") or []
            if not choices:
                raise ValueError(f"响应中缺少 choices: {result}")

            message = choices[0].get("message") or {}
            content = self._extract_message_content(message.get("content"))
            if content:
                return content

            # 兼容部分服务把文本放在顶层 text / output_text
            fallback_text = choices[0].get("text") or result.get("output_text") or ""
            if fallback_text:
                return fallback_text

            raise ValueError(f"无法从响应中提取文本内容: {result}")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"API 请求失败: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            import traceback
            logger.error(f"API 请求异常: {type(e).__name__}: {e}")
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
            raise
    
    async def transcribe_video(
        self,
        video_path: str,
        duration: float,
        prompt: Optional[str] = None,
        window_records: Optional[List[Dict]] = None
    ) -> List[Observation]:
        """
        分析视频切片，获取观察记录
        
        Args:
            video_path: 视频文件路径
            duration: 视频时长（秒）
            prompt: 额外提示词（可选）
            window_records: 窗口记录列表（可选）
            
        Returns:
            List[Observation]: 观察记录列表
        """
        video_file = Path(video_path)
        if not video_file.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 提取视频帧
        frames = self._extract_frames_from_video(video_path, max_frames=8)
        if not frames:
            logger.warning(f"无法从视频提取帧: {video_path}")
            return []
        
        logger.info(f"开始分析视频: {video_file.name} ({duration:.0f}秒, {len(frames)}帧)")
        
        # 构建窗口信息文本（包含窗口标题/文件名/页面标题）
        window_info_text = ""
        if window_records:
            window_info_text = "\n\n窗口信息（窗口标题里可能包含文件名、网页标题、聊天对象、文档名）：\n"
            # 按时间段聚合相同的应用
            current_app = None
            current_title = None
            current_start = 0
            for record in window_records:
                app_name = record.get("app_name", "Unknown")
                window_title = record.get("window_title", "")
                if app_name != current_app or window_title != current_title:
                    if current_app:
                        title_part = f": {current_title}" if current_title else ""
                        window_info_text += f"- [{current_start:.0f}s - {record['timestamp']:.0f}s] {current_app}{title_part}\n"
                    current_app = app_name
                    current_title = window_title
                    current_start = record.get("timestamp", 0)
            # 添加最后一个
            if current_app:
                title_part = f": {current_title}" if current_title else ""
                window_info_text += f"- [{current_start:.0f}s - {duration:.0f}s] {current_app}{title_part}\n"
        
        # 构建消息内容（包含多张图片）
        content = []
        content.append({
            "type": "text",
            "text": f"以下是一段 {duration:.0f} 秒屏幕录制的 {len(frames)} 个关键帧，请分析用户的活动。{window_info_text}{prompt or ''}"
        })
        
        for i, frame_base64 in enumerate(frames):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame_base64}",
                    "detail": "low"
                }
            })
        
        messages = [
            {"role": "system", "content": TRANSCRIBE_SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ]
        
        try:
            response_text = await self._chat_completion(messages)
            observations = self._parse_observations_from_text(response_text, duration)
            
            logger.info(f"视频分析完成: {video_file.name} -> {len(observations)} 条观察记录")
            
            # 后处理：用真实窗口信息覆盖 AI 返回的 app_name
            if window_records and observations:
                observations = self._apply_window_records(observations, window_records, duration)
            
            return observations
        except Exception as e:
            logger.error(f"视频分析失败: {e}")
            return []
    
    def _apply_window_records(
        self, 
        observations: List[Observation], 
        window_records: List[Dict],
        duration: float
    ) -> List[Observation]:
        """
        用真实窗口记录覆盖 AI 返回的 app_name
        
        根据时间戳匹配，找到每个 observation 对应时间段内使用最多的应用
        """
        if not window_records:
            return observations
        
        # 预处理：构建时间段到应用的映射
        # 格式: [(start_ts, end_ts, app_name, window_title), ...]
        time_segments = []
        current_app = None
        current_title = None
        current_start = 0
        
        for record in window_records:
            app_name = record.get("app_name", "Unknown")
            window_title = record.get("window_title", "")
            timestamp = record.get("timestamp", 0)
            
            if app_name != current_app:
                if current_app:
                    time_segments.append((current_start, timestamp, current_app, current_title))
                current_app = app_name
                current_title = window_title
                current_start = timestamp
        
        # 添加最后一个时间段
        if current_app:
            time_segments.append((current_start, duration, current_app, current_title))
        
        # 为每个 observation 找到对应的应用
        for obs in observations:
            obs_start = obs.start_ts
            obs_end = obs.end_ts
            
            # 统计这个时间段内各应用的占用时长
            app_durations: Dict[str, float] = {}
            app_titles: Dict[str, str] = {}
            
            for seg_start, seg_end, app_name, window_title in time_segments:
                # 计算重叠时间
                overlap_start = max(obs_start, seg_start)
                overlap_end = min(obs_end, seg_end)
                
                if overlap_end > overlap_start:
                    overlap_duration = overlap_end - overlap_start
                    app_durations[app_name] = app_durations.get(app_name, 0) + overlap_duration
                    if app_name not in app_titles:
                        app_titles[app_name] = window_title
            
            # 找到占用时间最长的应用
            if app_durations:
                main_app = max(app_durations, key=app_durations.get)
                obs.app_name = main_app
                obs.window_title = app_titles.get(main_app, obs.window_title)
                obs.file_hint = self._extract_file_hint(obs.window_title, main_app)
                logger.debug(f"后处理: [{obs_start:.0f}s-{obs_end:.0f}s] app_name -> {main_app}, file_hint -> {obs.file_hint}")
        
        return observations
    
    async def generate_activity_cards(
        self,
        observations: List[Observation],
        context_cards: Optional[List[ActivityCard]] = None,
        start_time: Optional[datetime] = None,
        prompt: Optional[str] = None
    ) -> List[ActivityCard]:
        """
        根据观察记录生成时间轴卡片
        
        Args:
            observations: 观察记录列表
            context_cards: 前序卡片（用于上下文）
            start_time: 开始时间
            prompt: 额外提示词（可选）
            
        Returns:
            List[ActivityCard]: 活动卡片列表
        """
        if not observations:
            return []
        
        # 计算总时长
        total_duration = max((obs.end_ts for obs in observations), default=0)
        
        # 构建观察记录文本
        obs_text = f"【总观察时长】{total_duration:.0f} 秒\n\n"
        obs_text += "观察记录：\n"
        for obs in observations:
            obs_text += f"- [{obs.start_ts:.0f}s - {obs.end_ts:.0f}s] {obs.text}"
            extras = []
            if obs.app_name:
                extras.append(f"应用: {obs.app_name}")
            if obs.file_hint:
                extras.append(f"文件/页面线索: {obs.file_hint}")
            elif obs.window_title:
                extras.append(f"窗口标题: {obs.window_title[:120]}")
            if extras:
                obs_text += f" ({'；'.join(extras)})"
            obs_text += "\n"
        
        # 添加时间上下文
        if start_time:
            obs_text += f"\n录制开始时间: {start_time.isoformat()}"
        
        # 添加前序卡片上下文（重点：上一张卡片的详细信息用于判断是否合并）
        if context_cards:
            obs_text += "\n\n【上一张卡片信息】（用于判断是否合并）：\n"
            prev_card = context_cards[-1]
            obs_text += f"类别: {prev_card.category}\n"
            obs_text += f"标题: {prev_card.title}\n"
            obs_text += f"描述: {prev_card.summary}\n"
            if prev_card.app_sites:
                apps = ", ".join([app.name for app in prev_card.app_sites])
                obs_text += f"应用: {apps}\n"
            # 添加上一张卡片的结束时间，用于判断时间间隔
            if prev_card._next_card_start_time:
                obs_text += f"结束时间: {prev_card._next_card_start_time.isoformat()}\n"
            
            obs_text += "\n【前序活动卡片】（最近3个用于参考上下文）：\n"
            for card in context_cards[-3:]:
                obs_text += f"- {card.category}: {card.title}\n"
            
            # 添加时间间隔提示
            if start_time and prev_card._next_card_start_time:
                time_gap = (start_time - prev_card._next_card_start_time).total_seconds() / 60
                obs_text += f"\n【时间间隔】上一张卡片结束时间 {prev_card._next_card_start_time.strftime('%H:%M:%S')} 与当前批次开始时间 {start_time.strftime('%H:%M:%S')} 之间的间隔: {time_gap:.1f}分钟\n"
                if time_gap > 60:
                    obs_text += "⚠️ 时间间隔超过1小时，必须创建新卡片，禁止合并！\n"
        
        # 重试机制：最多重试2次（总共3次机会）
        max_retries = 2
        for attempt in range(max_retries + 1):
            # 添加额外提示词（如果是重试，强调时间连续性）
            if attempt > 0 and not "【⚠️ 重要提示】" in obs_text:
                obs_text += f"\n\n【⚠️ 重要提示】上次生成的卡片未通过验证！请严格遵守以下规则：\n"
                obs_text += "1. 所有卡片的 end_ts 必须 ≤ 总观察时长（不要超过！）\n"
                obs_text += "2. 多张卡片的 end_ts 必须严格递增（卡片1 < 卡片2 < 卡片3...）\n"
                obs_text += "3. 每张卡片的持续时间至少 6 秒\n"
                obs_text += "4. 严禁出现时间重叠或倒序！\n"
                obs_text += f"5. 总观察时长为 {total_duration:.0f} 秒，合理分配时间范围\n"
                obs_text += "6. 只返回纯JSON，不要包含任何文字说明或markdown代码块！\n"
            
            if prompt:
                obs_text += f"\n{prompt}"
            
            messages = [
                {"role": "system", "content": GENERATE_CARDS_SYSTEM_PROMPT},
                {"role": "user", "content": obs_text}
            ]
            
            try:
                logger.info(f"开始生成活动卡片: {len(observations)} 条观察记录 (尝试 {attempt + 1}/{max_retries + 1})")
                response_text = await self._chat_completion(messages, model=self.text_model)
                
                cards = self._parse_cards_from_text(response_text, start_time, total_duration)
                
                # 如果解析失败（返回空列表），输出AI原始响应
                if not cards:
                    logger.error(f"AI响应解析失败，原始响应内容：\n{response_text}")
                    
                    if attempt < max_retries:
                        logger.info("将重新提交给AI分析，强调规则")
                    else:
                        logger.error(f"已达到最大重试次数 ({max_retries + 1})，仍然无法解析AI响应")
                        return []
                    continue
                
                # 验证卡片时间连续性
                is_valid, error_msg = self._validate_card_continuity(cards)
                
                if is_valid:
                    logger.info(f"活动卡片生成完成并通过验证: {len(cards)} 张卡片")
                    return cards
                else:
                    logger.warning(f"活动卡片时间连续性验证失败 (尝试 {attempt + 1}/{max_retries + 1}): {error_msg}")
                    logger.info(f"AI生成的卡片内容：\n{self._format_cards_for_log(cards)}")
                    
                    if attempt < max_retries:
                        logger.info("将重新提交给AI分析，强调时间连续性")
                        # 移除之前添加的提示词，准备下一次重试
                        obs_text = obs_text.split("【⚠️ 重要提示】")[0] if "【⚠️ 重要提示】" in obs_text else obs_text
                    else:
                        logger.error(f"已达到最大重试次数 ({max_retries + 1})，验证仍然失败: {error_msg}")
                        logger.warning("返回验证失败的卡片，后续在analysis.py中会进行进一步处理")
                        return cards
                        
            except Exception as e:
                logger.error(f"卡片生成失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                import traceback
                logger.error(traceback.format_exc())
                if attempt == max_retries:
                    return []
        
        return []
    
    def _parse_observations_from_text(self, text: str, duration: float) -> List[Observation]:
        """从文本响应中解析观察记录"""
        observations = []
        
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
                items = data.get("observations", [])
                
                for item in items:
                    obs = Observation(
                        start_ts=float(item.get("start_ts", 0)),
                        end_ts=float(item.get("end_ts", duration)),
                        text=item.get("text", ""),
                        app_name=item.get("app_name"),
                        window_title=item.get("window_title"),
                        file_hint=item.get("file_hint")
                    )
                    observations.append(obs)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}, 原文: {text[:200]}")
            # 如果 JSON 解析失败，创建一个基于整段文本的观察记录
            observations.append(Observation(
                start_ts=0,
                end_ts=duration,
                text=text[:500]
            ))
        
        return observations
    
    def _parse_cards_from_text(
        self, text: str, start_time: Optional[datetime], total_duration: float = 0
    ) -> List[ActivityCard]:
        """从文本响应中解析活动卡片"""
        cards = []
        now = datetime.now().replace(tzinfo=None)
        
        try:
            # 尝试多种方式提取JSON
            json_data = None
            
            # 方法0：先移除markdown代码块标记（```json ... ```）
            cleaned_text = text
            markdown_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
            if markdown_match:
                cleaned_text = markdown_match.group(1)
                logger.debug("移除markdown代码块标记")
            
            # 方法1：尝试匹配标准的JSON数组或对象
            json_match = re.search(r'\[[\s\S]*\]', cleaned_text)
            if json_match:
                try:
                    json_data = json.loads(json_match.group())
                    logger.debug("使用方法1成功解析JSON数组")
                except json.JSONDecodeError:
                    pass
            
            # 方法2：尝试匹配JSON对象（包含cards字段）
            if json_data is None:
                json_match = re.search(r'\{[\s\S]*\}', cleaned_text)
                if json_match:
                    try:
                        json_data = json.loads(json_match.group())
                        logger.debug("使用方法2成功解析JSON对象")
                    except json.JSONDecodeError:
                        pass
            
            # 方法3：尝试修复常见的JSON格式问题
            if json_data is None:
                try:
                    # 移除可能的多余逗号
                    fixed_text = re.sub(r',\s*([}\]])', r'\1', cleaned_text)
                    # 移除注释
                    fixed_text = re.sub(r'//.*?\n', '\n', fixed_text)
                    fixed_text = re.sub(r'/\*.*?\*/', '', fixed_text, flags=re.DOTALL)
                    # 再次尝试提取
                    json_match = re.search(r'\{[\s\S]*\}', fixed_text)
                    if json_match:
                        json_data = json.loads(json_match.group())
                        logger.debug("使用方法3成功解析修复后的JSON")
                except json.JSONDecodeError:
                    pass
            
            if json_data is None:
                logger.warning("无法从响应中提取有效的JSON数据")
                logger.info(f"原始响应内容（前2000字符）:\n{text[:2000]}")
                logger.debug(f"完整响应长度: {len(text)} 字符")
                return []
            
            # 根据JSON格式提取卡片列表
            items = []
            if isinstance(json_data, list):
                items = json_data
            elif isinstance(json_data, dict):
                items = json_data.get("cards", [])
            else:
                logger.warning(f"未知的JSON格式: {type(json_data)}: {json_data}")
                return []
            
            for item in items:
                # 解析相对时间（秒数）
                # 注意：不再解析start_ts，开始时间由系统根据视频录制时间点设置
                card_end_ts = None
                
                # 只解析结束时间戳
                if item.get("end_ts") is not None:
                    card_end_ts = float(item.get("end_ts", 0))
                
                # 验证时间戳在合理范围内
                if card_end_ts is not None and card_end_ts < 0:
                    logger.warning(f"卡片结束时间戳为负数，修正为0: {card_end_ts}")
                    card_end_ts = 0
                
                if card_end_ts is not None and total_duration > 0 and card_end_ts > total_duration:
                    logger.warning(f"卡片结束时间戳超过观察记录时长，修正: {card_end_ts} -> {total_duration}")
                    card_end_ts = total_duration
                
                # 解析应用列表（duration_seconds稍后在analysis.py中根据窗口记录精确计算）
                app_sites = []
                for app in item.get("app_sites", []):
                    app_sites.append(AppSite(
                        name=app.get("name", ""),
                        duration_seconds=0  # 暂时设为0，稍后在analysis.py中精确计算
                    ))
                
                card = ActivityCard(
                    category=item.get("category", "其他"),
                    title=item.get("title", "未命名活动"),
                    summary=item.get("summary", ""),
                    start_time=None,  # 稍后在analysis.py中设置
                    app_sites=app_sites,
                    productivity_score=float(item.get("productivity_score", 0))
                )
                
                # 只存储结束时间的相对时间戳，用于后续转换为绝对时间
                # 开始时间由系统根据视频录制时间点设置，不再使用AI推断的时间
                if card_end_ts is not None:
                    card._relative_end = card_end_ts
                
                # 解析合并相关字段
                card._merge_with_previous = bool(item.get("merge_with_previous", False))
                card._updated_summary = item.get("updated_summary")
                
                cards.append(card)
                    
        except json.JSONDecodeError as e:
            logger.warning(f"卡片 JSON 解析失败: {e}")
            logger.debug(f"原始响应内容:\n{text}")
            logger.debug(f"响应长度: {len(text)} 字符")
        except Exception as e:
            logger.error(f"卡片解析过程中发生意外错误: {e}")
            logger.debug(f"原始响应内容（前500字符）: {text[:500]}")
        
        return cards
    
    def _format_cards_for_log(self, cards: List[ActivityCard]) -> str:
        """
        格式化卡片内容用于日志输出
        
        Args:
            cards: 活动卡片列表
            
        Returns:
            str: 格式化的卡片内容字符串
        """
        if not cards:
            return "（无卡片）"
        
        lines = []
        for i, card in enumerate(cards, 1):
            line = f"  卡片{i}: {card.category} - {card.title}"
            
            if hasattr(card, '_relative_end') and card._relative_end is not None:
                line += f" (end_ts: {card._relative_end:.1f}s)"
            elif card._next_card_start_time:
                line += f" (end: {card._next_card_start_time.strftime('%H:%M:%S')})"
            
            if card.summary:
                line += f"\n    描述: {card.summary[:100]}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def _validate_card_continuity(self, cards: List[ActivityCard]) -> tuple[bool, str]:
        """
        验证卡片时间连续性（基于相对时间）
        
        验证规则：
        1. 每张卡片必须有结束时间的相对时间（_relative_end）
        2. 结束时间必须 > 6秒（最小有效持续时间）
        3. 检查与下一张卡片的时间连续性（基于相对时间）
        
        注意：这里只验证相对时间，绝对时间在analysis.py中设置后再验证
        
        Returns:
            (is_valid, error_message): 验证结果和错误信息
        """
        if not cards:
            return True, ""
        
        for i, card in enumerate(cards):
            # 检查卡片是否有相对结束时间
            if not hasattr(card, '_relative_end') or card._relative_end is None:
                return False, f"卡片 {i+1} 的结束时间未设置（缺少end_ts字段）"
            
            # 检查卡片持续时间是否合理（至少6秒）
            if card._relative_end < 6:
                return False, f"卡片 {i+1} 的持续时间过短：{card._relative_end}秒（最小要求6秒）"
            
            # 检查与下一张卡片的时间连续性
            if i < len(cards) - 1:
                next_card = cards[i + 1]
                if not hasattr(next_card, '_relative_end') or next_card._relative_end is None:
                    return False, f"卡片 {i+2} 的结束时间未设置（缺少end_ts字段）"
                
                # 检查是否有时间重叠
                if card._relative_end > next_card._relative_end:
                    # 相对时间应该是递增的，不应该出现当前卡片结束时间晚于下一张卡片结束时间
                    # 注意：这里假设卡片的相对时间是相对于批次开始时间的，且是递增的
                    return False, f"卡片 {i+1} 的结束时间 ({card._relative_end}s) 晚于卡片 {i+2} 的结束时间 ({next_card._relative_end}s)，时间顺序错误"
        
        return True, ""
    
    async def health_check(self) -> bool:
        """检查 API 连接状态"""
        try:
            messages = [{"role": "user", "content": "hi"}]
            await self._chat_completion(messages)
            return True
        except Exception as e:
            logger.warning(f"API 健康检查失败: {e}")
            return False
    
    async def generate_daily_summary(
        self,
        cards: List[ActivityCard],
        date: Optional[datetime] = None,
        model: Optional[str] = None,
        thinking_mode: Optional[str] = None,
        inspiration_cards: Optional[List] = None
    ) -> tuple[str, str]:
        """
        生成每日总结（包含事件总结和灵感总结）
        
        Args:
            cards: 活动卡片列表
            date: 日期（可选）
            model: 模型名称（可选，不传则使用默认的每日总结模型）
            thinking_mode: 思考模式（可选，不传则使用默认的每日总结思考模式）
            inspiration_cards: 灵感卡片列表（可选）
            
        Returns:
            (event_summary, inspiration_summary): 事件总结内容和灵感总结内容
        """
        # 使用配置的每日总结模型，如果未指定
        summary_model = model or config.DAILY_SUMMARY_MODEL
        summary_thinking_mode = thinking_mode if thinking_mode is not None else config.SUMMARY_THINKING_MODE
        
        # 生成事件总结
        if not cards:
            event_summary = "今天没有活动记录。"
        else:
            # 构建活动记录文本
            cards_text = f"日期: {date.strftime('%Y-%m-%d')}\n\n" if date else ""
            cards_text += "今日活动记录：\n"
            
            # 按类别分组统计
            category_stats: Dict[str, int] = {}
            total_duration = 0
            
            for card in cards:
                duration_min = int(card.duration_minutes)
                total_duration += duration_min
                category_stats[card.category] = category_stats.get(card.category, 0) + duration_min
                
                cards_text += f"\n[{card.start_time.strftime('%H:%M')} - {card.end_time.strftime('%H:%M')} ({duration_min}分钟)]\n"
                cards_text += f"类别: {card.category}\n"
                cards_text += f"标题: {card.title}\n"
                if card.summary:
                    cards_text += f"详情: {card.summary}\n"
                cards_text += f"效率评分: {card.productivity_score}\n"
                
                if card.app_sites:
                    cards_text += f"应用: {', '.join([site.name for site in card.app_sites])}\n"
            
            # 添加统计信息
            cards_text += f"\n\n统计信息：\n"
            cards_text += f"总时长: {total_duration} 分钟\n"
            cards_text += "各类别时长:\n"
            for category, duration in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
                cards_text += f"- {category}: {duration} 分钟\n"
            
            # 计算平均效率
            avg_productivity = sum(card.productivity_score for card in cards) / len(cards) if cards else 0
            cards_text += f"平均效率评分: {avg_productivity:.1f}\n"
            
            messages = [
                {"role": "system", "content": DAILY_SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": cards_text}
            ]
            
            try:
                logger.info(f"开始生成事件总结: {len(cards)} 张活动卡片，使用模型: {summary_model}, 思考模式: {summary_thinking_mode}")
                event_summary = await self._chat_completion(messages, model=summary_model, thinking_mode=summary_thinking_mode)
                logger.info(f"事件总结生成完成，字数: {len(event_summary)}")
            except Exception as e:
                logger.error(f"事件总结生成失败: {e}")
                event_summary = f"总结生成失败: {str(e)}"
        
        # 生成灵感总结
        if not inspiration_cards or len(inspiration_cards) == 0:
            inspiration_summary = "今天没有灵感记录。"
        else:
            # 构建灵感记录文本
            inspiration_text = f"日期: {date.strftime('%Y-%m-%d')}\n\n" if date else ""
            inspiration_text += f"今日灵感记录（共 {len(inspiration_cards)} 条）：\n\n"
            
            # 按类别分组
            category_inspirations: Dict[str, List] = {}
            for card in inspiration_cards:
                if card.category not in category_inspirations:
                    category_inspirations[card.category] = []
                category_inspirations[card.category].append(card)
            
            # 按类别输出
            for category, cards in sorted(category_inspirations.items()):
                inspiration_text += f"【{category}】\n"
                for idx, card in enumerate(cards, 1):
                    inspiration_text += f"{idx}. {card.content}\n"
                    if card.timestamp:
                        inspiration_text += f"   时间: {card.timestamp.strftime('%H:%M')}\n"
                    if card.notes:
                        inspiration_text += f"   备注: {', '.join(card.notes)}\n"
                    inspiration_text += "\n"
            
            messages = [
                {"role": "system", "content": INSPIRATION_SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": inspiration_text}
            ]
            
            try:
                logger.info(f"开始生成灵感总结: {len(inspiration_cards)} 条灵感记录，使用模型: {summary_model}, 思考模式: {summary_thinking_mode}")
                inspiration_summary = await self._chat_completion(messages, model=summary_model, thinking_mode=summary_thinking_mode)
                logger.info(f"灵感总结生成完成，字数: {len(inspiration_summary)}")
            except Exception as e:
                logger.error(f"灵感总结生成失败: {e}")
                inspiration_summary = f"灵感总结生成失败: {str(e)}"
        
        return event_summary, inspiration_summary
    
    async def generate_event_summary(
        self,
        cards: List[ActivityCard],
        date: Optional[datetime] = None,
        model: Optional[str] = None,
        thinking_mode: Optional[str] = None
    ) -> str:
        """
        生成事件总结
        
        Args:
            cards: 活动卡片列表
            date: 日期（可选）
            model: 模型名称（可选，不传则使用默认的每日总结模型）
            thinking_mode: 思考模式（可选，不传则使用默认的每日总结思考模式）
            
        Returns:
            事件总结内容
        """
        # 使用配置的每日总结模型，如果未指定
        summary_model = model or config.DAILY_SUMMARY_MODEL
        summary_thinking_mode = thinking_mode if thinking_mode is not None else config.SUMMARY_THINKING_MODE
        
        # 生成事件总结
        if not cards:
            event_summary = "今天没有活动记录。"
        else:
            # 构建活动记录文本
            cards_text = f"日期: {date.strftime('%Y-%m-%d')}\n\n" if date else ""
            cards_text += "今日活动记录：\n"
            
            # 按类别分组统计
            category_stats: Dict[str, int] = {}
            total_duration = 0
            
            for card in cards:
                duration_min = int(card.duration_minutes)
                total_duration += duration_min
                category_stats[card.category] = category_stats.get(card.category, 0) + duration_min
                
                cards_text += f"\n[{card.start_time.strftime('%H:%M')} - {card.end_time.strftime('%H:%M')} ({duration_min}分钟)]\n"
                cards_text += f"类别: {card.category}\n"
                cards_text += f"标题: {card.title}\n"
                if card.summary:
                    cards_text += f"详情: {card.summary}\n"
                cards_text += f"效率评分: {card.productivity_score}\n"
                
                if card.app_sites:
                    cards_text += f"应用: {', '.join([site.name for site in card.app_sites])}\n"
            
            # 添加统计信息
            cards_text += f"\n\n统计信息：\n"
            cards_text += f"总时长: {total_duration} 分钟\n"
            cards_text += "各类别时长:\n"
            for category, duration in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
                cards_text += f"- {category}: {duration} 分钟\n"
            
            # 计算平均效率
            avg_productivity = sum(card.productivity_score for card in cards) / len(cards) if cards else 0
            cards_text += f"平均效率评分: {avg_productivity:.1f}\n"
            
            messages = [
                {"role": "system", "content": DAILY_SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": cards_text}
            ]
            
            try:
                logger.info(f"开始生成事件总结: {len(cards)} 张活动卡片，使用模型: {summary_model}, 思考模式: {summary_thinking_mode}")
                event_summary = await self._chat_completion(messages, model=summary_model, thinking_mode=summary_thinking_mode)
                logger.info(f"事件总结生成完成，字数: {len(event_summary)}")
            except Exception as e:
                logger.error(f"事件总结生成失败: {e}")
                event_summary = f"总结生成失败: {str(e)}"
        
        return event_summary
    
    async def generate_inspiration_summary(
        self,
        event_summary: str,
        inspiration_cards: List,
        date: Optional[datetime] = None,
        model: Optional[str] = None,
        thinking_mode: Optional[str] = None
    ) -> str:
        """
        生成灵感总结（基于事件总结和灵感卡片）
        
        Args:
            event_summary: 事件总结内容
            inspiration_cards: 灵感卡片列表
            date: 日期（可选）
            model: 模型名称（可选，不传则使用默认的每日总结模型）
            thinking_mode: 思考模式（可选，不传则使用默认的每日总结思考模式）
            
        Returns:
            灵感总结内容
        """
        # 使用配置的每日总结模型，如果未指定
        summary_model = model or config.DAILY_SUMMARY_MODEL
        summary_thinking_mode = thinking_mode if thinking_mode is not None else config.SUMMARY_THINKING_MODE
        
        # 生成灵感总结
        if not inspiration_cards or len(inspiration_cards) == 0:
            inspiration_summary = "今天没有灵感记录。"
        else:
            # 构建灵感记录文本
            inspiration_text = f"日期: {date.strftime('%Y-%m-%d')}\n\n" if date else ""
            
            # 只有当事件总结已生成时才添加事件总结
            if event_summary and event_summary.strip():
                inspiration_text += f"今日事件总结：\n{event_summary}\n\n"
            
            inspiration_text += f"今日灵感记录（共 {len(inspiration_cards)} 条）：\n\n"
            
            # 按类别分组
            category_inspirations: Dict[str, List] = {}
            for card in inspiration_cards:
                if card.category not in category_inspirations:
                    category_inspirations[card.category] = []
                category_inspirations[card.category].append(card)
            
            # 按类别输出
            for category, cards in sorted(category_inspirations.items()):
                inspiration_text += f"【{category}】\n"
                for idx, card in enumerate(cards, 1):
                    inspiration_text += f"{idx}. {card.content}\n"
                    if card.timestamp:
                        inspiration_text += f"   时间: {card.timestamp.strftime('%H:%M')}\n"
                    if card.notes:
                        inspiration_text += f"   备注: {', '.join(card.notes)}\n"
                    inspiration_text += "\n"
            
            messages = [
                {"role": "system", "content": INSPIRATION_SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": inspiration_text}
            ]
            
            try:
                logger.info(f"开始生成灵感总结: {len(inspiration_cards)} 条灵感记录，使用模型: {summary_model}, 思考模式: {summary_thinking_mode}")
                inspiration_summary = await self._chat_completion(messages, model=summary_model, thinking_mode=summary_thinking_mode)
                logger.info(f"灵感总结生成完成，字数: {len(inspiration_summary)}")
            except Exception as e:
                logger.error(f"灵感总结生成失败: {e}")
                inspiration_summary = f"灵感总结生成失败: {str(e)}"
        
        return inspiration_summary
    
    async def generate_weekly_summary(
        self,
        daily_summaries: List[Dict],
        missing_days: List[datetime],
        end_date: Optional[datetime] = None,
        model: Optional[str] = None
    ) -> str:
        """
        生成每周总结（基于过去7天的每日总结）
        
        Args:
            daily_summaries: 每日总结列表，每个元素包含date, event_summary, inspiration_summary
            missing_days: 缺失每日总结的日期列表
            end_date: 结束日期（默认为当前日期）
            model: 模型名称（可选，不传则使用默认的每日总结模型）
            
        Returns:
            每周总结内容
        """
        # 使用配置的每日总结模型，如果未指定
        summary_model = model or config.DAILY_SUMMARY_MODEL
        
        if not daily_summaries:
            return "过去7天没有任何每日总结记录，无法生成每周总结。"
        
        # 构建每周总结文本
        end_date_str = end_date.strftime('%Y-%m-%d') if end_date else datetime.now().strftime('%Y-%m-%d')
        start_date = end_date - timedelta(days=6) if end_date else datetime.now() - timedelta(days=6)
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        weekly_text = f"每周总结报告\n"
        weekly_text += f"时间范围: {start_date_str} 至 {end_date_str}\n"
        weekly_text += f"共 {len(daily_summaries)} 天有记录，{len(missing_days)} 天无记录\n\n"
        
        # 添加每日总结内容
        weekly_text += "每日总结详情：\n"
        for summary in daily_summaries:
            date_str = summary['date'].strftime('%Y-%m-%d')
            weekly_text += f"\n【{date_str}】\n"
            weekly_text += f"事件总结：{summary['event_summary']}\n"
            if summary['inspiration_summary'] and summary['inspiration_summary'] != '暂无灵感总结':
                weekly_text += f"灵感总结：{summary['inspiration_summary']}\n"
            weekly_text += "\n"
        
        # 添加缺失日期信息
        if missing_days:
            missing_dates_str = ", ".join([d.strftime('%Y-%m-%d') for d in missing_days])
            weekly_text += f"\n缺失记录的日期：{missing_dates_str}\n"
        
        # 构建提示词
        system_prompt = """你是一位专业的时间管理顾问，擅长分析用户的每日活动总结并生成有价值的每周总结报告。

你的任务是：
1. 分析用户过去7天的每日活动总结
2. 识别主要活动模式和趋势
3. 发现效率提升或下降的原因
4. 提供具体的改进建议
5. 总结本周的亮点和需要改进的地方

输出要求：
- 使用清晰的markdown格式
- 包含数据洞察和趋势分析
- 提供具体可行的改进建议
- 语言简洁明了，重点突出
- 使用emoji增加可读性

报告结构：
1. 📊 本周概览
2. 📈 趋势分析
3. 🎯 亮点发现
4. ⚠️ 需要关注的问题
5. 💡 改进建议
6. 🚀 下周计划建议"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": weekly_text}
        ]
        
        try:
            logger.info(f"开始生成每周总结: {len(daily_summaries)} 天有记录，{len(missing_days)} 天缺失，使用模型: {summary_model}")
            weekly_summary = await self._chat_completion(messages, model=summary_model)
            logger.info(f"每周总结生成完成，字数: {len(weekly_summary)}")
        except Exception as e:
            logger.error(f"每周总结生成失败: {e}")
            weekly_summary = f"每周总结生成失败: {str(e)}"
        
        return weekly_summary
    
    async def test_connection(self, test_image: bool = True) -> tuple[bool, str]:
        """
        测试 API 连接（包含图片测试）
        
        Args:
            test_image: 是否测试图片发送能力
            
        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        if not self.api_key:
            return False, "API Key 未配置"
        
        try:
            if test_image:
                red_image = self._create_test_image([255, 0, 0])
                green_image = self._create_test_image([0, 255, 0])
                blue_image = self._create_test_image([0, 0, 255])
                
                content = [
                    {"type": "text", "text": "这里有三张纯色图片，请分别告诉我第一张、第二张、第三张图片分别是什么颜色。"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{red_image}",
                            "detail": "low"
                        }
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{green_image}",
                            "detail": "low"
                        }
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{blue_image}",
                            "detail": "low"
                        }
                    }
                ]
                messages = [{"role": "user", "content": content}]
                response = await self._chat_completion(messages)
                return True, f"连接成功！模型: {self.model}\n视觉测试通过，回复: {response[:150]}"
            else:
                messages = [{"role": "user", "content": "你好，请回复'测试成功'"}]
                response = await self._chat_completion(messages)
                return True, f"连接成功！模型: {self.model}\n回复: {response[:100]}"
        except httpx.HTTPStatusError as e:
            return False, f"HTTP 错误 {e.response.status_code}: {e.response.text[:200]}"
        except httpx.ConnectError:
            return False, "连接失败：无法连接到服务器"
        except httpx.TimeoutException:
            return False, "连接超时"
        except Exception as e:
            return False, f"错误: {str(e)}"
    
    def _create_test_image(self, color: List[int] = None) -> str:
        """创建一个简单的测试图片（纯色）并返回 base64
        
        Args:
            color: RGB颜色值，默认为红色[255, 0, 0]
            
        Returns:
            base64编码的图片字符串
        """
        import cv2
        import numpy as np
        import base64
        
        if color is None:
            color = [255, 0, 0]
        
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :] = color
        
        _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(buffer).decode('utf-8')


# 便捷函数：同步调用
def transcribe_video_sync(video_path: str, duration: float, **kwargs) -> List[Observation]:
    """同步版本的视频分析"""
    provider = DayflowBackendProvider(**kwargs)
    
    async def _run():
        try:
            return await provider.transcribe_video(video_path, duration)
        finally:
            await provider.close()
    
    return asyncio.run(_run())


def generate_cards_sync(
    observations: List[Observation],
    context_cards: Optional[List[ActivityCard]] = None,
    **kwargs
) -> List[ActivityCard]:
    """同步版本的卡片生成"""
    provider = DayflowBackendProvider(**kwargs)
    
    async def _run():
        try:
            return await provider.generate_activity_cards(observations, context_cards)
        finally:
            await provider.close()
    
    return asyncio.run(_run())


def generate_daily_summary_sync(
    cards: List[ActivityCard],
    date: Optional[datetime] = None,
    model: Optional[str] = None,
    thinking_mode: Optional[str] = None,
    inspiration_cards: Optional[List] = None,
    **kwargs
) -> tuple[str, str]:
    """同步版本的每日总结生成"""
    provider = DayflowBackendProvider(**kwargs)
    
    async def _run():
        try:
            return await provider.generate_daily_summary(cards, date, model, thinking_mode, inspiration_cards)
        finally:
            await provider.close()
    
    return asyncio.run(_run())


def generate_event_summary_sync(
    cards: List[ActivityCard],
    date: Optional[datetime] = None,
    model: Optional[str] = None,
    thinking_mode: Optional[str] = None,
    **kwargs
) -> str:
    """同步版本的事件总结生成"""
    provider = DayflowBackendProvider(**kwargs)
    
    async def _run():
        try:
            return await provider.generate_event_summary(cards, date, model, thinking_mode)
        finally:
            await provider.close()
    
    return asyncio.run(_run())


def generate_inspiration_summary_sync(
    event_summary: str,
    inspiration_cards: List,
    date: Optional[datetime] = None,
    model: Optional[str] = None,
    thinking_mode: Optional[str] = None,
    **kwargs
) -> str:
    """同步版本的灵感总结生成（基于事件总结和灵感卡片）"""
    provider = DayflowBackendProvider(**kwargs)
    
    async def _run():
        try:
            return await provider.generate_inspiration_summary(event_summary, inspiration_cards, date, model, thinking_mode)
        finally:
            await provider.close()
    
    return asyncio.run(_run())


def generate_weekly_summary_sync(
    daily_summaries: List[Dict],
    missing_days: List[datetime],
    end_date: Optional[datetime] = None,
    model: Optional[str] = None,
    **kwargs
) -> str:
    """同步版本的每周总结生成（基于过去7天的每日总结）
    
    Args:
        daily_summaries: 每日总结列表，每个元素包含date, event_summary, inspiration_summary
        missing_days: 缺失每日总结的日期列表
        end_date: 结束日期（默认为当前日期）
        model: 模型名称（可选，不传则使用默认的每日总结模型）
        
    Returns:
        每周总结内容
    """
    provider = DayflowBackendProvider(**kwargs)
    
    async def _run():
        try:
            return await provider.generate_weekly_summary(daily_summaries, missing_days, end_date, model)
        finally:
            await provider.close()
    
    return asyncio.run(_run())


async def generate_weekly_event_summary_async(
    daily_summaries: List[Dict],
    missing_days: List[datetime],
    end_date: Optional[datetime] = None,
    model: Optional[str] = None,
    **kwargs
) -> str:
    """
    生成每周事件总结（基于过去7天的每日事件总结）
    
    Args:
        daily_summaries: 每日总结列表，每个元素包含date, event_summary, inspiration_summary
        missing_days: 缺失每日总结的日期列表
        end_date: 结束日期（默认为当前日期）
        model: 模型名称（可选）
        
    Returns:
        每周事件总结内容
    """
    provider = DayflowBackendProvider(**kwargs)
    
    try:
        summary_model = model or config.DAILY_SUMMARY_MODEL
        
        if not daily_summaries:
            return "过去7天没有任何每日事件总结记录，无法生成每周事件总结。"
        
        end_date_str = end_date.strftime('%Y-%m-%d') if end_date else datetime.now().strftime('%Y-%m-%d')
        start_date = end_date - timedelta(days=6) if end_date else datetime.now() - timedelta(days=6)
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        weekly_text = f"每周事件总结报告\n"
        weekly_text += f"时间范围: {start_date_str} 至 {end_date_str}\n"
        weekly_text += f"共 {len(daily_summaries)} 天有记录，{len(missing_days)} 天无记录\n\n"
        
        weekly_text += "每日事件总结详情：\n"
        for summary in daily_summaries:
            date_str = summary['date'].strftime('%Y-%m-%d')
            weekly_text += f"\n【{date_str}】\n"
            if summary['event_summary']:
                weekly_text += f"事件总结：{summary['event_summary']}\n"
            weekly_text += "\n"
        
        if missing_days:
            missing_dates_str = ", ".join([d.strftime('%Y-%m-%d') for d in missing_days])
            weekly_text += f"\n缺失记录的日期：{missing_dates_str}\n"
        
        system_prompt = """你是一位专业的时间管理顾问，擅长分析用户的每日活动事件总结并生成有价值的每周事件总结报告。

你的任务是：
1. 分析用户过去7天的每日活动事件总结
2. 识别主要活动模式和趋势
3. 发现效率提升或下降的原因
4. 提供具体的改进建议
5. 总结本周的亮点和需要改进的地方

输出要求：
- 使用清晰的markdown格式
- 包含数据洞察和趋势分析
- 提供具体可行的改进建议
- 语言简洁明了，重点突出
- 使用emoji增加可读性

报告结构：
1. 📊 本周活动概览
2. 📈 工作效率趋势分析
3. 🎯 主要活动发现
4. ⚠️ 需要关注的问题
5. 💡 改进建议
6. 🚀 下周工作计划建议"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": weekly_text}
        ]
        
        logger.info(f"开始生成每周事件总结: {len(daily_summaries)} 天有记录，{len(missing_days)} 天缺失，使用模型: {summary_model}")
        weekly_summary = await provider._chat_completion(messages, model=summary_model)
        logger.info(f"每周事件总结生成完成，字数: {len(weekly_summary)}")
        
        return weekly_summary
    finally:
        await provider.close()


def generate_weekly_event_summary_sync(
    daily_summaries: List[Dict],
    missing_days: List[datetime],
    end_date: Optional[datetime] = None,
    model: Optional[str] = None,
    **kwargs
) -> str:
    """同步版本的每周事件总结生成
    
    Args:
        daily_summaries: 每日总结列表，每个元素包含date, event_summary, inspiration_summary
        missing_days: 缺失每日总结的日期列表
        end_date: 结束日期（默认为当前日期）
        model: 模型名称（可选）
        
    Returns:
        每周事件总结内容
    """
    return asyncio.run(generate_weekly_event_summary_async(daily_summaries, missing_days, end_date, model, **kwargs))


async def generate_weekly_inspiration_summary_async(
    daily_summaries: List[Dict],
    missing_days: List[datetime],
    end_date: Optional[datetime] = None,
    model: Optional[str] = None,
    **kwargs
) -> str:
    """
    生成每周灵感总结（基于过去7天的每日灵感总结）
    
    Args:
        daily_summaries: 每日总结列表，每个元素包含date, event_summary, inspiration_summary
        missing_days: 缺失每日总结的日期列表
        end_date: 结束日期（默认为当前日期）
        model: 模型名称（可选）
        
    Returns:
        每周灵感总结内容
    """
    provider = DayflowBackendProvider(**kwargs)
    
    try:
        summary_model = model or config.DAILY_SUMMARY_MODEL
        
        inspiration_summaries = [s for s in daily_summaries if s.get('inspiration_summary')]
        
        if not inspiration_summaries:
            return "过去7天没有任何每日灵感总结记录，无法生成每周灵感总结。"
        
        end_date_str = end_date.strftime('%Y-%m-%d') if end_date else datetime.now().strftime('%Y-%m-%d')
        start_date = end_date - timedelta(days=6) if end_date else datetime.now() - timedelta(days=6)
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        weekly_text = f"每周灵感总结报告\n"
        weekly_text += f"时间范围: {start_date_str} 至 {end_date_str}\n"
        weekly_text += f"共 {len(inspiration_summaries)} 天有灵感记录，{len(missing_days)} 天无记录\n\n"
        
        weekly_text += "每日灵感总结详情：\n"
        for summary in inspiration_summaries:
            date_str = summary['date'].strftime('%Y-%m-%d')
            weekly_text += f"\n【{date_str}】\n"
            if summary['inspiration_summary']:
                weekly_text += f"灵感总结：{summary['inspiration_summary']}\n"
            weekly_text += "\n"
        
        if missing_days:
            missing_dates_str = ", ".join([d.strftime('%Y-%m-%d') for d in missing_days])
            weekly_text += f"\n缺失记录的日期：{missing_dates_str}\n"
        
        system_prompt = """你是一位富有洞察力的创意顾问，擅长分析用户的每日灵感总结并生成有价值的每周灵感总结报告。

你的任务是：
1. 分析用户过去7天的每日灵感总结和思考
2. 发现思维模式和创意趋势
3. 识别有价值的创新点和突破性想法
4. 提供深度思考的延伸建议
5. 总结本周的灵感亮点和潜在机会

输出要求：
- 使用清晰的markdown格式
- 注重思维深度和创意价值
- 提供启发性思考和延伸建议
- 语言富有启发性和洞察力
- 使用emoji增加可读性

报告结构：
1. ✨ 本周灵感概览
2. 💭 思维模式分析
3. 🌟 亮点灵感发现
4. 🔍 深度思考延伸
5. 💡 创意建议
6. 🚀 下周思考方向"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": weekly_text}
        ]
        
        logger.info(f"开始生成每周灵感总结: {len(inspiration_summaries)} 天有记录，{len(missing_days)} 天缺失，使用模型: {summary_model}")
        weekly_summary = await provider._chat_completion(messages, model=summary_model)
        logger.info(f"每周灵感总结生成完成，字数: {len(weekly_summary)}")
        
        return weekly_summary
    finally:
        await provider.close()


def generate_weekly_inspiration_summary_sync(
    daily_summaries: List[Dict],
    missing_days: List[datetime],
    end_date: Optional[datetime] = None,
    model: Optional[str] = None,
    **kwargs
) -> str:
    """同步版本的每周灵感总结生成
    
    Args:
        daily_summaries: 每日总结列表，每个元素包含date, event_summary, inspiration_summary
        missing_days: 缺失每日总结的日期列表
        end_date: 结束日期（默认为当前日期）
        model: 模型名称（可选）
        
    Returns:
        每周灵感总结内容
    """
    return asyncio.run(generate_weekly_inspiration_summary_async(daily_summaries, missing_days, end_date, model, **kwargs))
