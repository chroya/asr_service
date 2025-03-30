# 语音转写服务 (ASR Service)

基于FastAPI、Celery和WhisperX的语音转写服务，提供API接口，支持音频转文本功能。

## 功能特点

- 🔊 **多语言支持**: 支持多种语言的转写，包括中文、英语等多种语言
- ⚡ **高效处理**: 采用先进的WhisperX技术，提供高效的音频转写
- 📊 **使用统计**: 通过u_id跟踪用户转写使用情况，支持使用限制
- 🔄 **实时状态更新**: 任务创建、处理和完成的实时更新通知
- 📄 **结果导出**: 支持下载转写结果，包含时间戳信息
- 🚀 **分布式处理**: 使用Celery任务队列进行分布式音频转写处理

## 技术栈

- **后端**: FastAPI, SQLAlchemy, Pydantic
- **音频处理**: WhisperX (基于OpenAI的Whisper模型)
- **存储**: SQLite (可扩展到PostgreSQL等)
- **消息队列**: Redis, MQTT
- **任务队列**: Celery, Flower (任务监控)
- **日志**: 按小时自动滚动的日志系统

## 安装指南

### 前置条件

- Python 3.8+
- Redis服务器（用于Celery和数据存储）
  redis服务本地部署：
  ```bash
     sudo apt install redis-server
     sudo nano /etc/redis/redis.conf # 修改配置文件，可选
     sudo systemctl start redis
     sudo systemctl enable redis  # 设置开机自启，可选
  ```
- MQTT代理 (可选，用于通知)

### 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/yourusername/asr_service.git
cd asr_service
```

2. 创建并激活虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # 在Windows上使用: venv\Scripts\activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```
注意：transformers不要用4.50，可以降级到4.49

4. 创建配置文件

```bash
cp .env.example .env
```

5. 编辑`.env`文件，根据需要配置参数

6. 初始化数据库

```bash
python -m app.db.init_db
```

7. 启动服务

```bash
# 启动FastAPI服务
uvicorn app.main:app --reload

# 在另一个终端中启动Celery Worker
python celery_worker.py

# 可选：启动Flower监控（在另一个终端）
python celery_flower.py
# 或直接使用命令
# celery -A app.core.celery.celery_app flower --port=5555
```

## 使用指南

### API接口

API接口文档可以通过访问 http://localhost:8000/api/docs 获取。主要接口包括：
  
- 转写接口:
  - 创建转写任务: `POST /api/uploadfile`
  - 获取任务状态: `GET /api/task/{task_id}`
  - 获取转写结果: `GET /api/download/{task_id}`
  - 获取任务列表: `GET /api/tasks`
- 系统接口:
  - 健康检查: `GET /api/health`

### 演示页面

系统提供了两种界面用于测试和使用转写功能：

- 简易演示页面：访问 http://localhost:8000/demo 获取简单的文件上传演示
- 完整Web界面：访问 http://localhost:8000/web/ 获取完整的用户界面体验
- Celery任务监控：访问 http://localhost:5555 查看任务队列监控

#### 示例：创建转写任务

```bash
curl -X POST "http://localhost:8000/api/uploadfile" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/audio.mp3" \
  -F "extra_params={
    \"u_id\": 111,
    \"record_file_name\": \"audio.mp3\",
    \"uuid\": \"f62b91e6b6f04d6793e16f8ef5d03dc3\",
    \"task_id\": \"79edb736a27979ac5d2b024749499864\",
    \"mode_id\": 10001,
    \"language\": \"zh\",
    \"ai_mode\": \"GPT-4o\",
    \"speaker\": false
  }"
```

## 性能测试

### 压力测试工具

为了测试API的并发处理能力，项目提供了异步压测脚本。该脚本使用`asyncio`和`aiohttp`模拟多用户并发上传音频文件，并记录性能指标。

#### 安装压测依赖

```bash
# 安装压测所需依赖
pip install -r tests/requirements.txt
```

#### 使用方法

压测脚本位于`tests/load_test.py`，支持多种参数自定义：

```bash
# 基本用法 - 默认10个并发用户，持续60秒
python tests/load_test.py

# 自定义参数
python tests/load_test.py --url http://localhost:8000/api/uploadfile --users 20 --duration 120 --audio-dir ./uploads
```

