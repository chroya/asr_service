#!/usr/bin/env python
"""
针对ASR服务核心API的自动化测试
测试功能：
1. uploadfile接口 - 支持文件上传并转写
2. get_task_status接口 - 获取任务状态
"""

import os
import time
import json
import uuid
import hashlib
import pytest
import requests
from pathlib import Path

# 测试配置
BASE_URL = os.environ.get("ASR_API_BASE_URL", "http://192.168.1.18:8000")
JWT_TOKEN = os.environ.get("ASR_API_JWT_TOKEN", None)
TEST_FILES_DIR = Path(__file__).parent / "test_files"
TIMEOUT_SECONDS = 300  # 等待转写完成的超时时间

# 确保测试文件目录存在
TEST_FILES_DIR.mkdir(exist_ok=True)

# 支持的文件格式
SUPPORTED_FORMATS = [
    {"ext": "mp3", "mime": "audio/mpeg"},
    {"ext": "wav", "mime": "audio/wav"},
    {"ext": "ecm", "mime": "application/octet-stream"},
]

def get_headers():
    """获取请求头"""
    headers = {}
    if JWT_TOKEN:
        headers["Authorization"] = f"Bearer {JWT_TOKEN}"
    return headers

def calculate_task_id(file_path):
    """计算文件的md5作为task_id"""
    with open(file_path, 'rb') as f:
        file_hash = hashlib.md5(f.read(2*1024*1024)).hexdigest()  # 读取前2MB计算md5
    return file_hash

