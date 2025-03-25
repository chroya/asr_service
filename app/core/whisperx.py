import os
import json
import logging
import torch
import whisperx
from typing import Dict, Any, Optional, Tuple, Callable
from datetime import datetime
from faster_whisper import transcribe
from app.core.config import settings
from app.utils.time import convert_to_time_format

logger = logging.getLogger(__name__)

# 检查是否有可用GPU
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"WhisperX使用设备: {DEVICE}")

class WhisperXProcessor:
    """
    WhisperX音频处理器，用于处理音频文件并转写为文本
    """
    
    def __init__(self):
        """初始化WhisperX处理器"""
        # 确保结果目录存在
        os.makedirs(settings.TRANSCRIPTION_DIR, exist_ok=True)
        
        # 模型缓存
        self.model_cache = {}
    
    async def process_audio(
        self, 
        file_path: str, 
        result_path: str,
        task_id: str,
        language: Optional[str] = None,
        speaker_diarization: bool = False,
        callback: Optional[Callable[[int, str], None]] = None
    ) -> Tuple[Dict[str, Any], float]:
        """
        处理音频文件
        
        Args:
            file_path: 音频文件路径
            result_path: 结果文件路径
            task_id: 任务ID
            language: 音频语言代码（如不提供则自动检测）
            speaker_diarization: 是否启用说话人分离
            callback: 进度回调函数，接收进度百分比和消息参数
            
        Returns:
            Tuple[Dict[str, Any], float]: 转写结果和音频时长
        """
        logger.info(f"开始处理音频文件: {file_path}, 任务ID: {task_id}, 语言: {language}, 启用说话人分离: {speaker_diarization}")
        
        # 更新进度
        if callback:
            callback(10, "正在加载模型...")
        
        try:
            # 步骤1: 加载模型并转写
            if callback:
                callback(20, "正在转写音频...")
            
            # 加载whisper模型
            model = self._get_model(settings.WHISPER_MODEL_NAME)
            
            # 转写音频，如果指定了语言则传入
            transcription = model.transcribe(
                file_path, 
                batch_size=16,
                language=language,
            )
            
            # 提取检测到的语言
            detected_language = transcription.get("language", language)
            audio_duration = transcription.get("segments", [{}])[-1].get("end", 0) if transcription.get("segments") else 0
            
            if callback:
                callback(50, "正在对齐时间戳...")
            
            # 启用说话人分离
            if speaker_diarization and audio_duration > 1.0:
                try:
                    if callback:
                        callback(60, "正在进行说话人分离...")
                    
                    # 加载说话人分离模型
                    diarize_model = whisperx.DiarizationPipeline(
                        use_auth_token=settings.HF_TOKEN, 
                        device=DEVICE
                    )
                    
                    # 执行说话人分离
                    diarize_segments = diarize_model(
                        file_path,
                        min_speakers=1,
                        max_speakers=5
                    )
                    
                    if callback:
                        callback(70, "正在合并说话人信息...")
                    
                    # 将说话人信息与转写结果合并
                    result = whisperx.assign_word_speakers(
                        diarize_segments,
                        transcription
                    )
                    
                    # 更新segments
                    transcription["segments"] = result["segments"]
                    
                    if callback:
                        callback(80, "说话人分离完成...")
                except Exception as e:
                    logger.warning(f"说话人分离失败，使用原始转写结果: {str(e)}")
            
            # 步骤4: 提取完整文本
            if callback:
                callback(90, "正在生成最终结果...")
            
            # 从segments中提取完整文本
            full_text = ""
            for segment in transcription.get("segments", []):
                if "text" in segment:
                    full_text += segment["text"] + " "
            
            # 构建最终结果
            result = [
                    {
                        "id": i,
                        "start": convert_to_time_format(segment.get("start", 0)),
                        "end": convert_to_time_format(segment.get("end", 0)),
                        "speaker": segment.get("speaker", "SPEAKER_00"),
                        "text": segment.get("text", ""),
                        "seek": segment.get("seek", 0),
                        "tokens": segment.get("tokens", [0]),
                        "temperature": segment.get("temperature", 0),
                        "avg_logprob": segment.get("avg_logprob", 0),
                        "compression_ratio": segment.get("compression_ratio", 0),
                        "no_speech_prob": segment.get("no_speech_prob", 0),
                        "sid": segment.get("sid", 0),
                        "language": detected_language
                    }
                    for i, segment in enumerate(transcription.get("segments", []))
                ]
            
            # 保存结果
            if callback:
                callback(95, "正在保存结果...")
            
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"音频处理完成: {task_id}, 时长: {audio_duration}秒, 语言: {detected_language}")
            
            # 完成
            if callback:
                callback(100, "处理完成")
            
            return result, audio_duration
            
        except Exception as e:
            logger.exception(f"处理音频文件失败: {str(e)}")
            raise
    
    def _get_model(self, model_size: str = "small"):
        """
        获取WhisperX模型，如果已加载则从缓存返回
        
        Args:
            model_size: 模型大小，可选值: tiny, base, small, medium, large
            
        Returns:
            加载的模型
        """
        if model_size not in self.model_cache:
            logger.info(f"加载WhisperX模型: {model_size}")
            
            self.model_cache[model_size] = whisperx.load_model(
                model_size,
                device=DEVICE,
                compute_type="float16" if DEVICE == "cuda" else "float32"
            )
        
        return self.model_cache[model_size]
    
    def clear_cache(self):
        """清除模型缓存"""
        self.model_cache.clear()
        # 强制进行垃圾回收
        import gc
        gc.collect()
        if DEVICE == "cuda":
            torch.cuda.empty_cache() 