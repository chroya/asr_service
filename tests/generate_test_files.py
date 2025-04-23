#!/usr/bin/env python
"""
生成测试音频文件的辅助脚本
支持生成wav、mp3和ecm格式的测试文件
"""

import os
import wave
import numpy as np
import struct
from pathlib import Path
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试文件目录
TEST_FILES_DIR = Path(__file__).parent / "test_files"

def ensure_dirs():
    """确保测试文件目录存在"""
    TEST_FILES_DIR.mkdir(exist_ok=True)

def generate_sine_wave(frequency=440, duration=3, sample_rate=44100):
    """
    生成正弦波音频数据
    
    参数:
        frequency: 频率 (Hz)
        duration: 持续时间 (秒)
        sample_rate: 采样率 (Hz)
        
    返回:
        numpy array: 包含音频数据的数组
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # 生成正弦波
    sine_wave = 0.5 * np.sin(2 * np.pi * frequency * t)
    # 转换为16位PCM格式
    audio = sine_wave * 32767
    return audio.astype(np.int16)

def save_wav_file(filename, audio_data, sample_rate=44100):
    """
    将音频数据保存为WAV文件
    
    参数:
        filename: 文件名
        audio_data: 音频数据 (numpy array)
        sample_rate: 采样率 (Hz)
    """
    file_path = TEST_FILES_DIR / filename
    with wave.open(str(file_path), 'wb') as wav_file:
        # 设置参数 (nchannels, sampwidth, framerate, nframes, comptype, compname)
        wav_file.setparams((1, 2, sample_rate, 0, 'NONE', 'not compressed'))
        # 写入数据
        wav_file.writeframes(audio_data.tobytes())
    logger.info(f"保存WAV文件: {file_path}")
    return file_path

def convert_wav_to_mp3(wav_file, output_filename):
    """
    将WAV文件转换为MP3格式
    
    参数:
        wav_file: WAV文件路径
        output_filename: 输出MP3文件名
        
    返回:
        str: MP3文件路径
    """
    output_path = TEST_FILES_DIR / output_filename
    
    # 检查是否安装了ffmpeg
    try:
        # 使用ffmpeg将WAV转换为MP3
        cmd = ['ffmpeg', '-y', '-i', str(wav_file), '-codec:a', 'libmp3lame', '-qscale:a', '2', str(output_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"转换为MP3文件: {output_path}")
        return output_path
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.error(f"转换MP3失败: {e}")
        logger.error("请确保已安装ffmpeg")
        return None

def create_ecm_file(filename, content_size=1024):
    """
    创建一个简单的ECM格式文件
    
    参数:
        filename: 文件名
        content_size: 内容大小 (字节)
        
    返回:
        str: ECM文件路径
    """
    file_path = TEST_FILES_DIR / filename
    
    # ECM文件头 (简化版本)
    ecm_header = bytearray([0x45, 0x43, 0x4D, 0x00])  # "ECM" 后跟一个 null 字节
    
    # 生成随机内容
    random_content = os.urandom(content_size)
    
    # 写入文件
    with open(file_path, 'wb') as f:
        f.write(ecm_header)
        f.write(random_content)
    
    logger.info(f"创建ECM文件: {file_path}")
    return file_path

def main():
    """主函数"""
    ensure_dirs()
    
    # 生成测试音频数据 (1kHz正弦波，3秒)
    audio_data = generate_sine_wave(frequency=1000, duration=3)
    
    # 保存为WAV格式
    wav_file = save_wav_file("test_audio.wav", audio_data)
    
    # 转换为MP3格式
    mp3_file = convert_wav_to_mp3(wav_file, "test_audio.mp3")
    
    # 创建ECM格式文件
    ecm_file = create_ecm_file("test_audio.ecm")
    
    logger.info("生成测试文件完成")
    logger.info(f"WAV文件: {wav_file}")
    if mp3_file:
        logger.info(f"MP3文件: {mp3_file}")
    logger.info(f"ECM文件: {ecm_file}")

if __name__ == "__main__":
    main() 