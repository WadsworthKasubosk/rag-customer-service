#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  RAG Customer Service — 傻瓜式一键部署
#  自动检测 + 下载安装所有依赖（Docker/Python/pip）
#  完整错误处理 + 重试 + 回滚
# ============================================================

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
LOG_FILE="$PROJECT_DIR/deploy.log"

# ---------- 颜色 & 日志 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()   { echo "[$(date '+%H:%M:%S')] $*" >> "$LOG_FILE"; }
info()  { echo -e "${GREEN}[✓]${NC} $*";  log "[INFO]  $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*";  log "[WARN]  $*"; }
fail()  { echo -e "${RED}[✗]${NC} $*";    log "[ERROR] $*"; }
die()   { fail "$*"; echo -e "${RED}    详细日志: $LOG_FILE${NC}"; exit 1; }
step()  { echo -e "\n${CYAN}${BOLD}▸ $*${NC}"; log "===== $* ====="; }

# ---------- 全局错误捕获 ----------
cleanup() {
    local code=$?
    if [[ $code -ne 0 ]]; then
        echo ""
        fail "部署过程出错 (exit code: $code)"
        echo -e "${YELLOW}    查看完整日志: $LOG_FILE${NC}"
        echo -e "${YELLOW}    最后 10 行日志:${NC}"
        tail -10 "$LOG_FILE" 2>/dev/null | sed 's/^/      /'
    fi
}
trap cleanup EXIT

# 写入日志头
echo "===== deploy.sh $(date) =====" >> "$LOG_FILE"

# ---------- 工具函数 ----------
is_windows() { [[ "$OSTYPE" == msys* || "$OSTYPE" == cygwin* || "$OSTYPE" == win* ]]; }

has_cmd() { command -v "$1" >/dev/null 2>&1; }

# 带重试的命令执行
retry() {
    local max_attempts=$1; shift
    local delay=$1; shift
    local desc=$1; shift
    local attempt=1
    while true; do
        if "$@" >> "$LOG_FILE" 2>&1; then
            return 0
        fi
        if [[ $attempt -ge $max_attempts ]]; then
            fail "$desc 失败 (已重试 $max_attempts 次)"
            return 1
        fi
        warn "$desc 失败，${delay}s 后重试 ($attempt/$max_attempts)..."
        sleep "$delay"
        attempt=$((attempt + 1))
    done
}

# 等待条件满足
wait_for() {
    local desc=$1; shift
    local timeout=$1; shift
    local interval=$1; shift
    local elapsed=0
    while ! "$@" >/dev/null 2>&1; do
        if [[ $elapsed -ge $timeout ]]; then
            die "$desc 超时 (${timeout}s)"
        fi
        sleep "$interval"
        elapsed=$((elapsed + interval))
    done
}

# ---------- 自动安装: winget 辅助 ----------
ensure_winget() {
    if has_cmd winget; then return 0; fi
    die "未找到 winget 包管理器。Windows 11 自带 winget，请确认 '应用安装程序' 已更新。
    手动安装: https://aka.ms/getwinget"
}

winget_install() {
    local pkg_id=$1
    local name=$2
    echo -e "  ${CYAN}→ 正在通过 winget 安装 $name ...${NC}"
    if winget install --id "$pkg_id" -e --accept-source-agreements --accept-package-agreements >> "$LOG_FILE" 2>&1; then
        info "$name 安装完成"
        return 0
    else
        fail "$name winget 安装失败"
        return 1
    fi
}

