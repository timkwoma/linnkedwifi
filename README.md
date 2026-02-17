# LINKEDWIFI

Production-style local development stack for a multi-tenant ISP SaaS:

- Backend: FastAPI + PostgreSQL + Redis + FreeRADIUS SQL sync
- Frontend: Next.js + TailwindCSS + Recharts dashboards
- Roles: Super-Admin, ISP Admin, Users
- Flows: Phone+OTP auth, M-Pesa STK push callback activation, MAC/IP/phone session binding

## Project Layout

- `backend/linkedwifi_saas/main.py` FastAPI entrypoint
- `backend/linkedwifi_saas/models.py` tenant-aware ORM schema
- `backend/linkedwifi_saas/routers/` API modules
- `backend/linkedwifi_saas/session_engine.py` reconnect and expiry logic
- `backend/linkedwifi_saas/utils/freeradius.py` FreeRADIUS SQL integration
- `frontend/app/` landing page and dashboards
- `infra/schema.sql` app database schema reference
- `infra/freeradius_schema.sql` FreeRADIUS SQL tables
- `docs/local-testing.md` module-by-module setup and MikroTik tests
- `docs/deployment.md` VPS deployment notes

## Quick Start

1. Setup backend:
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m linkedwifi_saas.seed
uvicorn linkedwifi_saas.main:app --reload --port 8000
```

2. Setup frontend:
```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

3. Open:
- Landing page: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

