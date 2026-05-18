@echo off
chcp 65001 >nul
title FB Affiliate Scanner

cd /d "%~dp0"

REM Neu chua setup, chay setup truoc
if not exist "python\python.exe" (
    echo ============================================
    echo  Lan dau su dung - Dang chay setup...
    echo  (Co the mat 5-10 phut, vui long cho)
    echo ============================================
    call setup_env.bat
    if errorlevel 1 (
        echo.
        echo [LOI] Setup that bai. Vui long lien he ho tro.
        pause
        exit /b 1
    )
)

echo Dang khoi dong FB Affiliate Scanner...
python\python.exe gui.py

if errorlevel 1 (
    echo.
    echo [LOI] Chuong trinh gap loi. Xem logs\scanner.log de biet them chi tiet.
    pause
)
