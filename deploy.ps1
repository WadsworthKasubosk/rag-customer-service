#Requires -Version 5.1
<#
.SYNOPSIS
    RAG Customer Service — Windows PowerShell 一键部署
    对方只要双击 deploy.bat 即可，全自动检测 + 安装 + 启动
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("deploy","start","stop","stop-all","restart","status","logs","init-db","help")]
    [string]$Command = "deploy"
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir
$LogFile = Join-Path $ProjectDir "deploy.log"

# ── Colors ───────────────────────────────────────────────────────────
function Write-OK    { param($m) Write-Host "  [OK] " -ForegroundColor Green -NoNewline; Write-Host $m }
function Write-Fail  { param($m) Write-Host "  [FAIL] " -ForegroundColor Red -NoNewline; Write-Host $m }
function Write-Warn  { param($m) Write-Host "  [!] " -ForegroundColor Yellow -NoNewline; Write-Host $m }
function Write-Step  { param($m) Write-Host "`n▸ $m" -ForegroundColor Cyan }
function Write-Log   { param($m) Add-Content -Path $LogFile -Value "[$(Get-Date -f 'HH:mm:ss')] $m" }

# ── Helpers ──────────────────────────────────────────────────────────
function Test-Command { param($c) $null -ne (Get-Command $c -ErrorAction SilentlyContinue) }

function Test-TcpPort {
    param([string]$Host_, [int]$Port, [int]$Timeout = 2000)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $result = $tcp.BeginConnect($Host_, $Port, $null, $null)
        $ok = $result.AsyncWaitHandle.WaitOne($Timeout)
        if ($ok -and $tcp.Connected) { $tcp.Close(); return $true }
        $tcp.Close(); return $false
    } catch { return $false }
}

function Invoke-Logged {
    param([string]$Desc, [scriptblock]$Block)
    Write-Log "START: $Desc"
    try {
        & $Block *>> $LogFile
        Write-Log "DONE: $Desc"
    } catch {
        Write-Log "FAIL: $Desc — $_"
        throw
    }
}

# ══════════════════════════════════════════════════════════════════════
#  1. Docker
# ══════════════════════════════════════════════════════════════════════
function Ensure-Docker {
    Write-Step "检查 Docker"

    if (Test-Command "docker") {
        $info = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Docker 已安装且正在运行"
            return
        }
        # installed but not running
        Write-Warn "Docker 已安装但 daemon 未运行，尝试启动 Docker Desktop..."
        $dd = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        if (Test-Path $dd) {
            Start-Process $dd
            Write-Host "  等待 Docker Desktop 启动 (最长120s)..." -NoNewline
            $elapsed = 0
            while ($elapsed -lt 120) {
                Start-Sleep 5; $elapsed += 5
                Write-Host "." -NoNewline
                docker info 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { Write-Host ""; Write-OK "Docker Desktop 已启动"; return }
            }
            Write-Host ""
            throw "Docker Desktop 启动超时"
        }
        throw "Docker Desktop 未运行且无法自动启动"
    }

    # Not installed
    Write-Warn "未检测到 Docker，尝试通过 winget 安装..."
    if (-not (Test-Command "winget")) {
        throw "未找到 winget。请手动安装 Docker Desktop: https://www.docker.com/products/docker-desktop/"
    }
    winget install --id Docker.DockerDesktop -e --accept-source-agreements --accept-package-agreements *>> $LogFile
    Write-Host ""
    Write-OK "Docker Desktop 安装完成"
    Write-Warn "请完成以下步骤后重新运行:"
    Write-Host "  1. 从开始菜单启动 Docker Desktop" -ForegroundColor Cyan
    Write-Host "  2. 等待托盘图标变绿（首次可能需要几分钟）" -ForegroundColor Cyan
    Write-Host "  3. 重新双击 deploy.bat" -ForegroundColor Cyan
    exit 0
}

# ══════════════════════════════════════════════════════════════════════
#  2. Python
# ══════════════════════════════════════════════════════════════════════
$Script:PythonCmd = ""

