@echo off
echo ==========================================
echo The Oregon Trail - Multiplayer Server
echo ==========================================

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        echo Make sure Python is installed and in your PATH.
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Starting server...
echo Host URL:   http://localhost:5000/host
echo Player URL: http://localhost:5000/
echo Press Ctrl+C to stop
echo ==========================================
python server.py

echo.
echo Server stopped.
pause
