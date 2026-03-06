#!/bin/bash
echo "=================================================="
echo "     MADF - Multi-Agent Discussion Framework"
echo "=================================================="
echo ""

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found. Please install Python 3.10+."
    exit 1
fi

# 2. Check Node
if ! command -v npm &> /dev/null; then
    echo "[ERROR] Node.js not found. Please install Node.js 16+."
    exit 1
fi

# 3. Setup Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv .venv
    echo "[INFO] Installing backend dependencies..."
    source .venv/bin/activate
    pip install -r requirements.txt
else
    echo "[INFO] Virtual environment found. Activating..."
    source .venv/bin/activate
fi

# 4. Start Backend
echo "[INFO] Starting Backend Server..."
gnome-terminal --title="MADF Backend" -- bash -c "source .venv/bin/activate; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; exec bash" || \
xterm -title "MADF Backend" -e "source .venv/bin/activate; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; exec bash" &

# 5. Setup Frontend
cd frontend
if [ ! -d "node_modules" ]; then
    echo "[INFO] Installing frontend dependencies..."
    npm install
fi

# 6. Start Frontend
echo "[INFO] Starting Frontend Server..."
gnome-terminal --title="MADF Frontend" -- bash -c "npm run dev; exec bash" || \
xterm -title "MADF Frontend" -e "npm run dev; exec bash" &

echo ""
echo "[SUCCESS] MADF is starting!"
echo "Backend: http://localhost:8000/docs"
echo "Frontend: http://localhost:5173"
echo ""
echo "Press any key to close this launcher..."
read -n 1 -s
