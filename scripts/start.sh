#!/usr/bin/env bash
# Single-command local dev startup: Postgres (Docker) + backend (uvicorn) +
# frontend (vite), all reachable from the host via published/localhost
# ports. Deliberately does NOT run the backend inside Docker too - on this
# host the container-to-container bridge network drops traffic between
# compose services (confirmed with docker run --network ... + ping/nc, both
# 100% packet loss) even though Postgres's published port on localhost works
# fine. Running the backend on the host sidesteps that broken bridge
# entirely. See docker-compose.yml for the container-only path once that's
# fixed.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/.dev-logs"
mkdir -p "$LOG_DIR"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

stopping=0
cleanup() {
  [ "$stopping" -eq 1 ] && return
  stopping=1
  echo
  echo "==> Stopping..."
  kill 0
}
trap cleanup EXIT INT TERM

echo "==> Starting Postgres"
docker compose up -d postgres

echo "==> Waiting for Postgres to accept connections"
ready=0
for _ in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U aiseo >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "Postgres did not become ready in time." >&2
  exit 1
fi
echo "Postgres is ready."

if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "==> Creating backend/.env from .env.example - fill in QWEN_API_KEY / GITHUB_TOKEN for full functionality"
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

if [ ! -x "$BACKEND_DIR/.venv/bin/python" ]; then
  echo "==> Creating backend virtualenv"
  python3 -m venv "$BACKEND_DIR/.venv"
  (cd "$BACKEND_DIR" && .venv/bin/pip install -e ".[dev]")
fi

echo "==> Applying database migrations"
(cd "$BACKEND_DIR" && .venv/bin/python -m alembic upgrade head)

echo "==> Starting backend (uvicorn --reload) -> $BACKEND_LOG"
(cd "$BACKEND_DIR" && exec .venv/bin/uvicorn app.main:app --reload --port 8000) >"$BACKEND_LOG" 2>&1 &

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "==> Installing frontend dependencies"
  (cd "$FRONTEND_DIR" && npm install)
fi

echo "==> Starting frontend (vite dev server) -> $FRONTEND_LOG"
(cd "$FRONTEND_DIR" && exec npm run dev) >"$FRONTEND_LOG" 2>&1 &

cat <<EOF

Backend:  http://localhost:8000  (docs at /docs)
Frontend: http://localhost:5173
Logs:     tail -f "$BACKEND_LOG" "$FRONTEND_LOG"
Press Ctrl+C to stop everything.

EOF

wait