主要参数说明：
- `--url`: 转写API的URL（默认：http://localhost:8000/api/uploadfile）
- `--users`: 并发用户数（默认：10）
- `--duration`: 测试持续时间，单位秒（默认：60）
- `--audio-dir`: 音频文件目录，脚本会自动搜索该目录下的音频文件（默认：./uploads）

#### 测试结果解析

压测完成后，脚本会生成详细的测试报告，包含以下指标：

- **请求数据**：总请求数、成功/失败请求数、成功率
- **性能指标**：每秒请求数(RPS)、测试持续时间
- **响应时间**：最小/最大/平均响应时间
- **百分位数据**：50%/90%/95%/99%请求的响应时间

#### 测试策略建议

1. **梯度测试**：从低并发(5-10)开始，逐步增加到中等(20-50)和高并发(100+)
2. **系统监控**：测试期间建议使用`htop`或`top`监控服务器资源使用情况
3. **关键指标**：重点关注RPS(每秒请求数)和95%请求的响应时间
4. **瓶颈分析**：当响应时间急剧增加或成功率下降时，表明系统达到性能瓶颈

压测日志会保存到`load_test.log`文件，可用于后续分析。

## 部署指南

### 使用Docker部署

1. 构建Docker镜像:

```bash
docker build -t asr-service .
```

2. 运行容器:

```bash
docker run -p 8000:8000 -v $(pwd)/data:/app/data --env-file .env asr-service
```

### 使用NGINX和Gunicorn部署

1. 安装Gunicorn:

```bash
pip install gunicorn
```

2. 创建systemd服务文件:

```
[Unit]
Description=ASR Service
After=network.target

[Service]
User=yourusername
Group=yourgroup
WorkingDirectory=/path/to/asr_service
ExecStart=/path/to/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app -b 0.0.0.0:8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

3. 配置NGINX:

```
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /path/to/asr_service/app/static;
    }
}
```

### 使用Supervisor部署

1. 安装supervisor:

```bash
# Ubuntu/Debian
sudo apt-get install supervisor

# CentOS
sudo yum install supervisor

# macOS
brew install supervisor
```

2. 配置文件已准备好（supervisor_config.ini），包含以下服务：
   - asr_api: FastAPI 服务
   - asr_celery: Celery Worker
   - asr_flower: Flower监控服务

3. 启动supervisor服务：

```bash
# 启动supervisor
supervisord -c supervisor_config.ini

# 查看所有进程状态
supervisorctl -c supervisor_config.ini status

# 启动所有服务
supervisorctl -c supervisor_config.ini start all

# 重启所有服务
supervisorctl -c supervisor_config.ini restart all

# 停止所有服务
supervisorctl -c supervisor_config.ini stop all

# 也可以单独控制某个服务，例如：
supervisorctl -c supervisor_config.ini restart asr_api
```

4. 查看日志：
   - API服务日志：`logs/api.log` 和 `logs/api_error.log`
   - Celery Worker日志：`logs/celery.log` 和 `logs/celery_error.log`
   - Flower监控日志：`logs/flower.log` 和 `logs/flower_error.log`

## 项目结构

```
asr_service/
├── app/                      # 应用程序包
│   ├── core/                 # 核心模块
│   │   ├── celery.py         # Celery配置
│   ├── models/               # 数据模型
│   ├── routes/               # 路由模块
│   │   ├── api/              # API路由
│   │   └── web/              # Web界面路由
│   ├── services/             # 服务层
│   ├── static/               # 静态文件
│   └── utils/                # 工具函数
│       ├── files.py          # 文件处理工具
│       └── logging_config.py # 日志配置
├── celery_worker.py          # Celery Worker启动脚本
├── celery_flower.py          # Celery Flower启动脚本
├── tests/                    # 测试目录
│   ├── load_test.py          # 压力测试脚本
│   └── requirements.txt      # 测试依赖
├── supervisor_config.ini     # Supervisor配置
└── requirements.txt          # 项目依赖
```

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

## 贡献

欢迎贡献代码、报告问题或提出改进建议。
