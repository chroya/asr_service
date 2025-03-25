from datetime import timedelta

def convert_to_time_format(seconds: float) -> str:
    # 使用 timedelta 来处理时间
    td = timedelta(seconds=seconds)
    
    # 获取小时、分钟和秒
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # 格式化为 "HH:MM:SS"
    return f"{hours:02}:{minutes:02}:{seconds:02}"