# ---------- 自动安装: Docker Desktop ----------
ensure_docker() {
    step "检查 Docker"

    if has_cmd docker; then
        # 检查 Docker daemon 是否运行
        if docker info >> "$LOG_FILE" 2>&1; then
            info "Docker 已安装且正在运行"
            return 0
        fi
        # Docker 已装但 daemon 没跑
        warn "Docker 已安装但 daemon 未运行"
        if is_windows; then
            info "尝试启动 Docker Desktop..."
            cmd.exe /c "start \"\" \"C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe\"" 2>/dev/null || true
            echo -e "  ${CYAN}等待 Docker Desktop 启动（最长 120s）...${NC}"
            wait_for "Docker Desktop 启动" 120 5 docker info
            info "Docker Desktop 已启动"
            return 0
        fi
        die "请手动启动 Docker daemon (sudo systemctl start docker)"
    fi

    # Docker 不存在，自动安装
    warn "未检测到 Docker"
    if is_windows; then
        ensure_winget
        step "安装 Docker Desktop"
        winget_install "Docker.DockerDesktop" "Docker Desktop" \
            || die "Docker Desktop 安装失败。手动安装: https://www.docker.com/products/docker-desktop/"

        echo -e "  ${YELLOW}Docker Desktop 安装完成，需要重启终端或电脑后 Docker 才可用。${NC}"
        echo -e "  ${YELLOW}请完成以下步骤:${NC}"
        echo -e "  ${CYAN}1. 关闭当前终端${NC}"
        echo -e "  ${CYAN}2. 启动 Docker Desktop（开始菜单搜索 Docker）${NC}"
        echo -e "  ${CYAN}3. 等待 Docker 启动完毕（托盘图标变绿）${NC}"
        echo -e "  ${CYAN}4. 重新打开终端，再次运行 bash deploy.sh${NC}"
        exit 0
    else
        # Linux
        step "安装 Docker (Linux)"
        if has_cmd apt-get; then
            sudo apt-get update >> "$LOG_FILE" 2>&1
            retry 3 5 "安装 Docker" sudo apt-get install -y docker.io docker-compose-plugin
        elif has_cmd dnf; then
            retry 3 5 "安装 Docker" sudo dnf install -y docker docker-compose-plugin
        elif has_cmd pacman; then
            retry 3 5 "安装 Docker" sudo pacman -Sy --noconfirm docker docker-compose
        else
            die "无法自动安装 Docker，请手动安装: https://docs.docker.com/engine/install/"
        fi
        sudo systemctl start docker >> "$LOG_FILE" 2>&1
        sudo systemctl enable docker >> "$LOG_FILE" 2>&1
        sudo usermod -aG docker "$USER" >> "$LOG_FILE" 2>&1 || true
        info "Docker 安装完成"
    fi
}

# ---------- 自动安装: Python ----------
ensure_python() {
    step "检查 Python"

    # 尝试多种命令名
    local py_cmd=""
    for cmd in python python3 py; do
        if has_cmd "$cmd"; then
            local ver
            ver=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1) || true
            if [[ -n "$ver" ]]; then
                local major minor
                major=$(echo "$ver" | cut -d. -f1)
                minor=$(echo "$ver" | cut -d. -f2)
                if [[ $major -ge 3 && $minor -ge 9 ]]; then
                    py_cmd="$cmd"
                    break
                fi
                warn "$cmd 版本 $ver 太低（需要 >= 3.9）"
            fi
        fi
    done

    if [[ -n "$py_cmd" ]]; then
        info "Python 已就绪: $($py_cmd --version 2>&1) [$py_cmd]"
        # 确保 PYTHON_CMD 全局可用
        PYTHON_CMD="$py_cmd"
        return 0
    fi

    # 需要安装
    warn "未检测到 Python >= 3.9"
    if is_windows; then
        ensure_winget
        step "安装 Python 3.12"
        winget_install "Python.Python.3.12" "Python 3.12" \
            || die "Python 安装失败。手动安装: https://www.python.org/downloads/"

        # winget 装完后 PATH 可能不更新，手动追加
        export PATH="/c/Users/$USERNAME/AppData/Local/Programs/Python/Python312:/c/Users/$USERNAME/AppData/Local/Programs/Python/Python312/Scripts:$PATH"

        # 验证
        if has_cmd python; then
            PYTHON_CMD="python"
        elif has_cmd python3; then
            PYTHON_CMD="python3"
        elif has_cmd py; then
            PYTHON_CMD="py"
        else
            echo -e "  ${YELLOW}Python 安装完成但需要重启终端使 PATH 生效。${NC}"
            echo -e "  ${CYAN}请关闭终端，重新打开后运行 bash deploy.sh${NC}"
            exit 0
        fi
        info "Python 安装完成: $($PYTHON_CMD --version 2>&1)"
    else
        step "安装 Python (Linux)"
        if has_cmd apt-get; then
            sudo apt-get update >> "$LOG_FILE" 2>&1
            retry 3 5 "安装 Python" sudo apt-get install -y python3 python3-venv python3-pip
        elif has_cmd dnf; then
            retry 3 5 "安装 Python" sudo dnf install -y python3 python3-pip
        elif has_cmd pacman; then
            retry 3 5 "安装 Python" sudo pacman -Sy --noconfirm python python-pip
        else
            die "无法自动安装 Python，请手动安装: https://www.python.org/downloads/"
        fi
        PYTHON_CMD="python3"
        info "Python 安装完成"
    fi
}