function Ensure-Python {
    Write-Step "检查 Python"

    foreach ($cmd in @("python", "python3", "py")) {
        if (Test-Command $cmd) {
            $ver = & $cmd --version 2>&1
            if ($ver -match "(\d+)\.(\d+)") {
                $major = [int]$Matches[1]; $minor = [int]$Matches[2]
                if ($major -ge 3 -and $minor -ge 9) {
                    $Script:PythonCmd = $cmd
                    Write-OK "Python 已就绪: $ver ($cmd)"
                    return
                }
                Write-Warn "$cmd 版本 $ver 太低 (需要 >= 3.9)"
            }
        }
    }

    Write-Warn "未检测到 Python >= 3.9，尝试安装..."
    if (-not (Test-Command "winget")) {
        throw "请手动安装 Python >= 3.9: https://www.python.org/downloads/"
    }
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements *>> $LogFile
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    foreach ($cmd in @("python", "python3", "py")) {
        if (Test-Command $cmd) { $Script:PythonCmd = $cmd; Write-OK "Python 安装完成 ($cmd)"; return }
    }
    Write-Warn "Python 安装完成但需要重启终端。请关闭窗口后重新运行 deploy.bat"
    exit 0
}

# ══════════════════════════════════════════════════════════════════════
#  3. Docker containers
# ══════════════════════════════════════════════════════════════════════
function Start-Containers {
    Write-Step "启动 MySQL + Redis 容器"

    Invoke-Logged "docker compose up" { docker compose up -d }
    Write-OK "容器已启动"

    # Wait MySQL
    Write-Host "  等待 MySQL 就绪 " -NoNewline
    $elapsed = 0
    while ($elapsed -lt 90) {
        $r = docker exec rag-customer-service-mysql mysqladmin ping -uroot -prootpass --silent 2>&1
        if ($LASTEXITCODE -eq 0) { Write-Host ""; Write-OK "MySQL 就绪 (${elapsed}s)"; break }
        Write-Host "." -NoNewline; Start-Sleep 3; $elapsed += 3
    }
    if ($elapsed -ge 90) { throw "MySQL 启动超时 (90s)" }

    # Wait Redis
    Write-Host "  等待 Redis 就绪 " -NoNewline
    $elapsed = 0
    while ($elapsed -lt 30) {
        $r = docker exec rag-customer-service-redis redis-cli ping 2>&1
        if ($r -match "PONG") { Write-Host ""; Write-OK "Redis 就绪 (${elapsed}s)"; break }
        Write-Host "." -NoNewline; Start-Sleep 2; $elapsed += 2
    }
    if ($elapsed -ge 30) { throw "Redis 启动超时 (30s)" }
}

# ══════════════════════════════════════════════════════════════════════
#  4. Python venv + deps
# ══════════════════════════════════════════════════════════════════════
function Setup-PythonEnv {
    Write-Step "配置 Python 环境"

    $py = if ($Script:PythonCmd) { $Script:PythonCmd } else { "python" }
    $venv = Join-Path $ProjectDir ".venv"

    if (-not (Test-Path $venv)) {
        Write-Host "  创建虚拟环境..."
        & $py -m venv $venv *>> $LogFile
        if ($LASTEXITCODE -ne 0) { throw "创建虚拟环境失败" }
    }

    # Activate
    $activateScript = Join-Path $venv "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        & $activateScript
    } else {
        throw "虚拟环境激活脚本未找到: $activateScript"
    }
    Write-OK "虚拟环境已激活"

    # Upgrade pip
    python -m pip install --upgrade pip *>> $LogFile

    # Install deps
    Write-Host "  安装项目依赖（首次可能需要几分钟）..."
    python -m pip install -r (Join-Path $ProjectDir "requirements.txt") *>> $LogFile
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "依赖安装失败，尝试使用清华镜像..."
        python -m pip install -r (Join-Path $ProjectDir "requirements.txt") -i https://pypi.tuna.tsinghua.edu.cn/simple *>> $LogFile
        if ($LASTEXITCODE -ne 0) { throw "依赖安装失败，请查看 $LogFile" }
    }
    Write-OK "依赖安装完成"
}

