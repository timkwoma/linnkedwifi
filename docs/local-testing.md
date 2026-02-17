# Local Testing Guide (PC + MikroTik + FreeRADIUS)

## 1. Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- FreeRADIUS 3.x (Ubuntu/WSL2 VM recommended)
- MikroTik router connected on same LAN as test PC

## 2. PostgreSQL Setup

Create DBs:

```sql
create database linkedwifi;
create database radius;
```

Apply schema:

```powershell
psql -U postgres -d linkedwifi -f infra/schema.sql
psql -U postgres -d radius -f infra/freeradius_schema.sql
```

Then seed app data:

```powershell
cd backend
python -m linkedwifi_saas.seed
```

Seed outputs include:
- 2 tenants
- 2 MikroTik devices
- 5 packages (hotspot + home)
- 1 super-admin account
- 1 ISP admin account

## 3. Backend Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:
- `DATABASE_URL=postgresql+psycopg://.../linkedwifi`
- `RADIUS_DB_URL=postgresql+psycopg://.../radius`
- Set valid M-Pesa sandbox credentials

Run API:

```powershell
uvicorn linkedwifi_saas.main:app --reload --port 8000
```

If you use migrations, run:
```powershell
cd backend
alembic upgrade head
```

## 4. Redis + Session Cleanup

Start Redis, then queue and run cleanup jobs:

1. `POST /sessions/jobs/enqueue-expiry`
2. `POST /sessions/jobs/run-once`

This marks expired `active` sessions as `expired` and removes FreeRADIUS entries.

## 5. Module-by-Module API Tests

## Module 1: DB + ORM

- `GET /health` returns `{"status":"ok"}`
- Verify seeded tables in PostgreSQL.

## Module 2: Auth (phone + OTP)

1. `POST /auth/request-otp` with:
```json
{"phone":"+254700000002","role":"isp_admin","tenant_id":"<tenant_uuid>"}
```
2. Use returned `dev_otp` in `POST /auth/verify-otp`.
3. Confirm JWT token returned.

## Module 3: Session Engine + FreeRADIUS

1. Trigger a paid session (module 4 callback), or call `POST /sessions/activate`.
2. Reconnect via `POST /sessions/reconnect` with new MAC/IP.
3. Check `radcheck` and `radreply` rows in `radius` DB.
4. Advance time (or edit `end_time`) and run cleanup job.
5. Confirm session becomes `expired` and radius rows are removed.

## Module 4: Payments (M-Pesa)

1. `POST /payments/mpesa/stk-push`
2. Simulate callback to `POST /payments/mpesa/callback` with `ResultCode = 0`.
3. Verify:
- `payments.status = success`
- session created in `sessions`
- FreeRADIUS entries inserted.

## Module 5: Dashboard APIs

- Super Admin:
  - `GET /superadmin/stats`
  - `GET /superadmin/tenants`
  - `POST /superadmin/tenants`
- ISP Admin:
  - `GET /ispadmin/stats?tenant_id=...`
  - `GET /ispadmin/users?tenant_id=...`
  - `GET /ispadmin/packages?tenant_id=...`
  - `GET /ispadmin/payments?tenant_id=...`
  - `GET /devices?tenant_id=...`

## 6. Frontend Setup

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Pages:
- `/` landing page
- `/login` role-based OTP login
- `/super-admin` global dashboard
- `/isp-admin` tenant dashboard

## 7. MikroTik + FreeRADIUS Wiring

1. In MikroTik:
- Enable hotspot on LAN bridge/interface.
- Configure RADIUS:
  - Service: `hotspot`
  - Address: FreeRADIUS server IP
  - Secret: shared secret matching FreeRADIUS `clients.conf`

2. In FreeRADIUS (`sites-enabled/default`):
- Enable SQL module and use `radius` database.
- Confirm `authorize` and `accounting` sections include `sql`.

3. Captive Portal Flow:
- User connects to hotspot and enters phone/OTP.
- Buy package via M-Pesa.
- Callback activates session and writes radius check/reply rules.
- MikroTik authenticates user through FreeRADIUS.

## 8. Suggested Smoke Script

1. Seed data.
2. Login as ISP Admin via OTP.
3. Create STK push payment.
4. Post callback success.
5. Reconnect from same phone with different MAC/IP.
6. Confirm dashboard stats and active session count change.