# ---------- 自动安装: curl ----------
ensure_curl() {
    if has_cmd curl; then return 0; fi
    warn "未检测到 curl"
    if is_windows; then
        # Windows 11 自带 curl，不太可能走到这
        die "未找到 curl。请安装 curl 或使用 Windows 11 自带版本"
    else
        if has_cmd apt-get; then
            sudo apt-get install -y curl >> "$LOG_FILE" 2>&1
        elif has_cmd dnf; then
            sudo dnf install -y curl >> "$LOG_FILE" 2>&1
        fi
    fi
}

# ---------- 环境变量 ----------
load_env() {
    if [[ -f "$PROJECT_DIR/.env" ]]; then
        info "加载 .env 文件"
        set -a; source "$PROJECT_DIR/.env"; set +a
    fi
}

# ---------- Docker Compose 兼容层 ----------
dkc() {
    if docker compose version >> "$LOG_FILE" 2>&1; then
        docker compose "$@"
    elif has_cmd docker-compose; then
        docker-compose "$@"
    else
        die "docker compose 不可用"
    fi
}

# ---------- 启动容器 ----------
start_containers() {
    step "启动 MySQL + Redis 容器"

    # 检查端口冲突
    for port in 3306 6379; do
        if has_cmd ss; then
            if ss -tlnp 2>/dev/null | grep -q ":$port "; then
                warn "端口 $port 已被占用，检查是否是已有容器..."
            fi
        elif has_cmd netstat; then
            if netstat -an 2>/dev/null | grep -q ":$port "; then
                warn "端口 $port 已被占用，检查是否是已有容器..."
            fi
        fi
    done

    dkc up -d >> "$LOG_FILE" 2>&1 || die "Docker 容器启动失败，请检查 docker-compose.yml"
    info "容器已启动"

    # 等待 MySQL
    echo -ne "  等待 MySQL 就绪 "
    local elapsed=0
    while ! docker exec rag-customer-service-mysql \
        mysqladmin ping -uroot -prootpass --silent >> "$LOG_FILE" 2>&1; do
        if [[ $elapsed -ge 90 ]]; then
            echo ""
            die "MySQL 启动超时 (90s)。查看日志: docker logs rag-customer-service-mysql"
        fi
        echo -n "."
        sleep 3
        elapsed=$((elapsed + 3))
    done
    echo ""
    info "MySQL 就绪 (${elapsed}s)"

    # 等待 Redis
    echo -ne "  等待 Redis 就绪 "
    elapsed=0
    while ! docker exec rag-customer-service-redis redis-cli ping 2>/dev/null | grep -q PONG; do
        if [[ $elapsed -ge 30 ]]; then
            echo ""
            die "Redis 启动超时 (30s)。查看日志: docker logs rag-customer-service-redis"
        fi
        echo -n "."
        sleep 2
        elapsed=$((elapsed + 2))
    done
    echo ""
    info "Redis 就绪 (${elapsed}s)"
}

# ---------- Python 虚拟环境 + 依赖 ----------
setup_python_env() {
    step "配置 Python 环境"

    local venv_dir="$PROJECT_DIR/.venv"
    local py="${PYTHON_CMD:-python}"

    # 创建 venv
    if [[ ! -d "$venv_dir" ]]; then
        info "创建虚拟环境..."
        "$py" -m venv "$venv_dir" >> "$LOG_FILE" 2>&1 \
            || die "创建虚拟环境失败。尝试: $py -m pip install virtualenv"
    fi

    # 激活 venv
    if [[ -f "$venv_dir/Scripts/activate" ]]; then
        source "$venv_dir/Scripts/activate"   # Windows (Git Bash / MSYS2)
    elif [[ -f "$venv_dir/bin/activate" ]]; then
        source "$venv_dir/bin/activate"       # Linux / macOS
    else
        die "虚拟环境激活脚本未找到"
    fi
    info "虚拟环境已激活"

    # 升级 pip
    python -m pip install --upgrade pip >> "$LOG_FILE" 2>&1 || warn "pip 升级失败，继续..."

    # 安装依赖
    info "安装项目依赖（首次可能需要几分钟）..."
    if ! python -m pip install -r "$PROJECT_DIR/requirements.txt" >> "$LOG_FILE" 2>&1; then
        fail "依赖安装失败"
        echo -e "  ${YELLOW}常见原因:${NC}"
        echo -e "  ${CYAN}  - 网络问题: 尝试设置镜像源 pip install -i https://pypi.tuna.tsinghua.edu.cn/simple${NC}"
        echo -e "  ${CYAN}  - C 扩展编译失败: 安装 Visual Studio Build Tools${NC}"
        echo -e "  ${CYAN}  - 详细错误: $LOG_FILE${NC}"
        exit 1
    fi
    info "依赖安装完成"
}