# ══════════════════════════════════════════════════════════════════════
#  5. Database init
# ══════════════════════════════════════════════════════════════════════
function Init-Database {
    Write-Step "初始化数据库"

    python -c "
from sqlalchemy import create_engine, text
from app.config import MYSQL_URL
engine = create_engine(MYSQL_URL)
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
" *>> $LogFile
    if ($LASTEXITCODE -ne 0) { throw "无法连接 MySQL，请确认容器正在运行" }

    python -m app.scripts.init_db *>> $LogFile
    if ($LASTEXITCODE -ne 0) { throw "数据库初始化失败" }
    Write-OK "数据库 schema + demo 数据就绪"
}

# ══════════════════════════════════════════════════════════════════════
#  6. Start app
# ══════════════════════════════════════════════════════════════════════
$Script:AppPort = if ($env:APP_PORT) { $env:APP_PORT } else { "8000" }
$Script:AppHost = if ($env:APP_HOST) { $env:APP_HOST } else { "0.0.0.0" }

function Start-App {
    Write-Step "启动应用"

    $pidFile = Join-Path $ProjectDir "app.pid"

    # Kill old process
    if (Test-Path $pidFile) {
        $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($oldPid) {
            $proc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
            if ($proc) { $proc | Stop-Process -Force; Start-Sleep 2 }
        }
        Remove-Item $pidFile -Force
    }

    # Check port
    $portInUse = Get-NetTCPConnection -LocalPort $Script:AppPort -ErrorAction SilentlyContinue
    if ($portInUse) {
        throw "端口 $($Script:AppPort) 已被占用。设置 APP_PORT 环境变量使用其他端口"
    }

    Write-OK "启动 FastAPI ($($Script:AppHost):$($Script:AppPort))"
    $outLog = Join-Path $ProjectDir "uvicorn.out.log"
    $errLog = Join-Path $ProjectDir "uvicorn.err.log"

    $proc = Start-Process python -ArgumentList "-m","uvicorn","app.main:app","--host",$Script:AppHost,"--port",$Script:AppPort -PassThru -NoNewWindow -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    Set-Content -Path $pidFile -Value $proc.Id

    # Health check
    Write-Host "  健康检查 " -NoNewline
    $elapsed = 0
    while ($elapsed -lt 30) {
        Start-Sleep 2; $elapsed += 2
        Write-Host "." -NoNewline
        try {
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$($Script:AppPort)/health" -TimeoutSec 2 -ErrorAction Stop
            if ($resp.status -eq "ok") {
                Write-Host ""
                Write-OK "应用已启动 (PID: $($proc.Id))"
                return
            }
        } catch {}
    }
    Write-Host ""
    Write-Fail "健康检查超时，查看错误日志:"
    Get-Content $errLog -Tail 15 | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
    throw "应用启动失败"
}

# ══════════════════════════════════════════════════════════════════════
#  7. Stop
# ══════════════════════════════════════════════════════════════════════
function Stop-App {
    Write-Step "停止应用"
    $pidFile = Join-Path $ProjectDir "app.pid"
    if (Test-Path $pidFile) {
        $pid = Get-Content $pidFile
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) { $proc | Stop-Process -Force; Write-OK "应用已停止 (PID: $pid)" }
        else { Write-Warn "进程 $pid 已不存在" }
        Remove-Item $pidFile -Force
    } else { Write-Warn "应用未运行" }
}

function Stop-All {
    Stop-App
    Write-Step "停止 Docker 容器"
    docker compose down *>> $LogFile
    Write-OK "所有服务已停止"
}

