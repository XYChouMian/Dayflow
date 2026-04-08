"""
验证活跃度感知配置
"""
import sys
sys.path.insert(0, r'd:\Projects\Dayflow')

import config

print("=" * 60)
print("活跃度感知配置验证")
print("=" * 60)
print(f"ENABLE_AUTO_PAUSE: {config.ENABLE_AUTO_PAUSE}")
print(f"IDLE_THRESHOLD: {config.IDLE_THRESHOLD} 秒 ({config.IDLE_THRESHOLD/60:.1f} 分钟)")
print(f"THINKING_WINDOW: {config.THINKING_WINDOW} 秒 ({config.THINKING_WINDOW/60:.1f} 分钟)")
print(f"MIN_ACTIVITY_COUNT: {config.MIN_ACTIVITY_COUNT} 次")
print(f"CPU_THRESHOLD: {config.CPU_THRESHOLD}%")
print(f"ENABLE_CPU_CHECK: {config.ENABLE_CPU_CHECK}")
print(f"ENABLE_WINDOW_CHECK: {config.ENABLE_WINDOW_CHECK}")
print(f"AUTO_PAUSE_THRESHOLD: {config.AUTO_PAUSE_THRESHOLD} 秒 ({config.AUTO_PAUSE_THRESHOLD/60:.1f} 分钟)")
print(f"AUTO_RESUME_THRESHOLD: {config.AUTO_RESUME_THRESHOLD} 秒 ({config.AUTO_RESUME_THRESHOLD/60:.1f} 分钟)")
print("=" * 60)

expected_values = {
    "IDLE_THRESHOLD": 60,
    "AUTO_PAUSE_THRESHOLD": 60,
    "AUTO_RESUME_THRESHOLD": 20,
    "THINKING_WINDOW": 30,
    "MIN_ACTIVITY_COUNT": 1
}

all_correct = True
for key, expected in expected_values.items():
    actual = getattr(config, key)
    if actual == expected:
        print(f"✓ {key}: {actual} (正确)")
    else:
        print(f"✗ {key}: {actual} (期望: {expected})")
        all_correct = False

print("=" * 60)
if all_correct:
    print("✓ 所有配置值验证通过！")
    print("\n配置说明：")
    print("- 用户 1 分钟无活动后暂停录制")
    print("- 用户恢复活动 20 秒后恢复录制")
    print("- 思考窗口 30 秒，允许短暂思考不被判断为闲置")
    print("- 思考窗口内只需 1 次操作即可保持活跃状态")
    sys.exit(0)
else:
    print("✗ 部分配置值验证失败")
    sys.exit(1)
