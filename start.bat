@echo off
title IntZam LMS - Startup
color 5F
echo.
echo ========================================
echo    IntZam Loan Management System
echo ========================================
echo.

:: ---- Locate Python ----
echo  Locating Python...
set PYTHON_CMD=

:: Try 'py' launcher first (most reliable on Windows)
py --version >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=py
    goto :python_found
)

:: Try 'python'
python --version >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=python
    goto :python_found
)

:: Try 'python3'
python3 --version >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=python3
    goto :python_found
)

echo  [ERROR] Python not found. Please install Python 3.10+ and add it to PATH.
pause
exit /b 1

:python_found
echo  Python found: %PYTHON_CMD%
echo.

:: ---- Setup Virtual Environment ----
set VENV_DIR=%~dp0venv
set VENV_PYTHON=%VENV_DIR%\Scripts\python.exe

:: Check if venv exists and is valid (points to a working Python)
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" --version >nul 2>&1
    if %errorlevel% == 0 (
        echo  Virtual environment OK.
        goto :venv_ready
    )
    echo  Virtual environment is broken. Recreating...
    rmdir /s /q "%VENV_DIR%"
) else (
    echo  Virtual environment not found. Creating...
)

%PYTHON_CMD% -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
echo  Virtual environment created.

:venv_ready
:: ---- Install / Update Dependencies ----
echo  Installing dependencies...
"%VENV_PYTHON%" -m pip install -q -r "%~dp0backend\requirements.txt"
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to install requirements.
    pause
    exit /b 1
)
echo  Dependencies ready.
echo.

:: ---- Django Backend (port 8000) ----
echo  [1/3] Starting Django Backend on port 8000...
start "IntZam - Backend (8000)" cmd /k "cd /d %~dp0backend && %VENV_PYTHON% manage.py runserver 0.0.0.0:8000"
timeout /t 3 /nobreak >nul

:: ---- Admin Frontend (port 5173) ----
echo  [2/3] Starting Admin Frontend on port 5173...
start "IntZam - Admin (5173)" cmd /k "cd /d %~dp0admin-frontend && npm run dev"
timeout /t 2 /nobreak >nul

:: ---- Client PWA (port 5174) ----
echo  [3/3] Starting Client PWA on port 5174...
start "IntZam - Client PWA (5174)" cmd /k "cd /d %~dp0client-pwa && npm run dev"

echo.
echo ========================================
echo  All services started!
echo.
echo  Backend:     http://localhost:8000
echo  Admin:       http://localhost:5173
echo  Client PWA:  http://localhost:5174
echo ========================================
echo.
echo  Close this window or press any key to
echo  open the Client PWA in your browser.
echo.
pause >nul
start http://localhost:5174
