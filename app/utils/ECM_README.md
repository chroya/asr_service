# ECM 音频格式转换工具

这个工具用于将ECM格式（EchoMemo）的音频文件转换为标准的WAV或MP3格式。

## ECM格式说明

ECM格式是一种自定义的音频封装格式，具有以下特点：

- 文件头：
  - 前3字节：ECM标识符 (0x45, 0x43, 0x4D)
  - 第4字节：版本号 (0x01)
  - 第5字节：录音类型 (0x01-CALL, 0x02-NOTE)
  - 6-20字节：预留区域

- 文件体：
  - 每60字节为一个chunk单元，表示20ms长度的语音
  - 使用Opus编码，解码后为20ms的PCM数据（640字节）
  - 采样率：16kHz，单声道，16位

## 依赖项

运行脚本前需要安装以下Python库：

```bash
pip install opuslib wave pydub
```

对于MP3转换功能，还需要安装ffmpeg：

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
- Windows: 下载ffmpeg并添加到PATH环境变量

## 使用方法

### 单个文件转换

```bash
python ecm_to_wav.py input.ecm [-o output.wav] [-m]
```

参数说明：
- `input.ecm`：输入ECM文件
- `-o, --output`：指定输出WAV文件路径（默认与输入文件同名但扩展名为.wav）
- `-m, --mp3`：同时生成MP3文件

### 批量转换

```bash
python batch_ecm_to_wav.py input_dir [-o output_dir] [-p "*.ecm"] [-m]
```

参数说明：
- `input_dir`：输入目录，包含ECM文件
- `-o, --output_dir`：输出目录（默认与输入目录相同）
- `-p, --pattern`：文件匹配模式（默认为"*.ecm"）
- `-m, --mp3`：同时生成MP3文件

## 示例

转换单个文件：

```bash
python ecm_to_wav.py recording.ecm -o output.wav -m
```

批量转换目录中的所有ECM文件：

```bash
python batch_ecm_to_wav.py ./recordings -o ./converted -m
```

## 故障排除

1. 如果遇到"不是有效的ECM文件"错误，请确认文件格式是否符合ECM规范
2. 如果解码失败，可能是ECM文件损坏或格式不兼容
3. 如果生成MP3失败，请确认已正确安装ffmpeg 