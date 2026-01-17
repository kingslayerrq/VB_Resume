@echo off
setlocal

:: --- 1. DETECT PYTHON COMMAND ---
:: Check for standard 'python'
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :FOUND
)

:: Check for 'py' (Python Launcher)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :FOUND
)

:: If neither found
echo [ERROR] Python not found! 
echo Please install Python from python.org and check "Add to PATH".
pause
exit /b

:FOUND
echo [INFO] Using Python command: %PYTHON_CMD%

:: --- 2. SETUP VIRTUAL ENV ---
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    "%PYTHON_CMD%" -m venv venv
)

:: --- 3. ACTIVATE & INSTALL ---
call venv\Scripts\activate

if not exist "venv\Lib\site-packages\streamlit" (
    echo [2/4] Installing dependencies...
    pip install -r requirements.txt
    
    echo [3/4] Installing browser engines...
    playwright install
)

:: --- 4. RUN APP ---
echo [4/4] Launching Dashboard...
echo ---------------------------------------------------
echo Keep this window open.
echo ---------------------------------------------------

streamlit run app.py

pause