# ---------- 数据库初始化 ----------
init_database() {
    step "初始化数据库"

    # 先测试 MySQL 连接
    if ! python -c "
from sqlalchemy import create_engine, text
from app.config import MYSQL_URL
engine = create_engine(MYSQL_URL)
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
    print('ok')
" >> "$LOG_FILE" 2>&1; then
        die "无法连接 MySQL。请确认容器正在运行: docker ps"
    fi

    python -m app.scripts.init_db >> "$LOG_FILE" 2>&1 \
        || die "数据库初始化失败，查看 $LOG_FILE"
    info "数据库 schema + demo 数据就绪"
}

# ---------- 启动应用 ----------
start_app() {
    step "启动应用"

    local host="${APP_HOST:-0.0.0.0}"
    local port="${APP_PORT:-8000}"
    local workers="${APP_WORKERS:-1}"

    # 清理旧进程
    if [[ -f "$PROJECT_DIR/app.pid" ]]; then
        local old_pid
        old_pid=$(cat "$PROJECT_DIR/app.pid")
        if kill -0 "$old_pid" 2>/dev/null; then
            info "停止旧进程 (PID: $old_pid)"
            kill "$old_pid" 2>/dev/null || true
            sleep 2
            # 强杀
            kill -9 "$old_pid" 2>/dev/null || true
        fi
        rm -f "$PROJECT_DIR/app.pid"
    fi

    # 检查端口
    if has_cmd ss && ss -tlnp 2>/dev/null | grep -q ":$port "; then
        die "端口 $port 被占用。用 APP_PORT=其他端口 运行，或关闭占用进程"
    fi

    info "启动 FastAPI ($host:$port, workers=$workers)"
    nohup python -m uvicorn app.main:app \
        --host "$host" \
        --port "$port" \
        --workers "$workers" \
        > "$PROJECT_DIR/uvicorn.out.log" \
        2> "$PROJECT_DIR/uvicorn.err.log" &
    echo $! > "$PROJECT_DIR/app.pid"

    # 健康检查
    echo -ne "  健康检查 "
    local elapsed=0
    while ! curl -sf "http://127.0.0.1:$port/health" >> "$LOG_FILE" 2>&1; do
        if [[ $elapsed -ge 30 ]]; then
            echo ""
            fail "健康检查超时"
            echo -e "  ${YELLOW}查看错误日志:${NC}"
            tail -20 "$PROJECT_DIR/uvicorn.err.log" 2>/dev/null | sed 's/^/      /'
            exit 1
        fi
        echo -n "."
        sleep 2
        elapsed=$((elapsed + 2))
    done
    echo ""
    info "应用已启动 (PID: $(cat "$PROJECT_DIR/app.pid"))"
}

# ---------- 停止 ----------
stop_app() {
    step "停止应用"
    if [[ -f "$PROJECT_DIR/app.pid" ]]; then
        local pid
        pid=$(cat "$PROJECT_DIR/app.pid")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null; sleep 2
            kill -9 "$pid" 2>/dev/null || true
            info "应用已停止 (PID: $pid)"
        else
            warn "进程 $pid 已不存在"
        fi
        rm -f "$PROJECT_DIR/app.pid"
    else
        warn "应用未运行"
    fi
}

stop_all() {
    stop_app
    step "停止 Docker 容器"
    dkc down >> "$LOG_FILE" 2>&1
    info "所有服务已停止"
}

