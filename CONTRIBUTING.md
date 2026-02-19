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
npm run test
npm run test:watch      # Watch mode for development
npm run test:coverage   # Generate coverage report
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

The repo includes `docker-compose.local.yml` which starts Postgres 15 and Redis 7 with health checks.

**Start services:**

```bash
docker-compose -f docker-compose.local.yml up -d
```

**Check services:**

```bash
docker-compose -f docker-compose.local.yml ps
```

**Stop services:**

```bash
docker-compose -f docker-compose.local.yml down
```

**Cleanup (remove volumes):**

```bash
docker-compose -f docker-compose.local.yml down -v
```

### Manually with Docker commands

```bash
# Start Postgres
docker run -d \
  -e POSTGRES_DB=linkedwifi \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  --name linkedwifi-postgres \
  postgres:15

# Start Redis
docker run -d \
  -p 6379:6379 \
  --name linkedwifi-redis \
  redis:7
```

## Running Migrations & Seed Data

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

## Frontend Testing Setup

The repo uses **Jest** + **React Testing Library** for frontend unit and component tests.

### Writing Tests

Create test files in `frontend/__tests__/` or alongside components with `.test.tsx` or `.spec.tsx` extension:

```typescript
// frontend/__tests__/page.test.tsx
import { render, screen } from '@testing-library/react'
import Home from '@/app/page'

describe('Home page', () => {
  it('renders the landing page', () => {
    render(<Home />)
    expect(screen.getByText(/linkedwifi/i)).toBeInTheDocument()
  })
})
```

### Run tests locally:

```bash
cd frontend
npm run test          # Run all tests once
npm run test:watch   # Run in watch mode (re-run on file changes)
npm run test:coverage # Run and generate coverage report
```

Coverage reports are generated in `frontend/coverage/` and uploaded to Codecov on CI.

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

The repo uses **GitHub Actions** for automated testing, linting, and coverage checks across backend and frontend.

### What runs on every push/PR:

- **Backend tests:** pytest with DB + Redis services, PYTHONPATH set
- **Backend lint:** ruff check (E, F, I, B, UP rules)
- **Frontend tests:** Jest unit tests with coverage
- **Frontend lint:** ESLint (Next.js config)
- **Frontend build:** Next.js static build validation
- **Coverage reports:** XML + HTML generated for both backend and frontend
- **JUnit XML reports:** Structured test results for visibility
- **Codecov integration:** Coverage trend tracking and PR delta comments

### Parallel Jobs for Speed

- `backend-tests` — Runs backend tests, linting, and coverage in parallel
- `frontend-tests` — Runs frontend tests and linting in parallel
- `frontend-build` — Builds the Next.js app (separate from tests)

These jobs run in parallel, so total CI time is minimized.

### Artifacts uploaded to GitHub Actions:

- `backend-coverage-xml` — Coverage in XML format (for Codecov)
- `backend-coverage-html` — Browsable coverage report
- `backend-junit` — Pytest results in JUnit format
- `backend-pytest-log` (on failure only) — Full pytest output for debugging
- `frontend-coverage-xml` — Frontend Jest coverage report
- `frontend-jest` — Frontend test results (if added)

**Artifact retention:** 7 days (auto-cleanup)

### PR Coverage Comments

When you open a PR, GitHub Actions will post a coverage delta comment showing:
- Overall coverage %
- Lines added/removed
- Green (≥80%) / Orange (≥60%) / Red (<60%) thresholds

## Docker & Container Setup

### Local Docker Image Builds

To build and test Docker images locally:

```bash
# Build backend image
docker build -t linkedwifi-backend:dev ./backend

# Build frontend image
docker build -t linkedwifi-frontend:dev ./frontend

# Run containers
docker run -p 8000:8000 -e DATABASE_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/linkedwifi linkedwifi-backend:dev
docker run -p 3000:3000 linkedwifi-frontend:dev
```

Ensure Postgres + Redis are running on your host (via docker-compose.local.yml).

### Docker Hub / GHCR Push (CI Only)

The CI workflow automatically builds and pushes Docker images on successful tests (main branch only).

To enable:

1. Create Docker Hub account (or use GitHub Container Registry)
2. Add these GitHub Actions Secrets to your repo:
   - `DOCKER_USERNAME` — your Docker Hub username
   - `DOCKER_PASSWORD` — your Docker Hub access token (or PAT)
3. Push to main → CI will build and push images to:
   - `yourusername/linkedwifi-backend:latest`
   - `yourusername/linkedwifi-backend:${COMMIT_SHA}`
   - `yourusername/linkedwifi-frontend:latest`
   - `yourusername/linkedwifi-frontend:${COMMIT_SHA}`

## Dependency Management

### Automated Dependency Updates (Dependabot)

The repo uses **Dependabot** for automated dependency updates:

- **Python** (`backend/requirements.txt`) — Weekly Monday updates
- **Node.js** (`frontend/package.json`) — Weekly Monday updates
- **GitHub Actions** (`.github/workflows/`) — Weekly Monday updates

Dependabot will:
- Create PRs with dependency updates
- Run CI on each PR
- Auto-merge passing patches (if configured) or request review for minor/major

**Enable auto-merge:** Go to repo → Settings → Pull Requests → Check "Allow auto-merge"

### Manual Updates

```bash
# Update Python dependencies
cd backend
pip install --upgrade pip
pip list --outdated
# Edit requirements.txt and run: pip install -r requirements.txt

# Update Node dependencies
cd frontend
npm outdated
npm update
```

## Security Scanning

The CI pipeline includes:

- **Ruff** linting (catches common bugs)
- **Python coverage** (low coverage = risky code)
- **Dependabot** (outdated dependencies)
- **GitHub Actions security advisories** (notified automatically)

For production deployments, consider:
- OWASP dependency checks (`safety`, `pip-audit`)
- Container scanning (Trivy, Snyk)
- SAST scanning (Codacy, SonarCloud)

## PR Coverage Comments

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
cd frontend && npm run lint && npm run test && npm run build

# Run pre-commit against all files
pre-commit run --all-files

# Format all Python code
ruff format backend

# Generate coverage report
cd backend && PYTHONPATH=. pytest --cov=linkedwifi_saas --cov-report=html
cd frontend && npm run test:coverage

# Start all services with Docker
docker-compose -f docker-compose.local.yml up -d

# Seed the database
cd backend && . .venv/bin/activate && python -m linkedwifi_saas.seed

# Build Docker images locally
docker build -t linkedwifi-backend:dev ./backend
docker build -t linkedwifi-frontend:dev ./frontend

# Clean up Docker
docker-compose -f docker-compose.local.yml down -v
docker system prune -a
```

## Questions or Issues?

If you encounter setup issues:

1. Check that Python 3.11+ and Node.js 20+ are installed
2. Ensure Postgres 15 and Redis 7 are running
3. Run `pre-commit install` again if hooks aren't triggering
4. Look at CI logs in GitHub Actions for environment-specific issues
5. Ask in a comment on your PR or open an issue

Happy coding! 🚀
