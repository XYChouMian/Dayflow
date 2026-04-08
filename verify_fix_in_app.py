"""
验证修复在实际应用中的效果
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from core.health_reminder import HealthReminder, ActivitySession
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

def verify_fix_in_app():
    """验证修复在实际应用中的效果"""
    print("验证修复在实际应用中的效果\n")
    
    # 创建模拟存储
    storage = Mock()
    storage.get_setting = Mock(return_value="true")
    
    health_reminder = HealthReminder(storage)
    health_reminder.entertainment_threshold_minutes = 30
    health_reminder.work_threshold_minutes = 60
    
    # 测试用户报告的场景：游戏时间满了，但显示工作持续了很久
    print("=== 用户报告的场景：游戏时间满了，但显示工作持续了很久 ===")
    test_cards = [
        MockCard("编程", 60, 150, 85),      # 1小时编程，2.5小时前
        MockCard("游戏", 120, 30, 15),     # 2小时游戏，30分钟前
        MockCard("会议", 30, 0, 70),        # 30分钟会议，刚刚结束
    ]
    
    print("活动卡片:")
    for i, card in enumerate(test_cards):
        print(f"  {i+1}. {card.category}: {card.duration_minutes}分钟, 结束时间: {card.end_time}")
    
    # 检查会话构建
    sessions = health_reminder._build_sessions(test_cards)
    print(f"\n构建的会话数量: {len(sessions)}")
    
    for i, session in enumerate(sessions):
        print(f"  会话{i+1}: 类别={session.category}, 持续时间={session.duration_minutes:.0f}分钟")
        print(f"    是否工作活动: {session.is_work_activity()}")
        print(f"    是否娱乐活动: {session.is_entertainment_activity()}")
    
    # 检查提醒
    result = health_reminder.analyze_activities(test_cards)
    if result:
        print(f"\n✅ 提醒触发: {result.type.value}")
        print(f"  消息: {result.message}")
        print(f"  类别: {result.category}")
        
        # 验证修复效果
        if result.type.value == "entertainment_too_long" and result.category == "游戏":
            print("\n🎉 修复成功！游戏提醒正确触发，没有被工作提醒覆盖")
            return True
        elif result.type.value == "work_too_long":
            print("\n❌ 修复失败！仍然触发工作提醒，游戏提醒被覆盖")
            return False
    else:
        print("\n❌ 提醒未触发")
        return False

def verify_session_separation():
    """验证会话分离效果"""
    print("\n=== 验证会话分离效果 ===")
    
    # 创建模拟存储
    storage = Mock()
    storage.get_setting = Mock(return_value="true")
    
    health_reminder = HealthReminder(storage)
    health_reminder.entertainment_threshold_minutes = 30
    health_reminder.work_threshold_minutes = 60
    
    # 测试会话分离
    test_cards = [
        MockCard("编程", 60, 90, 85),      # 1小时编程，1.5小时前
        MockCard("游戏", 40, 0, 15),       # 40分钟游戏，刚刚结束
    ]
    
    sessions = health_reminder._build_sessions(test_cards)
    
    # 检查游戏会话是否被正确分离
    game_sessions = [s for s in sessions if s.category == "游戏"]
    work_sessions = [s for s in sessions if s.is_work_activity()]
    
    print(f"游戏会话数量: {len(game_sessions)}")
    print(f"工作会话数量: {len(work_sessions)}")
    
    if len(game_sessions) == 1 and len(work_sessions) == 1:
        print("✅ 会话分离成功！游戏和工作会话正确分离")
        return True
    else:
        print("❌ 会话分离失败！游戏会话被错误合并")
        return False

def verify_priority_logic():
    """验证优先级逻辑"""
    print("\n=== 验证优先级逻辑 ===")
    
    # 创建模拟存储
    storage = Mock()
    storage.get_setting = Mock(return_value="true")
    
    health_reminder = HealthReminder(storage)
    health_reminder.entertainment_threshold_minutes = 30
    health_reminder.work_threshold_minutes = 60
    
    # 测试当前会话优先级
    test_cards = [
        MockCard("游戏", 40, 0, 15),       # 40分钟游戏，刚刚结束（当前会话）
        MockCard("编程", 60, 90, 85),      # 1小时编程，1.5小时前
    ]
    
    result = health_reminder.analyze_activities(test_cards)
    
    if result and result.type.value == "entertainment_too_long":
        print("✅ 当前会话优先级正确！游戏提醒优先触发")
        return True
    else:
        print("❌ 当前会话优先级错误！游戏提醒未优先触发")
        return False

if __name__ == "__main__":
    print("开始验证修复在实际应用中的效果\n")
    
    test1 = verify_fix_in_app()
    test2 = verify_session_separation()
    test3 = verify_priority_logic()
    
    print(f"\n=== 验证结果 ===")
    print(f"用户场景修复: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"会话分离验证: {'✅ 通过' if test2 else '❌ 失败'}")
    print(f"优先级逻辑验证: {'✅ 通过' if test3 else '❌ 失败'}")
    
    if test1 and test2 and test3:
        print("\n🎉 所有验证通过！游戏会话合并问题已完全修复")
        print("用户的问题'游戏时间满了，还是显示的工作持续了很久'已解决")
    else:
        print("\n❌ 部分验证失败，需要进一步修复")