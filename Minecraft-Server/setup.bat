@echo off
echo Installing Python and dependencies...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Downloading Python...
    start https://www.python.org/downloads/
    echo Please install Python and then run this script again.
    pause
    exit
)

REM Install dependencies
pip install -r requirements.txt

echo Setup complete! You can now run the script.
pause
