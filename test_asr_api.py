#!/usr/bin/env python
"""
测试ASR API的简单脚本
使用方法:
python test_asr_api.py /path/to/audio.mp3
"""

import sys
import json
import uuid
import hashlib
import requests
import os.path

def main():
    if len(sys.argv) < 2:
        print("请提供音频文件路径")
        print("使用方法: python test_asr_api.py /path/to/audio.mp3")
        return
    
    # 获取音频文件路径
    audio_file_path = sys.argv[1]
    if not os.path.exists(audio_file_path):
        print(f"错误: 文件不存在 - {audio_file_path}")
        return
    
    # 服务器地址，可根据需要修改
    server_url = "http://localhost:8000/api/uploadfile"
    
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
        "uuid": uuid_str,
        "task_id": task_id,
        "mode_id": 10001,  # 默认模板ID，根据需要修改
        "language": "auto",  # 自动检测语言
        "ai_mode": "GPT-4o",  # 使用的AI模式
        "speaker": False  # 是否启用说话人分离
    }
    
    # 发送请求
    files = {
        'file': (filename, open(audio_file_path, 'rb'), 'audio/mpeg'),
        'extra_params': (None, json.dumps(extra_params))
    }
    
    print(f"上传文件: {filename}")
    print(f"参数: {json.dumps(extra_params, indent=2, ensure_ascii=False)}")
    print("正在发送请求...")
    
    try:
        response = requests.post(server_url, files=files)
        
        # 解析响应
        if response.status_code == 201:
            result = response.json()
            print(f"成功创建转写任务! 任务ID: {result['task_id']}")
            print(f"状态: {result['status']}")
            print(f"获取任务状态API: GET {server_url}/{result['task_id']}")
            print(f"获取转写结果API: GET {server_url}/{result['task_id']}/download")
        else:
            print(f"失败 (状态码: {response.status_code})")
            print(response.text)
    except Exception as e:
        print(f"请求失败: {str(e)}")

if __name__ == "__main__":
    main() 