@echo off
chcp 65001 >nul
title FB Scanner - Setup lan dau

cd /d "%~dp0"

echo ============================================
echo  FB Affiliate Scanner - Setup lan dau
echo  (Khong can cai Python truoc)
echo ============================================
echo.

REM --- Kiem tra neu da setup roi ---
if exist "python\python.exe" (
    echo [OK] Da co Python embedded, bo qua buoc tai.
    goto :install_deps
)

REM -------------------------------------------------------
REM [1/5] Tai Python embeddable
REM -------------------------------------------------------
echo [1/5] Dang tai Python 3.11 embeddable...

set PY_VER=3.11.9
set PY_ZIP=python-%PY_VER%-embed-amd64.zip
set PY_URL=https://www.python.org/ftp/python/%PY_VER%/%PY_ZIP%

powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%' -UseBasicParsing }"
if errorlevel 1 (
    echo [LOI] Khong tai duoc Python. Kiem tra ket noi mang.
    pause
    exit /b 1
)

echo [1/5] Giai nen Python...
powershell -Command "Expand-Archive -Path '%PY_ZIP%' -DestinationPath 'python' -Force"
del /f /q "%PY_ZIP%"

REM --- Bat import site trong python311._pth de pip hoat dong ---
powershell -Command "(Get-Content 'python\python311._pth') -replace '#import site','import site' | Set-Content 'python\python311._pth'"

REM -------------------------------------------------------
REM [2/5] Cai pip vao Python embedded
REM -------------------------------------------------------
echo [2/5] Cai pip...

REM Uu tien dung get-pip.py da bundle san, neu khong co thi tai ve
if exist "python\get-pip.py" (
    python\python.exe python\get-pip.py --quiet
) else (
    set GETPIP_URL=https://bootstrap.pypa.io/get-pip.py
    powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%GETPIP_URL%' -OutFile 'python\get-pip.py' -UseBasicParsing }"
    if errorlevel 1 (
        echo [LOI] Khong tai duoc get-pip.py. Kiem tra ket noi mang.
        pause
        exit /b 1
    )
    python\python.exe python\get-pip.py --quiet
)

if errorlevel 1 (
    echo [LOI] Cai pip that bai.
    pause
    exit /b 1
)

:install_deps
REM -------------------------------------------------------
REM [3/4] Cai thu vien
REM -------------------------------------------------------
echo [3/4] Cai dat thu vien (playwright, openpyxl...)...
python\python.exe -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [LOI] Cai thu vien that bai.
    pause
    exit /b 1
)

REM Cai playwright browser driver (khong can tai Chromium - dung Chrome co san)
python\python.exe -m playwright install-deps chromium >nul 2>&1

REM -------------------------------------------------------
REM [4/4] Tao thu muc du lieu
REM -------------------------------------------------------
echo [4/4] Tao thu muc du lieu...
if not exist "data\inbox"      mkdir "data\inbox"
if not exist "data\processing" mkdir "data\processing"
if not exist "data\output"     mkdir "data\output"
if not exist "data\archive"    mkdir "data\archive"
if not exist "data\error"      mkdir "data\error"
if not exist "logs"            mkdir "logs"

echo.
echo ============================================
echo  Setup hoan tat!
echo  LUU Y: Can cai Google Chrome de chay app.
echo  Lan sau chi can double-click launcher.bat
echo ============================================
echo.
pause
