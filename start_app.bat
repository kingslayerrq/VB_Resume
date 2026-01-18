@echo off
setlocal

:: --- 1. DETECT PYTHON COMMAND ---
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :FOUND
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :FOUND
)

echo [ERROR] Python not found! 
echo Please install Python from python.org and check "Add to PATH".
pause
exit /b

:FOUND
echo [INFO] Using Python command: %PYTHON_CMD%

:: --- CHECK FOR CREDENTIALS (SOFT CHECK) ---
if exist "credentials.json" (
    echo [INFO] Google Credentials found. Cloud features CAN BE ENABLED.
) else (
    echo [INFO] No credentials found. Running in LOCAL MODE.
    echo (Gmail scanning and Drive upload will be skipped)
)

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