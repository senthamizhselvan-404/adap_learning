# ⬡ EALPS — Effort-Aware Adaptive Learning Pathway System

> Full-stack AI platform implementing the HLD v1.0 specification.
> FNN difficulty scoring · Ollama gemma3:4b · Adaptive pathway engine · Market decay detection

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python Flask + SQLAlchemy + JWT |
| Database | SQLite (dev) → PostgreSQL-compatible |
| ML Model | scikit-learn FNN (MLPRegressor 64→32→16) |
| LLM | Ollama gemma3:4b (local, private) |
| Frontend | React + Vite + Tailwind CSS + Recharts |
| Auth | JWT (access 15min + refresh 7d) + bcrypt |

---

## Prerequisites

- **Python 3.10+** — `python --version`
- **Node.js 18+** — `node --version`
- **Ollama** — https://ollama.com (download and install)

---

## One-Command Start

### Linux / Mac
```bash
chmod +x start.sh
./start.sh
```

### Windows
```
Double-click start.bat
```

This will:
1. Pull `gemma3:4b` via Ollama (first time ~2.5GB download)
2. Create Python virtualenv and install deps
3. **Train the FNN model** (synthetic data, ~30 seconds)
4. Seed 44 skills + admin/demo accounts + 6 months market data
5. Start Flask on `:5000` and React on `:5173`

---

## Manual Setup (Step by Step)

### Step 1 — Ollama
```bash
# Install Ollama from https://ollama.com, then:
ollama serve          # start Ollama server
ollama pull gemma3:4b  # pull the model (~2.5GB)
```

### Step 2 — Train the ML Model
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

python ml_training/train_fnn.py
# Output: ml_models/fnn_scorer.pkl
# Expected: MAE < 0.05, R² > 0.90
```

### Step 3 — Seed Database
```bash
python seed_data.py
# Creates: ealps.db with 44 skills, admin + demo accounts, market data
```

### Step 4 — Start Backend
```bash
python run.py
# Running on http://localhost:5000
```

### Step 5 — Start Frontend
```bash
cd ../frontend
npm install
npm run dev
# Running on http://localhost:5173
```

---

## Login Credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@ealps.dev | admin123 |
| Learner | learner@ealps.dev | learner123 |

---

## ML Architecture

### FNN Difficulty Scorer
```
Input:  [bloom_level, prerequisite_count, abstraction_level, avg_hours_to_learn]
Hidden: [64] → [32] → [16]  (ReLU activation)
Output: difficulty_score ∈ [0.0, 1.0]
Training: 3000+ synthetic samples from curated skill profiles
```

**Training data source**: 35 real skill profiles (HTML → Quantum Computing) with
known difficulty ground truth, augmented with Gaussian noise to 3000+ samples.

If model is not trained, the system falls back to a calibrated weighted heuristic
(same features, deterministic formula) — so the app works even without training.

### Decay Detector
- `decay_flag = True` when demand_index declines >15% over 3 consecutive months
- `emerging_flag = True` when growth_rate >25% MoM for 2 consecutive periods
- Runs automatically after every market data refresh

### Ollama Integration (gemma3:4b)
- **Skill extraction**: parses raw curriculum text → structured skill list
- **Pathway explanation**: generates human-readable rationale for skill sequence
- **Gap analysis**: produces 3 curriculum recommendations for admin

The app functions fully without Ollama running — Ollama calls return a warning
message instead of crashing.

---

## API Reference

```
POST /api/v1/auth/register         Register new learner
POST /api/v1/auth/login            Login → JWT tokens
GET  /api/v1/learners/me           Get profile
PUT  /api/v1/learners/me/skills    Update known skills + effort capacity
POST /api/v1/pathways/generate     Generate personalised pathway (FNN + Ollama)
GET  /api/v1/pathways/             List all pathways
GET  /api/v1/pathways/{id}         Get pathway with full skill sequence
PUT  /api/v1/pathways/{id}/progress Log effort hours + auto-unlock next skill
POST /api/v1/pathways/{id}/recalibrate Adaptive recalibration
GET  /api/v1/skills/               List skills with market data
GET  /api/v1/skills/{id}/market    Skill market time series
GET  /api/v1/admin/curriculum/health Decay/emergence report
GET  /api/v1/admin/curriculum/analysis Ollama narrative analysis
POST /api/v1/admin/market/refresh  Re-simulate + run decay detection
POST /api/v1/curriculum/           Upload + extract skills from text
```

---

## VSCode Workspace Tips

1. Install **Python** + **Pylance** extensions
2. Select `backend/venv` as your Python interpreter
3. Install **ESLint** + **Prettier** for the frontend
4. Run `Flask` debug config with `run.py` as entry point

---

## Production Upgrade Path (Phase 2)

- Swap SQLite → PostgreSQL (just change `DATABASE_URL` env var)
- Add Redis for JWT session store + API caching
- Add Celery + Airflow for scheduled ETL (real LinkedIn/O*NET APIs)
- Add SHAP explainability to FNN model
- Add real-time prerequisite graph via CourseSkill edges
- Deploy on AWS (EC2 + RDS + CloudFront) per HLD §3.4
