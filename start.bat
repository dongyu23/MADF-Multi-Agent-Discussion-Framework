@echo off
echo ==================================================
echo      MADF - Multi-Agent Discussion Framework
echo ==================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+.
    pause
    exit /b
)

:: 2. Check Node
call npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 16+.
    pause
    exit /b
)

:: 3. Setup Virtual Environment
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    echo [INFO] Installing backend dependencies...
    call .venv\Scripts\activate
    pip install -r requirements.txt
) else (
    echo [INFO] Virtual environment found. Activating...
    call .venv\Scripts\activate
)

:: 4. Start Backend (in new window)
echo [INFO] Starting Backend Server...
start "MADF Backend" cmd /k "call .venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: 5. Setup Frontend
cd frontend
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    call npm install
)

:: 6. Start Frontend (in new window)
echo [INFO] Starting Frontend Server...
start "MADF Frontend" cmd /k "npm run dev"

echo.
echo [SUCCESS] MADF is starting!
echo Backend: http://localhost:8000/docs
echo Frontend: http://localhost:5173
echo.
echo Press any key to close this launcher (servers will keep running)...
pause >nul
