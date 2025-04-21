from app.core.config import settings

def get_download_url(filename: str) -> str:
    """
    生成文件下载URL
    
    Args:
        filename: 文件名（不包含路径）
            - 如果传入的是路径，则自动提取文件名部分
    
    Returns:
        str: 完整的下载URL
    """
    # 如果传入的是路径，则提取文件名部分
    if '/' in filename:
        filename = filename.split('/')[-1]
    
    return f"{settings.BASE_URL}{settings.DOWNLOAD_URL_PREFIX}/{filename}" 