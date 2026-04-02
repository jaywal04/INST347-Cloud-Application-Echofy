@echo off
setlocal
if /i "%~1"=="backend" goto run_backend
if /i "%~1"=="frontend" goto run_frontend

set "DIR=%~dp0"
cd /d "%DIR%"
echo Starting Echofy: Backend :5000 and Frontend :3000 in separate windows.
start "Echofy Backend :5000" /D "%DIR%" cmd /k call "%~f0" backend
ping -n 2 127.0.0.1 >nul
start "Echofy Frontend :3000" /D "%DIR%" cmd /k call "%~f0" frontend
echo Done. You can close this window.
ping -n 3 127.0.0.1 >nul
exit /b 0

:run_backend
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%cd%\backend"
set "PY="
if exist "%cd%\.venv\Scripts\python.exe" set "PY=%cd%\.venv\Scripts\python.exe"
if defined PY (
  echo Using .venv for backend
  "%PY%" -c "import flask" 2>nul
  if errorlevel 1 (
    echo Flask is missing from .venv. Install dependencies:
    echo   "%PY%" -m pip install -r requirements.txt
    pause
    exit /b 1
  )
  echo Backend API at http://127.0.0.1:5000/
  echo Press Ctrl+C to stop.
  "%PY%" -m app.main
  exit /b %errorlevel%
)
echo Backend: no .venv found. Create one and install deps, or use system Python with Flask installed.
echo   python -m venv .venv
echo   .venv\Scripts\activate
echo   pip install -r requirements.txt
echo.
echo Trying system Python...
where python >nul 2>&1
if %errorlevel% equ 0 (
  python -c "import flask" 2>nul
  if errorlevel 1 (
    echo Flask not found. Run: pip install -r requirements.txt
    pause
    exit /b 1
  )
  echo Backend API at http://127.0.0.1:5000/
  echo Press Ctrl+C to stop.
  python -m app.main
  exit /b %errorlevel%
)
where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 -c "import flask" 2>nul
  if errorlevel 1 (
    echo Flask not found. Run: py -3 -m pip install -r requirements.txt
    pause
    exit /b 1
  )
  echo Backend API at http://127.0.0.1:5000/
  echo Press Ctrl+C to stop.
  py -3 -m app.main
  exit /b %errorlevel%
)
echo Python 3 was not found. Install from https://www.python.org/downloads/
pause
exit /b 1

:run_frontend
setlocal
cd /d "%~dp0"
set "PORT=3000"
set "PY="
if exist "%cd%\.venv\Scripts\python.exe" set "PY=%cd%\.venv\Scripts\python.exe"
echo Frontend at http://localhost:%PORT%/
echo Press Ctrl+C to stop.
if defined PY (
  "%PY%" -m http.server %PORT% --directory frontend\public
  exit /b %errorlevel%
)
where python >nul 2>&1
if %errorlevel% equ 0 (
  python -m http.server %PORT% --directory frontend\public
  exit /b %errorlevel%
)
where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 -m http.server %PORT% --directory frontend\public
  exit /b %errorlevel%
)
echo Python 3 was not found. Install from https://www.python.org/downloads/
pause
exit /b 1
