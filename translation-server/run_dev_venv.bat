@echo off
echo YouTube AI Translation - Development Mode (with venv)
echo.

REM Check if virtual environment exists
if exist "venv" (
    echo Virtual environment found. Activating...
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Creating new virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        echo Please ensure Python 3.8+ is installed and accessible
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install/update dependencies
echo.
echo Installing/updating dependencies from requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

REM Start the application
echo.
echo Dependencies installed successfully.
echo Starting application...
python youtube-ai-translation.py

if errorlevel 1 (
    echo.
    echo Application exited with error
    pause
)