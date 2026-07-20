# Qwen SEO Agent Reference Pack

This repository reference pack defines the architecture, agent model, frontend design system, coding standards, and implementation roadmap for a production-ready Qwen-powered SEO multi-agent application.

---

## Local Development & Testing

Prerequisites: Python 3.12+, Node 20+, Docker.

### Quick start (single command)

```bash
./scripts/start.sh
```

Starts Postgres in Docker, then runs the backend (`uvicorn --reload`) and
frontend (`vite`) directly on the host - bootstrapping the backend
virtualenv and frontend `node_modules` on first run if they don't exist yet.
Backend: `http://localhost:8000`, frontend: `http://localhost:5173`, logs in
`.dev-logs/`. Ctrl+C stops everything.

The backend runs on the host rather than in its own container because, on
some hosts, Docker's container-to-container bridge network drops traffic
between compose services even though Postgres's published port on
`localhost` still works fine - running the backend on the host sidesteps
that. If your Docker networking is fine, `docker compose up -d --build`
(below) runs the whole stack in containers instead.

### Step by step

#### 1. Start Postgres

```bash
docker compose up -d postgres
```

#### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in QWEN_API_KEY / GITHUB_TOKEN if you have them

python -m alembic upgrade head   # apply migrations (main.py also auto-creates
                                 # tables on startup as a dev convenience)

python -m pytest -q             # run the test suite (170 tests, no real
                                 # Qwen key needed - model calls are stubbed)

uvicorn app.main:app --reload   # dev server at http://localhost:8000
```

#### 3. Frontend

```bash
cd frontend
npm install
npm run dev   # dev server at http://localhost:5173, proxies to the backend
```

#### 4. Evaluation suite

Exercises the real `SEOManagerAgent`/workers against golden repositories
(`backend/app/config/eval_cases.yaml`) and scores planning + finding
quality.

```bash
cd backend
python -m scripts.run_eval             # real Qwen Cloud calls - needs QWEN_API_KEY
python -m scripts.run_eval --sandbox   # no key needed - simulated output,
                                        # only proves the harness's wiring runs
```

#### 5. Full stack via Docker

```bash
docker compose up -d --build
```

Builds and runs backend + Postgres together (`docker-compose.yml`), serving
the built frontend from the backend at `http://localhost:8000`.

---

## Recommended Stack

- FastAPI
- React
- Bootstrap 5
- Pydantic
- PydanticAI
- Qwen Cloud
- PostgreSQL
- GitHub API
- Server-Sent Events
- Docker
- Alibaba Cloud
