# ASR服务自动化测试

本目录包含对ASR服务核心API的自动化测试脚本。

## 功能测试

主要测试以下核心能力：

1. `uploadfile`接口 - 文件上传并转写
   - 支持ecm、mp3、wav文件格式
   - 支持不同上传参数
   - 测试webhook回调功能

2. `get_task_status`接口 - 获取任务状态
   - 能正确获取不同状态的任务
   - 测试错误处理和边缘情况

## 使用方法

### 安装依赖

```bash
pip install -r requirements.txt
```

### 生成测试文件

在运行测试前，需要先生成测试音频文件：

```bash
python generate_test_files.py
```

这将在`test_files`目录中生成以下测试文件：
- `test_audio.wav` - WAV格式测试音频
- `test_audio.mp3` - MP3格式测试音频
- `test_audio.ecm` - ECM格式测试文件

注意：生成MP3文件需要安装ffmpeg。

### 运行测试

设置环境变量：

```bash
# 设置ASR服务API地址
export ASR_API_BASE_URL="http://localhost:8000"

# 设置JWT令牌（如果API需要认证）
export ASR_API_JWT_TOKEN="your_jwt_token"

# 设置Webhook测试URL（可选，用于测试webhook功能）
export WEBHOOK_TEST_URL="https://webhook.site/your-unique-url"
```

运行所有测试：

```bash
pytest -v test_core_apis.py
```

运行特定测试：

```bash
# 仅测试基本上传功能
pytest -v test_core_apis.py::TestCoreAPIs::test_upload_file_basic

# 仅测试获取任务状态
pytest -v test_core_apis.py::TestCoreAPIs::test_get_task_status
```

### 测试脚本说明

- `test_core_apis.py` - 主要测试脚本，包含所有API测试用例
- `generate_test_files.py` - 生成测试音频文件的辅助脚本
- `test_asr_api.py` - 简单的命令行测试工具，用于手动测试
- `test_asr_api.sh` - Shell版本的命令行测试工具

## 测试输出示例

成功的测试输出示例：

```
collected 5 items                                                                                               
test_core_apis.py::TestCoreAPIs::test_upload_file_basic PASSED
test_core_apis.py::TestCoreAPIs::test_upload_different_formats[mp3] PASSED
test_core_apis.py::TestCoreAPIs::test_upload_different_formats[wav] PASSED
test_core_apis.py::TestCoreAPIs::test_upload_with_different_params PASSED
test_core_apis.py::TestCoreAPIs::test_get_task_status PASSED
``` 