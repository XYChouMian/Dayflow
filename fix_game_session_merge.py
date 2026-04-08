"""
修复游戏会话被错误合并到工作会话的问题
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from core.health_reminder import HealthReminder
from unittest.mock import Mock

class MockCard:
    """模拟活动卡片类"""
    def __init__(self, category, duration_minutes, end_minutes_ago=0, productivity_score=0):
        now = datetime.now()
        self.start_time = now - timedelta(minutes=duration_minutes + end_minutes_ago)
        self.end_time = now - timedelta(minutes=end_minutes_ago)
        self.duration_minutes = duration_minutes
        self.category = category
        self.title = f'{category}活动'
        self.productivity_score = productivity_score

def create_mock_card(category, duration_minutes, end_minutes_ago=0, productivity_score=0):
    """创建模拟活动卡片"""
    return MockCard(category, duration_minutes, end_minutes_ago, productivity_score)

def test_session_merge_fix():
    """测试会话合并修复"""
    print("测试会话合并修复\n")
    
    # 创建模拟存储
    storage = Mock()
    storage.get_setting = Mock(return_value="true")
    
    # 创建健康提醒实例
    health_reminder = HealthReminder(storage)
    
    # 设置较短的阈值用于测试
    health_reminder.entertainment_threshold_minutes = 30
    health_reminder.work_threshold_minutes = 60
    health_reminder.cooldown_minutes = 5
    
    print("=== 测试场景：工作1小时 -> 游戏2小时 -> 工作30分钟 ===")
    
    # 模拟用户：工作1小时 -> 游戏2小时 -> 工作30分钟
    test_cards = [
        create_mock_card("编程", 60, 150, 85),      # 1小时编程，2.5小时前
        create_mock_card("游戏", 120, 30, 15),     # 2小时游戏，30分钟前
        create_mock_card("会议", 30, 0, 70),        # 30分钟会议，刚刚结束
    ]
    
    print("活动卡片:")
    for i, card in enumerate(test_cards):
        print(f"  {i+1}. {card.category}: {card.duration_minutes}分钟, 开始时间: {card.start_time}")
    
    # 检查会话构建
    sessions = health_reminder._build_sessions(test_cards)
    print(f"\n构建的会话数量: {len(sessions)}")
    
    for i, session in enumerate(sessions):
        print(f"  会话{i+1}: 类别={session.category}, 持续时间={session.duration_minutes:.0f}分钟")
    
    # 检查是否有游戏会话
    game_sessions = [s for s in sessions if s.category == "游戏"]
    work_sessions = [s for s in sessions if s.is_work_activity()]
    
    print(f"\n游戏会话数量: {len(game_sessions)}")
    print(f"工作会话数量: {len(work_sessions)}")
    
    if len(game_sessions) == 0:
        print("❌ 问题：游戏会话被合并到工作会话中")
        return False
    elif len(game_sessions) == 1 and len(work_sessions) >= 1:
        print("✅ 正确：游戏会话和工作会话分离")
        return True
    else:
        print("❓ 意外情况：会话数量异常")
        return False

def test_merge_logic():
    """测试合并逻辑"""
    print("\n=== 测试合并逻辑 ===")
    
    # 创建模拟存储
    storage = Mock()
    storage.get_setting = Mock(return_value="true")
    
    health_reminder = HealthReminder(storage)
    
    # 测试1：工作会话是否应该合并游戏活动
    print("测试1：工作会话是否应该合并游戏活动")
    
    # 创建工作会话
    work_session = MockCard("编程", 60, 0, 85)
    work_session.end_time = datetime.now() - timedelta(minutes=120)  # 2小时前结束
    
    # 创建游戏卡片
    game_card = create_mock_card("游戏", 120, 0, 15)
    
    # 检查是否应该合并
    should_merge = health_reminder._should_merge_sessions(work_session, {
        'category': '游戏',
        'start_time': game_card.start_time,
        'end_time': game_card.end_time,
        'productivity_score': 15
    })
    
    print(f"工作会话合并游戏活动: {should_merge}")
    
    if should_merge:
        print("❌ 问题：工作会话不应该合并游戏活动")
    else:
        print("✅ 正确：工作会话不合并游戏活动")

if __name__ == "__main__":
    test_session_merge_fix()
    test_merge_logic()