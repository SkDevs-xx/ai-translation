@echo off
echo YouTube AI Translation - Building executable...
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install/update requirements
echo Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Build executable with icon and modules
echo Building executable with custom icon...
pyinstaller --onefile ^
    --icon=icons/icons-128.png ^
    --name=youtube-ai-translation ^
    --add-data="icons;icons" ^
    --collect-all=core ^
    --collect-all=server ^
    --collect-all=translation ^
    --collect-all=gui ^
    --collect-all=utils ^
    youtube-ai-translation.py

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo Executable location: dist/youtube-ai-translation.exe
echo.
pause