def wait_for_task_completion(task_id, timeout=TIMEOUT_SECONDS):
    """等待转写任务完成，超时返回当前状态"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(
            f"{BASE_URL}/api/get_task_status?task_id={task_id}",
            headers=get_headers()
        )
        
        if response.status_code != 200:
            print(f"获取任务状态失败: {response.status_code}")
            print(response.text)
            time.sleep(5)
            continue
            
        result = response.json()
        code = result.get("code")
        
        # 任务完成
        if code == 0:
            return True, result
        
        # 任务失败
        if code < 0 and code != -4:  # -4是任务未上传的状态
            return False, result
            
        print(f"等待转写任务完成，当前状态: {result.get('msg')}")
        time.sleep(5)
    
    # 超时返回当前状态
    response = requests.get(
        f"{BASE_URL}/api/get_task_status?task_id={task_id}",
        headers=get_headers()
    )
    return False, response.json() if response.status_code == 200 else {"code": -999, "msg": "获取状态超时"}

def create_test_file(ext, content=None, size_kb=10):
    """创建测试文件，如果不提供内容则创建指定大小的随机文件"""
    file_path = TEST_FILES_DIR / f"test_file.{ext}"
    
    # 如果提供了内容，直接写入
    if content:
        with open(file_path, 'wb') as f:
            f.write(content)
        return file_path
    
    # 创建随机内容文件
    with open(file_path, 'wb') as f:
        # 写入一些随机数据
        f.write(os.urandom(size_kb * 1024))
    
    return file_path

class TestCoreAPIs:
    """测试ASR服务的核心API"""
    
    def test_upload_file_basic(self):
        """测试基本的文件上传功能"""
        # 创建一个测试WAV文件
        test_file_path = TEST_FILES_DIR / "test_audio.wav"
        if not test_file_path.exists():
            pytest.skip(f"测试文件不存在: {test_file_path}")
        
        # 计算文件的task_id
        task_id = calculate_task_id(test_file_path)
        
        # 准备请求参数
        extra_params = {
            "u_id": 123,
            "record_file_name": test_file_path.name,
            "task_id": task_id,
            "mode_id": 10001,
            "language": "auto",
            "ai_mode": "GPT-4o",
            "speaker": False,
            "whisper_arch": "base"
        }
        
        # 发送请求
        files = {
            'file': (test_file_path.name, open(test_file_path, 'rb'), 'audio/wav'),
            'extra_params': (None, json.dumps(extra_params))
        }
        
        response = requests.post(
            f"{BASE_URL}/api/uploadfile",
            files=files,
            headers=get_headers()
        )
        
        # 验证响应
        assert response.status_code == 200, f"上传失败: {response.text}"
        result = response.json()
        assert result["task_id"] == task_id, f"返回的task_id与请求不一致: {result['task_id']} != {task_id}"
        assert result["code"] == 0, f"上传状态码不为0: {result['code']}"
        
        # 等待任务完成并验证结果
        is_completed, status_result = wait_for_task_completion(task_id)
        assert is_completed, f"转写任务未在规定时间内完成: {status_result}"
        assert status_result["code"] == 0, f"转写失败: {status_result}"
    
    @pytest.mark.parametrize("file_format", SUPPORTED_FORMATS)
    def test_upload_different_formats(self, file_format):
        """测试上传不同格式的文件"""
        ext = file_format["ext"]
        mime = file_format["mime"]
        
        # 检查测试文件是否存在
        test_file_path = TEST_FILES_DIR / f"test_audio.{ext}"
        if not test_file_path.exists():
            pytest.skip(f"测试文件不存在: {test_file_path}")
        
        # 计算文件的task_id
        task_id = calculate_task_id(test_file_path)
        
        # 准备请求参数
        extra_params = {
            "u_id": 123,
            "record_file_name": test_file_path.name,
            "task_id": task_id,
            "mode_id": 10001,
            "language": "auto",
            "ai_mode": "GPT-4o",
            "speaker": False,
            "whisper_arch": "base"
        }
        
        # 发送请求
        files = {
            'file': (test_file_path.name, open(test_file_path, 'rb'), mime),
            'extra_params': (None, json.dumps(extra_params))
        }
        
        response = requests.post(
            f"{BASE_URL}/api/uploadfile",
            files=files,
            headers=get_headers()
        )
        
        # 验证响应
        assert response.status_code == 200, f"上传{ext}文件失败: {response.text}"
        result = response.json()
        assert result["task_id"] == task_id, f"返回的task_id与请求不一致: {result['task_id']} != {task_id}"
        assert result["code"] == 0, f"上传状态码不为0: {result['code']}"
        
        # 等待任务完成并验证结果
        is_completed, status_result = wait_for_task_completion(task_id)
        assert is_completed, f"转写{ext}文件任务未在规定时间内完成: {status_result}"
        assert status_result["code"] == 0, f"转写{ext}文件失败: {status_result}"
    
    def test_upload_with_different_params(self):
        """测试不同上传参数能正常识别"""
        # 创建一个测试WAV文件
        test_file_path = TEST_FILES_DIR / "test_audio.wav"
        if not test_file_path.exists():
            pytest.skip(f"测试文件不存在: {test_file_path}")
        
        # 测试不同的参数组合
        param_combinations = [
            {"language": "zh", "speaker": True, "whisper_arch": "large-v3"},
            {"language": "en", "speaker": False, "whisper_arch": "medium"},
            {"language": "auto", "speaker": True, "whisper_arch": "small"}
        ]
        
        for params in param_combinations:
            # 计算文件的task_id并加上随机后缀，避免重复
            base_task_id = calculate_task_id(test_file_path)
            task_id = f"{base_task_id}_{uuid.uuid4().hex[:8]}"
            
            # 准备请求参数
            extra_params = {
                "u_id": 123,
                "record_file_name": test_file_path.name,
                "task_id": task_id,
                "mode_id": 10001,
                "language": params["language"],
                "ai_mode": "GPT-4o",
                "speaker": params["speaker"],
                "whisper_arch": params["whisper_arch"]
            }
            
            # 发送请求
            files = {
                'file': (test_file_path.name, open(test_file_path, 'rb'), 'audio/wav'),
                'extra_params': (None, json.dumps(extra_params))
            }
            
            response = requests.post(
                f"{BASE_URL}/api/uploadfile",
                files=files,
                headers=get_headers()
            )
            
            # 验证响应
            assert response.status_code == 200, f"上传失败 (参数: {params}): {response.text}"
            result = response.json()
            assert result["task_id"] == task_id, f"返回的task_id与请求不一致: {result['task_id']} != {task_id}"
            assert result["code"] == 0, f"上传状态码不为0: {result['code']}"
            
            # 等待任务完成并验证结果
            is_completed, status_result = wait_for_task_completion(task_id)
            assert is_completed, f"转写任务未在规定时间内完成 (参数: {params}): {status_result}"
            assert status_result["code"] == 0, f"转写失败 (参数: {params}): {status_result}"

    def test_webhook_notification(self):
        """测试webhook通知功能"""
        # 此测试需要一个能接收webhook的服务
        # 可以使用类似 RequestBin, hookbin 等服务创建临时endpoint
        webhook_url = os.environ.get("WEBHOOK_TEST_URL")
        if not webhook_url:
            pytest.skip("未设置WEBHOOK_TEST_URL环境变量")
        
        # 创建一个测试WAV文件
        test_file_path = TEST_FILES_DIR / "test_audio.wav"
        if not test_file_path.exists():
            pytest.skip(f"测试文件不存在: {test_file_path}")
        
        # 计算文件的task_id
        task_id = calculate_task_id(test_file_path)
        task_id = f"{task_id}_webhook_test"
        
        # 准备请求参数
        extra_params = {
            "u_id": 123,
            "record_file_name": test_file_path.name,
            "task_id": task_id,
            "mode_id": 10001,
            "language": "auto",
            "ai_mode": "GPT-4o",
            "speaker": False,
            "whisper_arch": "base"
        }
        
        # 发送请求
        files = {
            'file': (test_file_path.name, open(test_file_path, 'rb'), 'audio/wav'),
            'extra_params': (None, json.dumps(extra_params))
        }
        
        response = requests.post(
            f"{BASE_URL}/api/uploadfile",
            files=files,
            headers=get_headers()
        )
        
        # 验证响应
        assert response.status_code == 200, f"上传失败: {response.text}"
        result = response.json()
        assert result["task_id"] == task_id, f"返回的task_id与请求不一致: {result['task_id']} != {task_id}"
        
        # 等待任务完成
        is_completed, status_result = wait_for_task_completion(task_id)
        assert is_completed, f"转写任务未在规定时间内完成: {status_result}"
        
        # 验证webhook是否被触发
        # 这部分需要根据实际的webhook接收服务来实现
        # 例如，如果使用RequestBin，可以查询其API确认是否收到了请求
        
    def test_get_task_status(self):
        """测试获取任务状态"""
        # 创建一个测试WAV文件
        test_file_path = TEST_FILES_DIR / "test_audio.wav"
        if not test_file_path.exists():
            pytest.skip(f"测试文件不存在: {test_file_path}")
        
        # 计算文件的task_id
        task_id = calculate_task_id(test_file_path)
        task_id = f"{task_id}_status_test"
        
        # 准备请求参数
        extra_params = {
            "u_id": 123,
            "record_file_name": test_file_path.name,
            "task_id": task_id,
            "mode_id": 10001,
            "language": "auto",
            "ai_mode": "GPT-4o",
            "speaker": False,
            "whisper_arch": "base"
        }
        
        # 发送上传请求
        files = {
            'file': (test_file_path.name, open(test_file_path, 'rb'), 'audio/wav'),
            'extra_params': (None, json.dumps(extra_params))
        }
        
        response = requests.post(
            f"{BASE_URL}/api/uploadfile",
            files=files,
            headers=get_headers()
        )
        
        # 验证上传响应
        assert response.status_code == 200, f"上传失败: {response.text}"
        
        # 立即查询状态
        response = requests.get(
            f"{BASE_URL}/api/get_task_status?task_id={task_id}",
            headers=get_headers()
        )
        
        # 验证状态响应
        assert response.status_code == 200, f"获取状态失败: {response.text}"
        result = response.json()
        
        # 初始状态应该是等待处理或处理中
        assert result["code"] in [1, 2], f"初始状态码不正确: {result}"
        
        # 等待一段时间后再次查询
        time.sleep(10)
        response = requests.get(
            f"{BASE_URL}/api/get_task_status?task_id={task_id}",
            headers=get_headers()
        )
        
        # 验证状态响应
        assert response.status_code == 200, f"获取状态失败: {response.text}"
        result = response.json()
        
        # 状态应该已更新
        assert "task_id" in result, f"状态响应缺少task_id字段: {result}"
        
        # 查询不存在的任务
        nonexistent_task_id = "nonexistent_" + uuid.uuid4().hex
        response = requests.get(
            f"{BASE_URL}/api/get_task_status?task_id={nonexistent_task_id}",
            headers=get_headers()
        )
        
        # 验证状态响应
        assert response.status_code == 200, f"获取状态失败: {response.text}"
        result = response.json()
        
        # 不存在的任务应返回特定的错误码
        assert result["code"] == -4, f"不存在任务的状态码不正确: {result}"

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 