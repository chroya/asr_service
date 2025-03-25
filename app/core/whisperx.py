import os
import json
import logging
import torch
import whisperx
from typing import Dict, Any, Optional, Tuple, Callable
from datetime import datetime
from faster_whisper import transcribe
from app.core.config import settings

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
        callback: Optional[Callable[[int, str], None]] = None
    ) -> Tuple[Dict[str, Any], float]:
        """
        处理音频文件
        
        Args:
            file_path: 音频文件路径
            task_id: 任务ID
            language: 音频语言代码（如不提供则自动检测）
            callback: 进度回调函数，接收进度百分比和消息参数
            
        Returns:
            Tuple[Dict[str, Any], float]: 转写结果和音频时长
        """
        logger.info(f"开始处理音频文件: {file_path}, 任务ID: {task_id}")
        
        # 更新进度
        if callback:
            callback(10, "正在加载模型...")
        
        try:
            # 步骤1: 加载模型并转写
            if callback:
                callback(20, "正在转写音频...")
            
            # 加载whisper模型
            model = self._get_model("tiny")
            
            # 转写音频
            # transcription = whisperx.transcribe(
            #     audio=file_path,
            #     model=model,
            #     language=language,
            #     device=DEVICE
            # )
            transcription = model.transcribe(file_path, batch_size=16)
            
            # 提取检测到的语言
            detected_language = transcription.get("language", language)
            audio_duration = transcription.get("segments", [{}])[-1].get("end", 0) if transcription.get("segments") else 0
            
            if callback:
                callback(50, "正在对齐时间戳...")
            
            # 步骤2: 使用VAD过滤
            # if audio_duration > 1.0:  # 只有当音频长度大于1秒时进行VAD过滤
            #     try:
            #         # 加载VAD模型
            #         vad_model, vad_metadata = whisperx.load_vad_model(DEVICE)
                    
            #         # 使用VAD过滤
            #         vad_segments = whisperx.get_vad_segments(
            #             file_path, 
            #             vad_model,
            #             vad_metadata, 
            #             DEVICE,
            #             min_speech_duration_ms=250
            #         )
                    
            #         if callback:
            #             callback(60, "正在对齐文本...")
                    
            #         # 步骤3: 加载对齐模型
            #         if detected_language:
            #             # 对齐模型只支持部分语言
            #             supported_langs = ["en", "zh", "de", "es", "fr", "it", "ja", "ko", "pl", "pt", "ru", "tr", "nl", "ca"]
            #             if detected_language in supported_langs:
            #                 try:
            #                     align_model, align_metadata = whisperx.load_align_model(
            #                         language_code=detected_language,
            #                         device=DEVICE
            #                     )
                                
            #                     # 对齐转写结果
            #                     aligned_transcription = whisperx.align(
            #                         transcription["segments"],
            #                         align_model,
            #                         align_metadata,
            #                         file_path,
            #                         DEVICE,
            #                     )
                                
            #                     # 更新segments
            #                     transcription["segments"] = aligned_transcription["segments"]
                                
            #                     if callback:
            #                         callback(70, "正在完善对齐结果...")
            #                 except Exception as e:
            #                     logger.warning(f"对齐模型加载或处理失败，使用原始转写结果: {str(e)}")
            #     except Exception as e:
            #         logger.warning(f"VAD处理失败，使用原始转写结果: {str(e)}")
            
            # 步骤4: 提取完整文本
            if callback:
                callback(80, "正在生成最终结果...")
            
            # 从segments中提取完整文本
            full_text = ""
            for segment in transcription.get("segments", []):
                if "text" in segment:
                    full_text += segment["text"] + " "
            
            # 构建最终结果
            result = {
                "text": full_text.strip(),
                "language": detected_language,
                "segments": transcription.get("segments", [])
            }
            
            # 保存结果
            if callback:
                callback(90, "正在保存结果...")
            
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"音频处理完成: {task_id}, 时长: {audio_duration}秒")
            
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