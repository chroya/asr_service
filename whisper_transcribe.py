import whisper
import torch
import logging
import argparse
import os
from pathlib import Path
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_model(model_name="base"):
    """
    加载Whisper模型
    """
    try:
        logger.info(f"正在加载 {model_name} 模型...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model(model_name).to(device)
        logger.info(f"模型加载成功，使用设备: {device}")
        return model
    except Exception as e:
        logger.error(f"模型加载失败: {str(e)}")
        raise

def transcribe_audio(model, audio_path, language=None):
    """
    转写音频文件
    """
    try:
        logger.info(f"开始转写音频文件: {audio_path}")
        start_time = time.time()
        
        # 转写选项
        transcribe_options = {
            "task": "transcribe",
            "verbose": True
        }
        if language:
            transcribe_options["language"] = language
            
        # 执行转写
        result = model.transcribe(audio_path, **transcribe_options)
        
        duration = time.time() - start_time
        logger.info(f"转写完成，耗时: {duration:.2f} 秒")
        return result
        
    except Exception as e:
        logger.error(f"转写过程出错: {str(e)}")
        raise

def save_transcription(result, output_path):
    """
    保存转写结果
    """
    try:
        # 保存完整的JSON结果
        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        # 保存纯文本结果
        text_path = output_path.with_suffix('.txt')
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(result["text"])
            
        logger.info(f"转写结果已保存至: {json_path} 和 {text_path}")
        
    except Exception as e:
        logger.error(f"保存结果时出错: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description="使用Whisper进行音频转写")
    parser.add_argument("audio_path", help="音频文件路径")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium", "large", "large-v3"],
                      help="Whisper模型大小 (默认: base)")
    parser.add_argument("--language", help="音频语言 (例如: zh, en, ja)")
    args = parser.parse_args()
    
    try:
        # 检查文件是否存在
        audio_path = Path(args.audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"找不到音频文件: {audio_path}")
            
        # 加载模型并执行转写
        model = load_model(args.model)
        result = transcribe_audio(model, str(audio_path), args.language)
        
        # 保存结果
        output_path = audio_path.with_suffix('')
        save_transcription(result, output_path)
        
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main()) 