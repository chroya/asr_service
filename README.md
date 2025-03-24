# 语音转写服务 (ASR Service)

基于FastAPI和WhisperX的语音转写服务，提供Web界面和API接口，支持音频转文本功能。

## 功能特点

- 🔊 **多语言支持**: 支持多种语言的转写，包括中文、英语等多种语言
- ⚡ **高效处理**: 采用先进的WhisperX技术，提供高效的音频转写
- 🔒 **用户管理**: 完整的用户注册、登录和权限控制系统
- 📊 **使用统计**: 跟踪用户转写次数和处理时长，支持使用限制
- 📱 **响应式界面**: 友好的Web界面，支持桌面和移动设备
- 🔄 **实时状态更新**: 任务创建、处理和完成的实时更新通知
- 📄 **结果导出**: 支持下载转写结果，包含时间戳信息

## 技术栈

- **后端**: FastAPI, SQLAlchemy, Pydantic
- **音频处理**: WhisperX (基于OpenAI的Whisper模型)
- **存储**: SQLite (可扩展到PostgreSQL等)
- **消息队列**: Redis, MQTT
- **前端**: HTML, CSS, JavaScript, Bootstrap 5
- **模板**: Jinja2

## 安装指南

### 前置条件

- Python 3.8+
- Redis服务器
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
uvicorn app.main:app --reload
```

## 使用指南

### 访问Web界面

打开浏览器访问 http://localhost:8000/web 即可使用Web界面：

- 首页: `/web`
- 登录: `/web/login`
- 注册: `/web/register`
- 用户仪表板: `/web/dashboard`
- 转写界面: `/web/transcribe`
- 任务详情: `/web/task/{task_id}`

### API接口

API接口文档可以通过访问 http://localhost:8000/api/docs 获取。主要接口包括：

- 认证: `/api/auth/`
  - 注册: `POST /api/auth/register`
  - 登录: `POST /api/auth/token`
  - 用户信息: `GET /api/auth/me`
  
- 转写: `/api/transcription/`
  - 创建转写任务: `POST /api/transcription/`
  - 获取任务状态: `GET /api/transcription/{task_id}`
  - 获取转写结果: `GET /api/transcription/{task_id}/result`
  - 获取任务列表: `GET /api/transcription/`
  - 删除任务: `DELETE /api/transcription/{task_id}`

- 用户: `/api/users/`
  - 获取用户信息: `GET /api/users/me`
  - 获取用户限制: `GET /api/users/me/limits`

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

## 项目结构

```
asr_service/
├── app/                      # 应用程序包
│   ├── api/                  # API模块
│   │   └── routes/           # API路由
│   ├── core/                 # 核心模块
│   ├── db/                   # 数据库模块
│   ├── models/               # 数据模型
│   ├── services/             # 服务层
│   ├── static/               # 静态文件
│   ├── templates/            # 模板文件
│   └── main.py               # 应用入口
├── uploads/                  # 上传文件目录
├── transcriptions/           # 转写结果目录
├── .env.example              # 环境变量示例
├── requirements.txt          # 依赖项
└── README.md                 # 项目说明
```

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

## 贡献

欢迎贡献代码、报告问题或提出改进建议。
