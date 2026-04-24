@echo off
title K-Reservation Bot
cd /d "%~dp0"

echo.
echo  ====================================
echo   K-Reservation Bot  ^|  Server Start
echo  ====================================
echo.

:: Python 확인 (python -> py 순서로 시도)
set PYTHON=
python --version >nul 2>&1
if not errorlevel 1 set PYTHON=python

if "%PYTHON%"=="" (
    py --version >nul 2>&1
    if not errorlevel 1 set PYTHON=py
)

if "%PYTHON%"=="" (
    echo  [ERROR] Python not found.
    echo  Python 3.x 를 설치하고 PATH 에 등록해 주세요.
    echo  https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  Python : %PYTHON%
echo.

:: flask 설치 확인
%PYTHON% -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo  Installing packages from requirements.txt ...
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo  [ERROR] pip install failed.
        pause
        exit /b 1
    )
)

:: playwright 설치 확인
%PYTHON% -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo  Installing playwright ...
    %PYTHON% -m pip install playwright
    %PYTHON% -m playwright install chromium
    if errorlevel 1 (
        echo  [ERROR] playwright install failed.
        pause
        exit /b 1
    )
)

echo.
echo  Server  :  http://localhost:5000
echo  Stop    :  Ctrl+C  or  close this window
echo  ----------------------------------------
echo.

:: 브라우저 자동 오픈 (2초 후)
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

%PYTHON% app.py

echo.
echo  Server stopped.
pause
