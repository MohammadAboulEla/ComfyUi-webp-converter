@echo off
REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python and try again.
    pause
    exit /b
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Install required libraries
if exist requirements.txt (
    echo Installing required libraries...
    pip install -r requirements.txt
) else (
    echo requirements.txt not found! Make sure it is in the same directory as this batch file.
    pause
    exit /b
)

REM Deactivate the virtual environment
deactivate

REM Pause to keep the terminal open
pause
