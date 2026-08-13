# MMmaker 快速开始

## 环境要求

- Python 3.12+
- Node.js 20+
- Redis（本地部署需要）
- pnpm（前端包管理）

## 安装

### 1. 克隆仓库

```bash
git clone <repo-url> MMmaker
cd MMmaker
```

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env.dev
# 编辑 .env.dev，填写 API Key 和模型配置
```

### 3. 安装后端依赖

```bash
cd backend
pip install uv
uv sync
```

### 4. 安装前端依赖

```bash
cd frontend
pnpm install
```

## 启动

### 启动 Redis

```bash
# Docker 方式
docker run -d -p 6379:6379 redis:alpine

# 或使用系统 Redis
redis-server
```

### 启动后端

```bash
cd backend
ENV=DEV uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 启动前端

```bash
cd frontend
pnpm run dev
```

## 使用

1. 打开 http://localhost:5173
2. 进入"设置"页面，配置各智能体的 API Key 和模型
3. 返回首页，选择竞赛类型，粘贴题目
4. 点击"开始建模"
5. 在任务页面实时查看执行进度
6. 在 HIL 检查点做出决策
7. 任务完成后查看生成的论文

## Docker 部署

```bash
# 1. 创建后端环境配置文件
cp backend/.env.example backend/.env.dev
# 编辑 backend/.env.dev，填写 API Key 和模型配置

# 2. 启动所有服务
docker-compose up -d
```

访问：
- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs
