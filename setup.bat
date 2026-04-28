@echo off
title RAG Setup
cd /d "%~dp0"

echo.
echo ========================================
echo   RAG Customer Service Setup
echo   Dir: %CD%
echo ========================================
echo.

:: ── Find mysql.exe ──
set "MC=mysql"
where mysql >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] mysql not in PATH, searching...
    if exist "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" (
        set "MC=C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
        goto :found
    )
    if exist "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" (
        set "MC=C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"
        goto :found
    )
    if exist "C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe" (
        set "MC=C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe"
        goto :found
    )
    if exist "D:\MySQL\bin\mysql.exe" (
        set "MC=D:\MySQL\bin\mysql.exe"
        goto :found
    )
    if exist "E:\MySQL\bin\mysql.exe" (
        set "MC=E:\MySQL\bin\mysql.exe"
        goto :found
    )
    echo [FAIL] Cannot find mysql.exe
    echo        Please enter full path to mysql.exe:
    set /p MC=Path:
)
:found
echo [OK] mysql: %MC%
echo.

:: ── Step 1: pip install ──
echo ========================================
echo [1/4] Installing Python packages...
echo ========================================
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install "sqlalchemy>=2.0.36" -i https://pypi.tuna.tsinghua.edu.cn/simple
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] pip install failed
    pause
    exit /b 1
)
echo [OK] packages installed
echo.

:: ── Step 2: MySQL setup ──
echo ========================================
echo [2/4] MySQL setup...
echo ========================================
echo.
echo Enter MySQL root password (press Enter if none):
set /p ROOTPW=Password:

if "%ROOTPW%"=="" (
    "%MC%" -u root -e "CREATE DATABASE IF NOT EXISTS rag_customer_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    "%MC%" -u root -e "CREATE USER IF NOT EXISTS 'rag_user'@'localhost' IDENTIFIED BY 'rag_pass';"
    "%MC%" -u root -e "GRANT ALL PRIVILEGES ON rag_customer_service.* TO 'rag_user'@'localhost';"
    "%MC%" -u root -e "FLUSH PRIVILEGES;"
) else (
    "%MC%" -u root -p%ROOTPW% -e "CREATE DATABASE IF NOT EXISTS rag_customer_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    "%MC%" -u root -p%ROOTPW% -e "CREATE USER IF NOT EXISTS 'rag_user'@'localhost' IDENTIFIED BY 'rag_pass';"
    "%MC%" -u root -p%ROOTPW% -e "GRANT ALL PRIVILEGES ON rag_customer_service.* TO 'rag_user'@'localhost';"
    "%MC%" -u root -p%ROOTPW% -e "FLUSH PRIVILEGES;"
)

if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] MySQL setup failed
    echo        If you can setup manually, press any key to continue
    pause
)
echo [OK] MySQL ready
echo.

:: ── Step 3: Init database ──
echo ========================================
echo [3/4] Init database tables...
echo ========================================
python -m app.scripts.init_db
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Database init failed
    pause
    exit /b 1
)
echo [OK] Database ready
echo.

:: ── Step 4: Start app ──
echo ========================================
echo [4/4] Starting app...
echo ========================================
echo.
echo   Open browser: http://127.0.0.1:8000
echo   API docs:     http://127.0.0.1:8000/docs
echo   Press Ctrl+C to stop
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
