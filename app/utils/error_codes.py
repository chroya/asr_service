"""
转写服务错误码定义
"""

# 成功状态码
SUCCESS = 0

# 错误码前缀
# 10xx - 文件相关错误
# 11xx - 任务状态相关错误
# 12xx - 服务错误

# 文件相关错误 (10xx)
ERROR_FILE_NOT_FOUND = 1001        # 音频文件不存在
ERROR_PROCESSING_FAILED = 1002     # 处理失败
ERROR_INVALID_FILE_FORMAT = 1003   # 无效的音频文件格式
ERROR_FILE_TOO_LARGE = 1004        # 文件大小超过限制

# 任务状态相关错误 (11xx)
ERROR_TASK_NOT_FOUND = 1101        # 任务不存在
ERROR_TASK_NOT_COMPLETED = 1102    # 任务尚未完成
ERROR_RESULT_NOT_FOUND = 1103      # 任务结果不存在
ERROR_MAX_RETRY_EXCEEDED = 1104    # 任务重试次数超限

# 服务错误 (12xx)
ERROR_SERVICE_UNAVAILABLE = 1201   # 服务不可用
ERROR_RATE_LIMIT_EXCEEDED = 1202   # 超出速率限制

# 错误码对应的描述信息
ERROR_MESSAGES = {
    SUCCESS: "file upload success",  
    ERROR_FILE_NOT_FOUND: "音频文件不存在",
    ERROR_PROCESSING_FAILED: "处理失败",
    ERROR_INVALID_FILE_FORMAT: "无效的音频文件。支持的格式：MP3, WAV, FLAC, M4A, OGG",
    ERROR_FILE_TOO_LARGE: "文件大小超过限制",
    ERROR_TASK_NOT_FOUND: "任务不存在",
    ERROR_TASK_NOT_COMPLETED: "任务尚未完成",
    ERROR_RESULT_NOT_FOUND: "任务结果不存在",
    ERROR_MAX_RETRY_EXCEEDED: "任务重试次数超限，任务已被取消",
    ERROR_SERVICE_UNAVAILABLE: "服务不可用",
    ERROR_RATE_LIMIT_EXCEEDED: "超出速率限制"
}

def get_error_message(code: int, custom_message: str = None) -> str:
    """
    获取错误码对应的描述信息
    
    Args:
        code: 错误码
        custom_message: 自定义错误信息
        
    Returns:
        str: 错误描述信息
    """
    
    if custom_message:
        return custom_message
    
    return ERROR_MESSAGES.get(code, f"未知错误 (代码: {code})") 