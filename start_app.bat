@echo off
TITLE AI Resume Factory Installer
echo ========================================================
echo      🏭 SETTING UP AI RESUME FACTORY FOR YOU...
echo ========================================================

:: 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo Please download Python 3.10+ from python.org and try again.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit
)

:: 2. Create Virtual Environment (if not exists)
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
)

:: 3. Activate venv
call venv\Scripts\activate

:: 4. Install Dependencies
if not exist "venv\Lib\site-packages\streamlit" (
    echo [2/4] Installing libraries - One time setup...
    pip install -r requirements.txt
    
    echo [3/4] Installing browser engines...
    playwright install
)

:: 5. Run the App
echo [4/4] Launching the Dashboard...
echo --------------------------------------------------------
echo NOTE: Do not close this black window while the app is running.
echo --------------------------------------------------------

streamlit run app.py

pause