# ══════════════════════════════════════════════════════════════════════
#  8. Status
# ══════════════════════════════════════════════════════════════════════
function Show-Status {
    Write-Host "`n===== 服务状态 =====" -ForegroundColor White

    Write-Host "`nDocker 容器:" -ForegroundColor Cyan
    docker compose ps 2>&1 | ForEach-Object { Write-Host "  $_" }

    Write-Host "`n应用进程:" -ForegroundColor Cyan
    $pidFile = Join-Path $ProjectDir "app.pid"
    if (Test-Path $pidFile) {
        $pid = Get-Content $pidFile
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) { Write-OK "运行中 (PID: $pid)" } else { Write-Fail "PID 文件存在但进程已退出" }
    } else { Write-Warn "未运行" }

    Write-Host "`n健康检查:" -ForegroundColor Cyan
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$($Script:AppPort)/health" -TimeoutSec 3
        Write-OK "http://127.0.0.1:$($Script:AppPort)/health → $($resp | ConvertTo-Json -Compress)"
    } catch { Write-Fail "http://127.0.0.1:$($Script:AppPort)/health 不可达" }
}

# ══════════════════════════════════════════════════════════════════════
#  Banner
# ══════════════════════════════════════════════════════════════════════
function Show-Banner {
    Write-Host ""
    Write-Host "  ════════════════════════════════════════" -ForegroundColor Green
    Write-Host "    部署完成！" -ForegroundColor Green
    Write-Host "  ════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "  应用地址:  " -NoNewline; Write-Host "http://127.0.0.1:$($Script:AppPort)" -ForegroundColor Cyan
    Write-Host "  API 文档:  " -NoNewline; Write-Host "http://127.0.0.1:$($Script:AppPort)/docs" -ForegroundColor Cyan
    Write-Host "  健康检查:  " -NoNewline; Write-Host "http://127.0.0.1:$($Script:AppPort)/health" -ForegroundColor Cyan
    Write-Host "  查看状态:  " -NoNewline; Write-Host "deploy.bat status" -ForegroundColor Cyan
    Write-Host "  停止服务:  " -NoNewline; Write-Host "deploy.bat stop-all" -ForegroundColor Cyan
    Write-Host ""
}

# ══════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════
Add-Content -Path $LogFile -Value "===== deploy.ps1 $(Get-Date) command=$Command ====="

# Load .env if exists
$envFile = Join-Path $ProjectDir ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
        }
    }
}

try {
    switch ($Command) {
        "deploy" {
            Write-Host "`n  RAG Customer Service — 一键部署`n" -ForegroundColor White
            Ensure-Docker
            Ensure-Python
            Start-Containers
            Setup-PythonEnv
            Init-Database
            Start-App
            Show-Banner
        }
        "start" {
            Ensure-Python
            Setup-PythonEnv
            Start-App
            Write-OK "应用已启动: http://127.0.0.1:$($Script:AppPort)"
        }
        "stop"     { Stop-App }
        "stop-all" { Stop-All }
        "restart"  { Ensure-Python; Stop-App; Setup-PythonEnv; Start-App }
        "status"   { Show-Status }
        "logs"     {
            $out = Join-Path $ProjectDir "uvicorn.out.log"
            $err = Join-Path $ProjectDir "uvicorn.err.log"
            Get-Content $out, $err -Tail 50 -Wait
        }
        "init-db"  { Ensure-Python; Setup-PythonEnv; Init-Database }
        "help" {
            Write-Host @"

  RAG Customer Service 部署脚本

  用法: deploy.bat [命令]

  命令:
    deploy      全量部署 [默认] — 自动安装一切并启动
    start       仅启动应用（跳过安装）
    stop        停止应用
    stop-all    停止应用 + Docker 容器
    restart     重启应用
    status      查看运行状态
    logs        实时日志
    init-db     仅初始化数据库

  环境变量:
    APP_PORT=8000       应用端口
    DEEPSEEK_API_KEY    DeepSeek API Key

  示例:
    deploy.bat                  一键全量部署
    deploy.bat status           查看状态
    deploy.bat stop-all         停掉一切

"@
        }
    }
} catch {
    Write-Host ""
    Write-Fail "$_"
    Write-Host "  详细日志: $LogFile" -ForegroundColor Yellow
    exit 1
}
