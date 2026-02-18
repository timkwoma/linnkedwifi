# Contributing to LINKEDWIFI

Welcome! This guide will help you set up the development environment, run tests locally, and understand the CI/CD pipeline.

## Environment Setup

### Backend (Python 3.11)

1. **Create a virtual environment:**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux (WSL)
```

2. **Install dependencies:**

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r ../requirements-dev.txt
```

3. **Set up environment variables:**

Create `backend/.env`:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/linkedwifi
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=dev-secret-key
JWT_ALGORITHM=HS256
```

### Frontend (Node.js 20+)

1. **Install dependencies:**

```bash
cd frontend
npm install
```

2. **Set up environment variables:**

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Pre-commit Hooks

The repo uses `pre-commit` to enforce linting and formatting automatically before commits.

### First-time setup:

```bash
pip install --user pre-commit
pre-commit install
```

### Run manually (before committing):

```bash
pre-commit run --all-files
```

This will:
- Check code with **ruff** (lint: E, F, I, B, UP rules)
- Format code with **ruff-format** (88-char line length)
- Fix trailing whitespace and EOF
- Validate YAML

## Running Tests Locally

### Backend Tests

Requires: Postgres 15 + Redis 7 running

**Quick test run:**

```bash
cd backend
export PYTHONPATH=.
pytest -q
```

**With coverage report:**

```bash
cd backend
export PYTHONPATH=.
pytest -q --cov=linkedwifi_saas --cov-report=html
# Open htmlcov/index.html in your browser
```

**Lint check:**

```bash
cd backend
ruff check linkedwifi_saas tests
```

### Frontend Tests & Build

```bash
cd frontend
npm run lint
npm run build
```

### Start dev servers:

**Backend (FastAPI):**

```bash
cd backend
source .venv/bin/activate
uvicorn linkedwifi_saas.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

**Frontend (Next.js):**

```bash
cd frontend
npm run dev
# Open http://localhost:3000
```

## Database + Redis Setup

### Using Docker (Recommended for local development)

Create `docker-compose.local.yml` in the repo root:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: linkedwifi
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - '5432:5432'
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - '6379:6379'

volumes:
  postgres_data:
```

**Start services:**

```bash
docker-compose -f docker-compose.local.yml up -d
```

**Stop services:**

```bash
docker-compose -f docker-compose.local.yml down
```

### Run Migrations & Seed Data

After DB is running:

```bash
cd backend
source .venv/bin/activate
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/linkedwifi
export REDIS_URL=redis://localhost:6379/0

# Run migrations
alembic upgrade head

# Seed sample data
python -m linkedwifi_saas.seed
```

## Development Workflow

1. **Create a branch:**

```bash
git checkout -b feature/your-feature-name
```

2. **Make changes** and test locally:

```bash
# Run tests
cd backend && PYTHONPATH=. pytest -q

# Check lint
ruff check linkedwifi_saas tests
```

3. **Commit with pre-commit:**

```bash
git add .
# pre-commit hooks run automatically
git commit -m "feat: your feature description"
```

4. **Push and open a PR:**

```bash
git push origin feature/your-feature-name
```

## CI/CD Pipeline

The repo uses **GitHub Actions** for automated testing, linting, and coverage checks.

### What runs on every push/PR:

- **Backend tests:** pytest with DB + Redis services, PYTHONPATH set
- **Backend lint:** ruff check (E, F, I, B, UP rules)
- **Frontend lint & build:** ESLint + Next.js build
- **Coverage reports:** XML + HTML generated
- **JUnit XML reports:** Test results for visibility

### Artifacts uploaded to GitHub Actions:

- `backend-coverage-xml` — Coverage in XML format (for integrations)
- `backend-coverage-html` — Browsable coverage report
- `backend-junit` — Test results in JUnit format
- `backend-pytest-log` (on failure) — Full pytest output for debugging

**Artifact retention:** 7 days (auto-cleanup)

### PR Coverage Comments

When you open a PR, GitHub Actions will post a coverage delta comment showing:
- Overall coverage %
- Lines added/removed
- Green (≥80%) / Orange (≥60%) / Red (<60%) thresholds

## Debugging CI Failures

If tests fail in CI but pass locally:

1. **Check the JUnit report:**
   - Go to the failed CI run → Artifacts
   - Download `backend-junit`
   - Open in your IDE or XML viewer for structured error info

2. **Check the pytest log (on failure):**
   - Download `backend-pytest-log` from Artifacts
   - Search for the actual error and stack trace

3. **Check the coverage report:**
   - Download `backend-coverage-html`
   - Open `index.html` to see coverage gaps

4. **Common issues:**
   - **Import errors:** Make sure `PYTHONPATH=.` is set when running from `backend/`
   - **DB not ready:** Services take ~5-10 seconds; CI has health checks + wait loop
   - **Linting failures:** Run `ruff check` and `ruff format` locally to match CI rules

## Code Standards

- **Python:** Python 3.11+, type hints preferred
- **Formatting:** `ruff format` (88-char line length)
- **Linting:** `ruff check` with rules: E, F, I, B, UP
- **Imports:** Auto-sorted by `ruff` (rule I)
- **TypeScript:** ESLint (Next.js config)
- **Test coverage:** Aim for ≥80% on new code

## Common Commands

```bash
# Full local test suite (from repo root)
cd backend && PYTHONPATH=. pytest -q && ruff check linkedwifi_saas tests
cd frontend && npm run lint && npm run build

# Run pre-commit against all files
pre-commit run --all-files

# Format all Python code
ruff format backend

# Generate coverage report
cd backend && PYTHONPATH=. pytest --cov=linkedwifi_saas --cov-report=html

# Start all services (Docker)
docker-compose -f docker-compose.local.yml up -d

# Seed the database
cd backend && python -m linkedwifi_saas.seed
```

## Questions or Issues?

If you encounter setup issues:

1. Check that Python 3.11+ and Node.js 20+ are installed
2. Ensure Postgres 15 and Redis 7 are running
3. Run `pre-commit install` again if hooks aren't triggering
4. Look at CI logs in GitHub Actions for environment-specific issues
5. Ask in a comment on your PR or open an issue

Happy coding! 🚀
