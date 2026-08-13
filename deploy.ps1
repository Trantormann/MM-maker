# MMmaker 一键本地部署脚本（Windows PowerShell）
# 用法：
#   .\deploy.ps1              # 完整部署（安装依赖 + 启动服务）
#   .\deploy.ps1 -SkipInstall # 跳过依赖安装，直接启动服务
#   .\deploy.ps1 -Stop        # 停止所有服务

param(
    [switch]$SkipInstall,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

function Write-Step([string]$msg) {
    Write-Host ""
    Write-Host "[MMmaker] $msg" -ForegroundColor Cyan
}

function Test-Command([string]$cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Test-PortOpen([int]$port) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return [bool]$listener
}

# ---------------------------------------------------------------------------
# 停止服务
# ---------------------------------------------------------------------------
if ($Stop) {
    Write-Step "停止 MMmaker 服务..."
    Get-Process -Name "python", "node" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "已停止（如需彻底清理请手动关闭相关终端窗口）"
    exit 0
}

Write-Step "MMmaker 本地部署开始"

# ---------------------------------------------------------------------------
# 1. 环境检查
# ---------------------------------------------------------------------------
Write-Step "1/6 检查运行环境"

if (-not (Test-Command "python")) {
    Write-Error "未检测到 Python。请先安装 Python 3.12+：https://www.python.org/downloads/"
}
$pyVersion = & python -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))"
$pyMajor, $pyMinor = $pyVersion -split "\." | ForEach-Object { [int]$_ }
if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 12)) {
    Write-Error "Python 版本过低（当前 $pyVersion），需要 3.12+。请升级 Python。"
}
Write-Host "  Python $pyVersion  OK"

if (-not (Test-Command "node")) {
    Write-Error "未检测到 Node.js。请先安装 Node.js 20+：https://nodejs.org/"
}
$nodeVersion = & node --version
Write-Host "  Node $nodeVersion  OK"

if (-not (Test-Command "pnpm")) {
    Write-Host "  未检测到 pnpm，正在通过 corepack 安装..." -ForegroundColor Yellow
    & corepack enable
    & corepack prepare pnpm@10.6.3 --activate
    if (-not (Test-Command "pnpm")) {
        Write-Error "pnpm 安装失败，请手动执行：npm install -g pnpm"
    }
}
Write-Host "  pnpm $(pnpm --version)  OK"

# ---------------------------------------------------------------------------
# 2. 环境配置文件
# ---------------------------------------------------------------------------
Write-Step "2/6 准备环境配置文件"

$envFile = Join-Path $BackendDir ".env.dev"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $BackendDir ".env.example") $envFile
    Write-Host "  已创建 .env.dev（复制自 .env.example）" -ForegroundColor Yellow
    Write-Host "  请编辑 backend\.env.dev 填写各智能体的 API Key 和模型配置。" -ForegroundColor Yellow
}
else {
    Write-Host "  .env.dev 已存在  OK"
}

# 设置 Jupyter 内核名为 mmmaker（保持 UTF-8 编码，避免中文注释被破坏）
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$envContent = [System.IO.File]::ReadAllText($envFile, [System.Text.Encoding]::UTF8)
$envContent = $envContent -replace '(?m)^JUPYTER_KERNEL_NAME=.*$', 'JUPYTER_KERNEL_NAME=mmmaker'
[System.IO.File]::WriteAllText($envFile, $envContent, $utf8NoBom)

