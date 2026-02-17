from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text

from .database import engine, settings
from .routers import auth, devices, ispadmin, payments, sessions, superadmin

app = FastAPI(title="LINKEDWIFI SaaS API", version="1.0.0")
logger = logging.getLogger("linkedwifi.api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(payments.router)
app.include_router(devices.router)
app.include_router(ispadmin.router)
app.include_router(superadmin.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    request_id = str(uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


def _check_database() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        return bool(client.ping())
    except Exception:
        return False


@app.get("/health/ready")
def ready() -> JSONResponse:
    db_ok = _check_database()
    redis_ok = _check_redis()
    overall_ok = db_ok and redis_ok
    payload = {
        "status": "ready" if overall_ok else "degraded",
        "checks": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
    }
    return JSONResponse(status_code=200 if overall_ok else 503, content=payload)
