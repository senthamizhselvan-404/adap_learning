@echo off
echo.
echo ╔══════════════════════════════════════════╗
echo ║   EALPS — Startup Script (Windows)      ║
echo ╚══════════════════════════════════════════╝
echo.

echo [1/6] Pulling Ollama model gemma3:4b...
ollama pull gemma3:4b

echo.
echo [2/6] Setting up Python backend...
cd backend

if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo.
echo [3/6] Training FNN model (if needed)...
if not exist ml_models\fnn_scorer.pkl (
    python ml_training\train_fnn.py
)

echo.
echo [4/6] Seeding database...
python seed_data.py

echo.
echo [5/6] Starting Flask backend...
start "EALPS Backend" cmd /k "call venv\Scripts\activate.bat && python run.py"
cd ..

echo.
echo [6/6] Starting React frontend...
cd frontend
if not exist node_modules (
    npm install
)
start "EALPS Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ════════════════════════════════════════════
echo   EALPS is starting!
echo.
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:5000
echo.
echo   Login: admin@ealps.dev / admin123
echo          learner@ealps.dev / learner123
echo ════════════════════════════════════════════
echo.
pause
