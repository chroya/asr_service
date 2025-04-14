#!/usr/bin/env python
"""
测试ASR API的简单脚本
使用方法:
python test_asr_api.py /path/to/audio.mp3 [jwt_token]
"""

import sys
import json
import uuid
import hashlib
import requests
import os.path

def main():
    if len(sys.argv) < 2:
        print("请提供音频文件路径和JWT令牌")
        print("使用方法: python test_asr_api.py /path/to/audio.mp3 [jwt_token]")
        return
    
    # 获取音频文件路径
    audio_file_path = sys.argv[1]
    if not os.path.exists(audio_file_path):
        print(f"错误: 文件不存在 - {audio_file_path}")
        return
    
    # 获取JWT令牌（如果提供）
    jwt_token = sys.argv[2] if len(sys.argv) > 2 else None
    if not jwt_token:
        print("警告: 未提供JWT令牌，API调用可能会失败")
    
    # 服务器地址，可根据需要修改
    server_url = "http://43.154.130.149:8000/api/uploadfile"
    
    # 生成唯一ID
    u_id = 123  # 用户ID，根据实际情况修改
    uuid_str = str(uuid.uuid4()).replace("-", "")
    
    # 计算文件的md5作为task_id
    with open(audio_file_path, 'rb') as f:
        file_hash = hashlib.md5(f.read(2*1024*1024)).hexdigest()  # 读取前2MB计算md5
    
    task_id = f"{file_hash}"
    
    # 准备文件和参数
    filename = os.path.basename(audio_file_path)
    
    # 构建extra_params
    extra_params = {
        "u_id": u_id,
        "record_file_name": filename,
        "task_id": task_id,
        "mode_id": 10001,  # 默认模板ID，根据需要修改
        "language": "auto",  # 自动检测语言
        "ai_mode": "GPT-4",  # 使用的AI模式
        "speaker": False,  # 是否启用说话人分离
        "whisper_arch": "base",  # whisper模型架构
        "content_id": str(uuid.uuid4()),  # 内容ID
        "server_id": "local-test"  # 服务器ID
    }
    
    # 准备请求头
    headers = {}
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"
    
    # 发送请求
    files = {
        'file': (filename, open(audio_file_path, 'rb'), 'audio/mpeg'),
        'extra_params': (None, json.dumps(extra_params))
    }
    
    print(f"上传文件: {filename}")
    print(f"参数: {json.dumps(extra_params, indent=2, ensure_ascii=False)}")
    print("正在发送请求...")
    
    try:
        response = requests.post(server_url, files=files, headers=headers)
        
        # 解析响应
        if response.status_code == 200:
            result = response.json()
            print(f"成功创建转写任务!")
            print(f"任务ID: {result['task_id']}")
            print(f"客户端ID: {result['client_id']}")
            print(f"文件名: {result['filename']}")
            print(f"创建时间: {result['created_at']}")
            print(f"状态码: {result['code']}")
            print(f"消息: {result['message']}")
            
            # 打印获取结果的API
            base_url = server_url.rsplit('/', 1)[0]
            print(f"\n获取转写结果API: GET {base_url}/download/{result['task_id']}")
            print("注意：调用下载API时需要在请求头中包含相同的JWT令牌")
        else:
            print(f"失败 (状态码: {response.status_code})")
            print(response.text)
            
        # 打印速率限制信息（如果有）
        rate_limit_headers = [
            "X-Rate-Limit-Audio-Seconds",
            "X-Rate-Limit-Requests",
            "X-Rate-Remaining-Audio-Seconds",
            "X-Rate-Remaining-Requests",
            "X-Rate-Reset-Audio-Seconds",
            "X-Rate-Reset-Requests",
            "Retry-After"
        ]
        
        rate_limits = {h: response.headers.get(h) for h in rate_limit_headers if h in response.headers}
        if rate_limits:
            print("\n速率限制信息:")
            for header, value in rate_limits.items():
                print(f"{header}: {value}")
            
    except Exception as e:
        print(f"请求失败: {str(e)}")

if __name__ == "__main__":
    main() 