@echo off
chcp 65001 >nul 2>&1
title RAG Customer Service - 一键部署
color 0A

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   RAG Customer Service 一键部署 (Windows)    ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: ── CD to script directory ──
cd /d "%~dp0"

:: ── Check if Git Bash is available ──
where bash >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [i] 检测到 bash，使用 deploy.sh 部署...
    echo.
    bash deploy.sh %*
    goto :end
)

:: ── No bash, fall through to PowerShell bootstrap ──
echo  [i] 未检测到 bash，使用 PowerShell 部署...
echo.
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" %*

:end
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [!] 部署过程出错，请查看上方错误信息
)
echo.
pause
