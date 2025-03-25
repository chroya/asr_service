#!/bin/bash
# 测试ASR API的简单脚本
# 使用方法: ./test_asr_api.sh /path/to/audio.mp3 [server_url]

# 检查参数
if [ $# -lt 1 ]; then
  echo "请提供音频文件路径"
  echo "使用方法: ./test_asr_api.sh /path/to/audio.mp3 [server_url]"
  exit 1
fi

# 音频文件路径
AUDIO_FILE=$1

# 检查文件是否存在
if [ ! -f "$AUDIO_FILE" ]; then
  echo "错误: 文件不存在 - $AUDIO_FILE"
  exit 1
fi

# 服务器地址，如果提供了第二个参数则使用，否则使用默认值
SERVER_URL=${2:-"http://localhost:8000/api/uploadfile"}

# 生成UUID
UUID=$(uuidgen | tr -d '-')

# 计算文件的MD5值（使用前2MB）
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  TASK_ID=$(dd if="$AUDIO_FILE" bs=2m count=1 2>/dev/null | md5)
else
  # Linux
  TASK_ID=$(dd if="$AUDIO_FILE" bs=2M count=1 2>/dev/null | md5sum | cut -d' ' -f1)
fi

# 获取文件名
FILENAME=$(basename "$AUDIO_FILE")

# 构建extra_params
EXTRA_PARAMS='{
  "u_id": 123,
  "record_file_name": "'$FILENAME'",
  "uuid": "'$UUID'",
  "task_id": "'$TASK_ID'",
  "mode_id": 10001,
  "language": "auto",
  "ai_mode": "GPT-4o",
  "speaker": false
}'

echo "上传文件: $FILENAME"
echo "服务器URL: $SERVER_URL"
echo "UUID: $UUID"
echo "任务ID: $TASK_ID"
echo "正在发送请求..."

# 发送请求
curl -X POST "$SERVER_URL" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@$AUDIO_FILE" \
  -F "extra_params=$EXTRA_PARAMS" \
  -w "\n\n状态码: %{http_code}\n" \
  | tee response.json

echo ""
echo "请求完成，响应已保存到 response.json"
echo "获取任务状态: curl -X GET \"$SERVER_URL/$TASK_ID\""
echo "获取转写结果: curl -X GET \"$SERVER_URL/$TASK_ID/download\"" 