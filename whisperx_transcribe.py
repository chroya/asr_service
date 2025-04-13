import torch
import whisperx
import os
import sys
import time
import logging
import json

# 设置日志配置
logging.basicConfig(level=logging.INFO, format='--------%(asctime)s------- - %(levelname)s - File: -----%(file_name)s------ - Language: %(lang)s - %(message)s')

def audio_transcribe(model, audio, batch_size ,language):
    start_time = time.time()
    try:
        
        result = model.transcribe(audio, batch_size=batch_size ,language=language)
        
        return result, time.time() - start_time
    except Exception as e:
        logging.error('Error during audio loading or transcription: %s', str(e), extra={'file_name': os.path.basename(audio_file_path), 'lang': 'unknown'})
        raise

def align_transcription(result, model_a, metadata, audio, device,language):
    start_time = time.time()
    try:
        result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
        return result, time.time() - start_time
    except Exception as e:
        logging.error('Error during transcription alignment: %s', str(e), extra={'file_name': os.path.basename(audio_file_path), 'lang': language})
        raise

def write_result_to_file(file_path, result):
    try:
        with open(file_path, 'w') as f:
            f.write(result)
    except Exception as e:
        logging.error('Error writing result to file: %s', str(e), extra={'file_name': os.path.basename(file_path), 'lang': 'unknown'})

def handle_error(audio_file_path,excpt):
    try:
        with open(audio_file_path, 'w') as f:
            f.write("err "+str(excpt))
    except Exception as e:
        logging.error('Error writing error to file: %s', str(e), extra={'file_name': os.path.basename(audio_file_path), 'lang': 'unknown'})

def transcribe_audio(audio_file_path, language):
    extra = {'file_name': os.path.basename(audio_file_path), 'lang': language}
    logging.info('Starting transcription process', extra=extra)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    batch_size = 16
    compute_type = "float16" if device == "cuda" else "float32"
    audio_file_export_path = os.path.splitext(audio_file_path)[0] + ".txt"
    print("set exprot file:"+audio_file_export_path)

    try:
        
        logging.info("Model 1 load start", extra=extra)
        
        #语言好像是这样处理：load_model(model_name, device=device, device_index=device_index, download_root=model_dir, compute_type=compute_type, language=args['language']
        #model = whisperx.load_model("large-v3", device, compute_type=compute_type,language =language)
        # model_dir = "/root/model/"
        #这里加了language =language后，就不会出现出现：No language specified, language will be first be detected for each audio file (increases inference time)
        # asr_options = {
        # "initial_prompt": "这是一段会议记录。",
        # }
        
        model = whisperx.load_model("base", device, compute_type=compute_type,language =language, task='transcribe')
        audio = whisperx.load_audio(audio_file_path)
        
        #语言有生效，设置什么语言，输出就转写和翻译成什么语言
        result, load_transcribe_time = audio_transcribe(model, audio, batch_size, language)
        logging.info("语言："+result["language"], extra=extra)
        logging.info("------------audio_transcribe end--------------", extra=extra)
        
        logging.info(f"Audio loaded and transcribed successfully in-------- {load_transcribe_time:.2f} --------seconds", extra=extra)
        
        logging.info("Model 2 load start", extra=extra)
        
        #语言需要带着load_align_model
        model_a, metadata = whisperx.load_align_model(device=device,language_code =language )
        #这里的语言没有使用
        aligned_result, align_time = align_transcription(result, model_a, metadata, audio, device, language)
        logging.info(f"Transcription aligned successfully in-------- {align_time:.2f} --------seconds", extra=extra)
        # aligned_result = result
        
        #aligned_result['words']={}
        #aligned_result['word_segments']={}
        segments = aligned_result["segments"]

        # 遍历segments数组
        for segment in segments:
            # 检查当前segment是否有words键
            if "words" in segment:
                # 删除words键
                del segment["words"]
        
        write_result_to_file(audio_file_export_path , json.dumps(segments))

    except Exception as e:
        handle_error(audio_file_export_path,e)
        logging.error('An error occurred during the transcription process', str(e), extra=extra)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python whisperx_transcribe.py <language_code> <audio_file_path>")
        sys.exit(1)

    language_code = sys.argv[1]
    audio_file_path = sys.argv[2]

    transcribe_audio(audio_file_path, language_code)