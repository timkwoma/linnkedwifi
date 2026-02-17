# VPS Deployment Notes

This project now includes deployment templates:

- `infra/systemd/linkedwifi-backend.service`
- `infra/systemd/linkedwifi-frontend.service`
- `infra/nginx.linkedwifi.conf`
- `infra/docker-compose.prod.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`

## Option A: Systemd + Nginx

1. Provision Ubuntu 22.04+ VM.
2. Install packages:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm nginx
```
3. Deploy code to:
- `/opt/linkedwifi/backend`
- `/opt/linkedwifi/frontend`
4. Backend setup:
```bash
cd /opt/linkedwifi/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
5. Frontend setup:
```bash
cd /opt/linkedwifi/frontend
npm ci
npm run build
```
6. Install systemd units:
```bash
sudo cp infra/systemd/linkedwifi-backend.service /etc/systemd/system/
sudo cp infra/systemd/linkedwifi-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now linkedwifi-backend linkedwifi-frontend
```
7. Install Nginx site:
```bash
sudo cp infra/nginx.linkedwifi.conf /etc/nginx/sites-available/linkedwifi
sudo ln -s /etc/nginx/sites-available/linkedwifi /etc/nginx/sites-enabled/linkedwifi
sudo nginx -t && sudo systemctl reload nginx
```
8. Add TLS:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d linkedwifi.example.com
```
9. Verify health endpoints:
```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/ready
curl http://linkedwifi.example.com/health/ready
```
Optional one-command smoke test:
```bash
chmod +x infra/scripts/smoke-check.sh
BACKEND_URL=http://127.0.0.1:8000 \
FRONTEND_URL=http://127.0.0.1:3000 \
PUBLIC_URL=http://linkedwifi.example.com \
infra/scripts/smoke-check.sh
```

## Option B: Docker Compose

1. Install Docker + Compose plugin.
2. Set production env files:
- `backend/.env`
- `frontend/.env.local`
3. Run:
```bash
cd infra
docker compose -f docker-compose.prod.yml up -d --build
```
Then verify:
```bash
curl http://127.0.0.1:8000/health/ready
docker compose -f docker-compose.prod.yml ps
```
The `backend` container now has an explicit healthcheck against `/health/ready`, and `frontend` waits for a healthy backend before startup.
You can also run:
```bash
chmod +x infra/scripts/smoke-check.sh
infra/scripts/smoke-check.sh
```

## Security Checklist

- Rotate JWT secret and M-Pesa credentials before go-live.
- Set `MPESA_CALLBACK_SECRET` and send it as `X-Callback-Secret` on callback requests.
- Restrict PostgreSQL and Redis to private network only.
- Enforce HTTPS for callback and dashboard traffic.
- Keep VM packages updated and enable firewall rules.

## Runtime Observability

- API responses include `X-Request-ID` for request tracing.
- Backend logs include request id, method, path, status, and latency.
- On systemd deployments, inspect logs with:
```bash
journalctl -u linkedwifi-backend -f
```
