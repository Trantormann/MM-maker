# MMmaker 快速开始

## 环境要求

- Python 3.12+
- Node.js 20+ 与 pnpm
- Redis（本地服务）

## 一键部署（Windows，推荐）

```powershell
# 在项目根目录执行
.\deploy.ps1              # 完整部署（安装依赖 + 启动服务）
.\deploy.ps1 -SkipInstall # 已安装过依赖，直接启动
.\deploy.ps1 -Stop        # 停止服务
```

脚本会自动完成：环境检查 → 创建 `.env.dev` → 安装后端依赖 → 注册 Jupyter 内核 → 安装前端依赖 → 启动 Redis → 启动前后端服务。

## 手动安装

### 1. 克隆仓库

```bash
git clone <repo-url> MMmaker
cd MMmaker
```

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env.dev        # Windows PowerShell: Copy-Item .env.example .env.dev
# 编辑 .env.dev，填写 API Key 和模型配置
```

### 3. 安装后端依赖

**Windows (PowerShell)**：

```powershell
cd backend
python -m venv .venv            # 创建虚拟环境（规避 Store 版 Python 的 EFS 加密问题）
.\.venv\Scripts\python.exe -m pip install -r requirements.txt   # 安装 Python 依赖
# 注册 Jupyter 内核，让代码沙盒使用当前虚拟环境
.\.venv\Scripts\python.exe -m ipykernel install --user --name mmmaker --display-name "MMmaker Python 3"
```

**macOS / Linux**：

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m ipykernel install --user --name mmmaker --display-name "MMmaker Python 3"
```

> **注意**：若使用 Microsoft Store 版 Python，需先用 `python -m venv .venv` 创建虚拟环境，再用 `.\.venv\Scripts\python.exe -m pip install` 安装依赖，避免 EFS 加密文件导致的安装失败。

### 4. 安装前端依赖

```bash
cd frontend
pnpm install
```

## 启动

### 启动 Redis

```powershell
# Windows：安装 Memurai（Redis 兼容服务，安装后自动启动）
winget install Memurai.MemuraiDeveloper

# 或 Redis for Windows
winget install tporadowski.Redis
```

```bash
# macOS / Linux
redis-server
# 或 Docker 方式
docker run -d -p 6379:6379 redis:alpine
```

### 启动后端

**Windows (PowerShell)**：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**macOS / Linux**：

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
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

## Docker 部署（可选）

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
