import datetime
import time

# 获取当前系统时区信息
print(f"当前时间: {datetime.datetime.now()}")
print(f"UTC时间: {datetime.datetime.utcnow()}")
print(f"时区偏移: {time.timezone / -3600} 小时")  # time.timezone 单位是秒，负数表示东区

# 计算时区偏移
offset_hours = -time.timezone / 3600
print(f"系统时区: UTC{'+' if offset_hours >= 0 else ''}{int(offset_hours)}")