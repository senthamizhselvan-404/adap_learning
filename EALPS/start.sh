#!/bin/bash
set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   EALPS — Startup Script (Linux/Mac)    ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Check Ollama ──────────────────────────────────────
echo "▶ Checking Ollama..."
if ! command -v ollama &> /dev/null; then
  echo "  ❌ Ollama not found. Install from https://ollama.com"
  echo "     Then run: ollama pull gemma3:4b"
  echo ""
else
  echo "  ✓ Ollama found"
  echo "  ▶ Pulling gemma3:4b (skipped if already present)..."
  ollama pull gemma3:4b
fi

# ── Backend ───────────────────────────────────────────
echo ""
echo "▶ Setting up Python backend..."
cd backend

if [ ! -d "venv" ]; then
  echo "  Creating virtual environment..."
  python3 -m venv venv
fi

echo "  Installing dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

# Train ML model if not trained
if [ ! -f "ml_models/fnn_scorer.pkl" ]; then
  echo ""
  echo "▶ Training FNN Difficulty Scorer..."
  python ml_training/train_fnn.py
fi

# Seed database
echo ""
echo "▶ Seeding database..."
python seed_data.py

echo ""
echo "▶ Starting Flask backend on http://localhost:5000"
python run.py &
BACKEND_PID=$!
cd ..

# ── Frontend ──────────────────────────────────────────
echo ""
echo "▶ Setting up React frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
  echo "  Installing npm packages..."
  npm install
fi

echo "▶ Starting React frontend on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "════════════════════════════════════════════"
echo "  ✅ EALPS is running!"
echo ""
echo "  Frontend : http://localhost:5173"
echo "  Backend  : http://localhost:5000"
echo ""
echo "  Login: admin@ealps.dev / admin123"
echo "         learner@ealps.dev / learner123"
echo "════════════════════════════════════════════"
echo ""
echo "  Press Ctrl+C to stop all services"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
