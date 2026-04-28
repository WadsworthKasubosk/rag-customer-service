@echo off
chcp 65001 >nul 2>&1
title RAG Customer Service - 无 Docker 部署
color 0A

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   RAG Customer Service 无 Docker 部署        ║
echo  ║   要求: 本地已有 MySQL                       ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"
echo  工作目录: %CD%
echo.

:: ── 0. 找 mysql.exe ──
set "MYSQL_CMD=mysql"
where mysql >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [!] mysql 不在 PATH 中，自动搜索...
    set "MYSQL_CMD="
    for %%d in (
        "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
        "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"
        "C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe"
        "C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin\mysql.exe"
        "D:\MySQL\bin\mysql.exe"
        "E:\MySQL\bin\mysql.exe"
        "C:\mysql\bin\mysql.exe"
        "D:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
    ) do (
        if exist %%d (
            set "MYSQL_CMD=%%~d"
            echo  [OK] 找到: %%~d
        )
    )
    if not defined MYSQL_CMD (
        echo.
        echo  [FAIL] 找不到 mysql.exe
        echo         请手动输入 mysql.exe 的完整路径:
        echo         例如: C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe
        echo.
        set /p "MYSQL_CMD=路径: "
        if not exist "!MYSQL_CMD!" (
            echo  [FAIL] 路径无效
            pause
            exit /b 1
        )
    )
)
echo.

:: ── 开启延迟变量 ──
setlocal enabledelayedexpansion

:: ── 1. 升级 pip 依赖 ──
echo ============================================
echo [1/4] 安装/升级 Python 依赖...
echo ============================================
pip install "sqlalchemy>=2.0.36" "pymysql>=1.1.1" "redis>=5.2.1" "fastapi==0.115.5" "uvicorn==0.32.1" "python-multipart==0.0.12" "python-docx==1.1.2" "pypdf>=5.1.0" "jinja2==3.1.4" "pydantic==2.10.3" "networkx>=3.2" "openai>=1.58.1" "langchain==0.3.7" "langchain-community==0.3.7" "langchain-openai==0.2.14" "langchain-huggingface==0.1.2" "sentence-transformers==3.3.1" -i https://pypi.tuna.tsinghua.edu.cn/simple
if !ERRORLEVEL! NEQ 0 (
    echo [FAIL] 依赖安装失败
    pause
    exit /b 1
)
echo [OK]   依赖安装完成
echo.

:: ── 2. MySQL 建库建用户 ──
echo ============================================
echo [2/4] 配置 MySQL...
echo ============================================
echo.
echo  请输入 MySQL root 密码（没有密码直接回车）:
set /p "ROOTPW=密码: "

if defined ROOTPW (
    "%MYSQL_CMD%" -u root -p%ROOTPW% -e "CREATE DATABASE IF NOT EXISTS rag_customer_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS 'rag_user'@'localhost' IDENTIFIED BY 'rag_pass'; GRANT ALL PRIVILEGES ON rag_customer_service.* TO 'rag_user'@'localhost'; FLUSH PRIVILEGES; SELECT 'MySQL OK' AS status;"
) else (
    "%MYSQL_CMD%" -u root -e "CREATE DATABASE IF NOT EXISTS rag_customer_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS 'rag_user'@'localhost' IDENTIFIED BY 'rag_pass'; GRANT ALL PRIVILEGES ON rag_customer_service.* TO 'rag_user'@'localhost'; FLUSH PRIVILEGES; SELECT 'MySQL OK' AS status;"
)

if !ERRORLEVEL! NEQ 0 (
    echo.
    echo [FAIL] MySQL 配置失败
    echo        可能原因: root 密码不对 / MySQL 服务未启动
    echo.
    echo  也可以手动执行（打开 MySQL 命令行后粘贴）:
    echo    CREATE DATABASE IF NOT EXISTS rag_customer_service CHARACTER SET utf8mb4;
    echo    CREATE USER IF NOT EXISTS 'rag_user'@'localhost' IDENTIFIED BY 'rag_pass';
    echo    GRANT ALL ON rag_customer_service.* TO 'rag_user'@'localhost';
    echo    FLUSH PRIVILEGES;
    echo.
    echo  手动建好后，按任意键继续下一步...
    pause
)
echo [OK]   MySQL 配置完成
echo.

:: ── 3. 初始化数据库表 + 演示数据 ──
echo ============================================
echo [3/4] 初始化数据库...
echo ============================================
python -m app.scripts.init_db
if !ERRORLEVEL! NEQ 0 (
    echo [FAIL] 数据库初始化失败
    echo        请确认 MySQL 中 rag_user 用户可以正常连接
    pause
    exit /b 1
)
echo [OK]   数据库初始化完成
echo.

:: ── 4. 启动应用 ──
echo ============================================
echo [4/4] 启动应用...
echo ============================================
echo.
echo  ════════════════════════════════════════
echo    部署完成！
echo  ════════════════════════════════════════
echo.
echo    浏览器打开: http://127.0.0.1:8000
echo    API 文档:   http://127.0.0.1:8000/docs
echo    按 Ctrl+C 停止服务
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo  服务已停止
pause
