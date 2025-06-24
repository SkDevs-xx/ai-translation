@echo off
echo YouTube AI Translation - Building executable...
echo.

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

REM Build executable with icon
echo Building executable with custom icon...
pyinstaller --onefile ^
    --windowed ^
    --icon=icons/icons-128.png ^
    --name=youtube-ai-translation ^
    --add-data="icons;icons" ^
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