# ---------- 状态 ----------
status() {
    local port="${APP_PORT:-8000}"
    echo ""
    echo -e "${BOLD}===== 服务状态 =====${NC}"
    echo ""

    # Docker
    echo -e "${CYAN}Docker 容器:${NC}"
    if docker info >> "$LOG_FILE" 2>&1; then
        dkc ps 2>/dev/null || warn "无法获取容器状态"
    else
        fail "Docker 未运行"
    fi

    # App
    echo ""
    echo -e "${CYAN}应用进程:${NC}"
    if [[ -f "$PROJECT_DIR/app.pid" ]]; then
        local pid
        pid=$(cat "$PROJECT_DIR/app.pid")
        if kill -0 "$pid" 2>/dev/null; then
            info "运行中 (PID: $pid)"
        else
            fail "PID 文件存在但进程已退出"
        fi
    else
        warn "未运行"
    fi

    # Health
    echo ""
    echo -e "${CYAN}健康检查:${NC}"
    local resp
    if resp=$(curl -sf "http://127.0.0.1:$port/health" 2>/dev/null); then
        info "http://127.0.0.1:$port/health → $resp"
    else
        fail "http://127.0.0.1:$port/health 不可达"
    fi
    echo ""
}

# ---------- 日志 ----------
logs() {
    if [[ ! -f "$PROJECT_DIR/uvicorn.out.log" && ! -f "$PROJECT_DIR/uvicorn.err.log" ]]; then
        die "日志文件不存在，应用可能从未启动过"
    fi
    tail -f "$PROJECT_DIR/uvicorn.out.log" "$PROJECT_DIR/uvicorn.err.log"
}

# ---------- 完成横幅 ----------
print_banner() {
    local port="${APP_PORT:-8000}"
    echo ""
    echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  部署完成！${NC}"
    echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
    echo ""
    echo -e "  应用地址:  ${CYAN}http://127.0.0.1:$port${NC}"
    echo -e "  健康检查:  ${CYAN}http://127.0.0.1:$port/health${NC}"
    echo -e "  查看日志:  ${CYAN}bash deploy.sh logs${NC}"
    echo -e "  查看状态:  ${CYAN}bash deploy.sh status${NC}"
    echo -e "  停止服务:  ${CYAN}bash deploy.sh stop-all${NC}"
    echo ""
}

# ---------- 帮助 ----------
usage() {
    cat <<EOF

${BOLD}RAG Customer Service 部署脚本${NC}

用法: bash deploy.sh [命令]

命令:
  ${GREEN}deploy${NC}      全量部署 [默认] — 自动安装一切 → 启动所有服务
  ${GREEN}start${NC}       仅启动应用（跳过安装）
  ${GREEN}stop${NC}        停止应用
  ${GREEN}stop-all${NC}    停止应用 + Docker 容器
  ${GREEN}restart${NC}     重启应用
  ${GREEN}status${NC}      查看运行状态
  ${GREEN}logs${NC}        实时日志
  ${GREEN}init-db${NC}     仅初始化数据库

环境变量:
  APP_PORT=8000       应用端口
  APP_HOST=0.0.0.0    监听地址
  APP_WORKERS=1       worker 数量
  DEEPSEEK_API_KEY    DeepSeek API Key

示例:
  bash deploy.sh                          # 一键全量部署
  APP_PORT=9000 bash deploy.sh deploy     # 指定端口部署
  bash deploy.sh stop-all                 # 停掉一切

EOF
}

# ---------- 主入口 ----------
PYTHON_CMD=""

case "${1:-deploy}" in
    deploy)
        echo -e "\n${BOLD}RAG Customer Service — 一键部署${NC}\n"
        load_env
        ensure_curl
        ensure_docker
        ensure_python
        start_containers
        setup_python_env
        init_database
        start_app
        print_banner
        ;;
    start)
        load_env
        ensure_python
        setup_python_env
        start_app
        info "应用已启动: http://127.0.0.1:${APP_PORT:-8000}"
        ;;
    stop)
        stop_app
        ;;
    stop-all)
        stop_all
        ;;
    restart)
        load_env
        ensure_python
        stop_app
        setup_python_env
        start_app
        info "重启完成: http://127.0.0.1:${APP_PORT:-8000}"
        ;;
    status)
        load_env
        status
        ;;
    logs)
        logs
        ;;
    init-db)
        load_env
        ensure_python
        setup_python_env
        init_database
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        fail "未知命令: $1"
        usage
        exit 1
        ;;
esac
