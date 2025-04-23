import opuslib
import wave
import os
from pydub import AudioSegment

def ecm_to_wav(input_ecm_path, output_wav_path, output_mp3_path=None):
    """
    将ECM格式文件解码为WAV文件
    
    Args:
        input_ecm_path: ECM文件路径
        output_wav_path: 输出WAV文件路径
        output_mp3_path: 可选，输出MP3文件路径
    """
    # 打开ECM文件
    with open(input_ecm_path, 'rb') as f:
        # 读取文件头
        header = f.read(20)
        
        # 验证文件头 (0x45, 0x43, 0x4D 对应 'E', 'C', 'M')
        if header[0] != 0x45 or header[1] != 0x43 or header[2] != 0x4D:
            raise ValueError(f"不是有效的ECM文件，文件头前3字节应该是0x45,0x43,0x4D，实际为{header[0]:02X},{header[1]:02X},{header[2]:02X}")
        
        version = header[3]
        if version != 0x01:
            print(f"警告: ECM版本为0x{version:02X}，当前脚本为v1(0x01)版本设计")
        
        audio_type = header[4]
        if audio_type == 0x01:
            print("音频类型: CALL (0x01)")
        elif audio_type == 0x02:
            print("音频类型: NOTE (0x02)")
        else:
            print(f"未知音频类型: 0x{audio_type:02X}")
        
        # 跳过预留区域
        # header[5:20] 是预留区域
        
        # 读取文件体数据
        body_data = f.read()
    
    # 检测误操作防护标记
    error_marker = b'\xEE\xEE\xEE' + b'\x00' * 57
    if error_marker in body_data:
        print("警告: 文件可能存在误操作防护标记，尝试移除")
        body_data = body_data.replace(error_marker, b'')
    
    # 解码音频数据
    decoder = opuslib.Decoder(16000, 1)  # 16kHz, 单声道
    pcm_data = bytearray()
    
    # 每60字节为一个chunk单元，20ms长度语音
    chunk_size = 60
    for i in range(0, len(body_data), chunk_size):
        chunk = body_data[i:i + chunk_size]
        if len(chunk) == chunk_size:  # 确保是完整的chunk
            try:
                # 解码为PCM数据，每20ms解码为640字节的PCM数据
                pcm_chunk = decoder.decode(chunk, 640)
                pcm_data.extend(pcm_chunk)
            except Exception as e:
                print(f"解码chunk失败 at {i}: {e}")
    
    # 写入WAV文件
    with wave.open(output_wav_path, 'wb') as wav:
        wav.setnchannels(1)  # 单声道
        wav.setsampwidth(2)  # 16位
        wav.setframerate(16000)  # 16kHz
        wav.writeframes(pcm_data)
    
    print(f"WAV文件已保存: {output_wav_path}")
    
    # 如果指定了MP3输出路径，则转换为MP3
    if output_mp3_path:
        AudioSegment.from_wav(output_wav_path).export(
            output_mp3_path, format='mp3', bitrate='24k'
        )
        print(f"MP3文件已保存: {output_mp3_path}")
    
    # 计算音频长度
    duration_seconds = len(pcm_data) / (16000 * 2)  # 采样率 * 字节/样本
    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)
    print(f"音频长度: {minutes}分{seconds}秒")
    
    return output_wav_path

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='将ECM文件转换为WAV/MP3')
    parser.add_argument('input', help='输入ECM文件路径')
    parser.add_argument('-o', '--output', help='输出WAV文件路径 (默认为与输入同名但扩展名为.wav)')
    parser.add_argument('-m', '--mp3', action='store_true', help='同时生成MP3文件')
    
    args = parser.parse_args()
    
    input_path = args.input
    if not os.path.exists(input_path):
        print(f"错误: 输入文件 {input_path} 不存在")
        exit(1)
    
    # 设置输出文件路径
    if args.output:
        output_wav = args.output
    else:
        output_wav = os.path.splitext(input_path)[0] + '.wav'
    
    # 设置可选的MP3输出路径
    if args.mp3:
        output_mp3 = os.path.splitext(output_wav)[0] + '.mp3'
    else:
        output_mp3 = None
    
    try:
        ecm_to_wav(input_path, output_wav, output_mp3)
    except Exception as e:
        print(f"转换失败: {e}") 