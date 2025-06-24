@echo off
echo YouTube AI Translation - Development Mode (with venv)
echo.

REM Check if virtual environment exists
if exist "venv" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Running with system Python...
)

REM Start the application
echo Starting application...
python youtube-ai-translation.py

if errorlevel 1 (
    echo.
    echo Application exited with error
    pause
)