# ---------------------------------------------------------------------------
# 3. 后端依赖 + Jupyter 内核
# ---------------------------------------------------------------------------
if (-not $SkipInstall) {
    Write-Step "3/6 安装后端依赖"

    $venvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

    # 用 python -m venv 创建虚拟环境（规避 Microsoft Store 版 Python 的 EFS 加密问题）
    if (-not (Test-Path $venvPython)) {
        Write-Host "  创建虚拟环境..."
        Push-Location $BackendDir
        & python -m venv .venv
        Pop-Location
        if (-not (Test-Path $venvPython)) {
            Write-Error "虚拟环境创建失败"
        }
    }
    else {
        Write-Host "  虚拟环境已存在，跳过创建"
    }

    # 用 pip 安装依赖（标准方式，规避 uv 在 EFS 加密环境下的兼容问题）
    Write-Host "  安装 Python 依赖（首次安装需几分钟）..."
    Push-Location $BackendDir
    & $venvPython -m pip install -r requirements.txt
    $pipExit = $LASTEXITCODE
    Pop-Location
    if ($pipExit -ne 0) {
        Write-Error "后端依赖安装失败（pip 退出码 $pipExit）"
    }

    # 注册 Jupyter 内核，确保代码沙盒使用当前虚拟环境（而非系统 Python）
    Write-Host "  注册 Jupyter 内核..."
    & $venvPython -m ipykernel install --user --name mmmaker --display-name "MMmaker Python 3" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Jupyter 内核注册失败，将回退到默认 python3 内核" -ForegroundColor Yellow
    }

    Write-Host "  后端依赖安装完成  OK"
}

# ---------------------------------------------------------------------------
# 4. 前端依赖
# ---------------------------------------------------------------------------
if (-not $SkipInstall) {
    Write-Step "4/6 安装前端依赖"

    Push-Location $FrontendDir
    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Host "  安装 npm 依赖..."
        & pnpm install
        if ($LASTEXITCODE -ne 0) {
            Pop-Location
            Write-Error "前端依赖安装失败"
        }
    }
    else {
        Write-Host "  前端依赖已存在，跳过安装"
    }
    Pop-Location
    Write-Host "  前端依赖安装完成  OK"
}

# ---------------------------------------------------------------------------
# 5. Redis
# ---------------------------------------------------------------------------
Write-Step "5/6 检查 Redis"

if (Test-PortOpen 6379) {
    Write-Host "  Redis 已在运行（端口 6379）  OK"
}
else {
    Write-Host "  Redis 未运行。任务执行依赖 Redis（消息队列与状态存储）。" -ForegroundColor Yellow
    Write-Host "  可选安装方式：" -ForegroundColor Yellow
    Write-Host "    - Memurai（Windows 推荐）: winget install Memurai.MemuraiDeveloper" -ForegroundColor Yellow
    Write-Host "    - Redis for Windows: winget install tporadowski.Redis" -ForegroundColor Yellow
    Write-Host "    - WSL: wsl --install 后执行 apt install redis-server" -ForegroundColor Yellow
    Write-Host "  后端仍会启动，但运行建模任务前请先启动 Redis。" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 6. 启动服务
# ---------------------------------------------------------------------------
Write-Step "6/6 启动服务"

# 启动后端（独立窗口）
$backendCmd = ".\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WorkingDirectory $BackendDir
Write-Host "  后端已启动（http://localhost:8000）  OK"

# 启动前端（独立窗口）
$frontendCmd = "pnpm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WorkingDirectory $FrontendDir
Write-Host "  前端已启动（http://localhost:5173）  OK"

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  MMmaker 部署完成！" -ForegroundColor Green
Write-Host "  前端界面：http://localhost:5173" -ForegroundColor Green
Write-Host "  后端 API：http://localhost:8000" -ForegroundColor Green
Write-Host "  API 文档：http://localhost:8000/docs" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  下一步：" -ForegroundColor Yellow
Write-Host "  1. 打开 http://localhost:5173" -ForegroundColor Yellow
Write-Host "  2. 进入「设置」页面，配置各智能体的 API Key 和模型" -ForegroundColor Yellow
Write-Host "  3. 返回首页，选择竞赛类型，粘贴题目，开始建模" -ForegroundColor Yellow
Write-Host ""
Write-Host "  停止服务：关闭两个终端窗口，或运行 .\deploy.ps1 -Stop" -ForegroundColor Gray
