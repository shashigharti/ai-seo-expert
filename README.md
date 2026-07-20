# AISeo Expert

AISeo Expert is an AI-powered SEO analysis and automated-fixing platform. Point it at a GitHub repository and it audits the site's source for SEO issues - crawlability problems, missing metadata, thin or poorly structured content, accessibility gaps, and performance bottlenecks - then, for the issues you approve, opens a pull request on that same repository with the fix already written.

Every finding comes with the evidence behind it, a plain-language explanation of why it matters, a recommended fix, and links to authoritative references (Google Search Central, W3C, MDN, schema.org, OWASP). Nothing is a black box: token usage, model choice, and estimated cost are shown live as each agent runs, and any agent's reasoning trace can be expanded to see exactly how it reached its conclusion.

## Features

- **Full-repository SEO analysis** - crawlability, sitemaps, canonical tags and redirects; page titles, meta descriptions and social tags; heading structure, content depth and internal linking; accessibility (alt text, semantic HTML, contrast, keyboard navigation); and performance (Core Web Vitals, image weight, render-blocking resources).
- **Evidence-based findings** - every issue includes its severity, the affected file(s), why it matters, a confidence score, and citations to authoritative sources rather than an unsupported claim.
- **Automated fix PRs** - approve a finding and a fix agent proposes the code change and opens a real pull request on your repository, ready for normal review and merge.
- **Live multi-agent execution panel** - real-time status, duration, tokens consumed, model used, and a short reasoning summary for every agent as it runs, streamed over Server-Sent Events.
- **Cost and reasoning transparency** - per-agent and per-issue token counts, estimated API cost, and (for models run in thinking mode) the agent's own reasoning trace, expandable on demand.
- **Second-opinion review** - low-confidence findings are automatically re-checked by a dedicated reviewer agent before they ever reach the user.
- **Prompt-injection guardrails** - repository content is attacker-controlled input by nature, so fetched files are always delimited and screened before ever reaching a model prompt.
- **Evaluation-driven agent development** - a golden-repository eval suite scores planning and finding quality against real repositories, independent of the unit test suite.

## How It Works

1. You submit a GitHub repository URL. The backend reads it directly via the GitHub API - no upload step.
2. A **manager agent** decides which specialist capabilities are relevant and creates analysis tasks.
3. Specialized **worker agents** each examine the repository for one category of issue and return structured findings with evidence.
4. Findings are schema- and evidence-validated; anything low-confidence gets a second opinion from a **reviewer agent**.
5. Results are synthesized into a single SEO report, grouped by category and sorted by severity, and shown to you in real time as agents complete.
6. You review the findings and approve the ones you want fixed.
7. A **fix agent** groups the approved issues, proposes the code changes, and a **GitHub PR generator** opens a pull request on your repository.

```text
React Frontend
      |
      v
FastAPI API  --------------------------------  Server-Sent Events (live updates)
      |
      v
Workflow Orchestrator
      |
      v
SEO Manager Agent
      |
      +---------------+---------------+---------------+---------------+
      v               v               v               v               v
Technical SEO     Metadata        Content SEO     Accessibility    Performance
   Worker          Worker           Worker           Worker           Worker
      |
      v
Reviewer Agent (as needed)
      |
      v
Result Synthesizer  -->  Human Approval  -->  Fix Manager  -->  GitHub PR Generator
```

Agents run on Qwen Cloud (Alibaba Cloud's DashScope): tasks that need real reasoning run on a larger model with thinking mode enabled, while simpler, more mechanical checks run on a smaller, faster one.

## Tech Stack

**Frontend**
- React 18 + TypeScript
- Vite
- React Router
- Bootstrap 5 + Bootstrap Icons
- Server-Sent Events for real-time agent execution updates

**Backend**
- FastAPI (Python 3.12)
- Pydantic v2 / pydantic-settings
- PydanticAI (agent orchestration over an OpenAI-compatible client)
- SQLAlchemy (async) + Alembic migrations
- python-jose (JWT auth) + bcrypt (password hashing)
- PyGithub (GitHub API integration)
- httpx

**AI / Multi-Agent System**
- Qwen Cloud (DashScope) - qwen-plus and qwen-max models
- Manager, worker, reviewer, and fix agents composed via a central agent registry and model-policy service
- Prompt-injection guarding and token-efficient prompting applied to every agent call

**Data & Storage**
- PostgreSQL (asyncpg driver) for workflows, tasks, findings, approvals, and decisions
- Alibaba Cloud OSS (or local filesystem in dev) for reports, generated patches, and large logs

**DevOps / Infrastructure**
- Docker (multi-stage build: React build stage + FastAPI runtime stage)
- Docker Compose for local development and production
- GitHub Actions CI/CD - backend tests + frontend build on every push/PR, automated deploy to Alibaba Cloud ECS on push to `master`
- Alibaba Cloud (ECS, OSS, and optionally ApsaraDB RDS / ACK for a larger deployment)

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
