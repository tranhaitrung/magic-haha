@echo off
chcp 65001 >nul
title Build Installer - FB Scanner

cd /d "%~dp0"

echo ============================================
echo  Build FBScanner_Setup.exe
echo ============================================
echo.

REM --- Kiem tra da chay setup_env.bat chua ---
if not exist "python\python.exe" (
    echo [BUOC 1] Chua co Python embedded.
    echo         Dang chay setup_env.bat de tai Python + Chromium...
    echo         ^(can ket noi internet, mat khoang 10 phut^)
    echo.
    call setup_env.bat
    if errorlevel 1 (
        echo [LOI] setup_env.bat that bai.
        pause
        exit /b 1
    )
)

echo [OK] Python embedded san sang.
echo.

REM --- Kiem tra Inno Setup ---
set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if %ISCC%=="" (
    echo [LOI] Khong tim thay Inno Setup 6.
    echo.
    echo Vui long cai Inno Setup 6 tu:
    echo   https://jrsoftware.org/isdl.php
    echo.
    echo Sau khi cai xong, chay lai file nay.
    pause
    exit /b 1
)

echo [BUILD] Dang compile installer...
if not exist "dist" mkdir "dist"

%ISCC% "FBScanner.iss"
if errorlevel 1 (
    echo [LOI] Build that bai.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Hoan tat!
echo  File: dist\FBScanner_Setup.exe
echo.
echo  Gui file nay cho user, ho chi can:
echo  - Double-click
echo  - Next, Next, Finish
echo  - Xai ngay tu Desktop shortcut
echo ============================================
echo.
pause
