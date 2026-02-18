from __future__ import annotations

import json

from redis import Redis

from .database import SessionLocal, settings
from .session_engine import expire_stale_sessions

QUEUE_KEY = "linkedwifi:jobs"


def redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def enqueue_cleanup_job() -> None:
    client = redis_client()
    client.rpush(QUEUE_KEY, json.dumps({"type": "expire_sessions"}))


def run_worker_once() -> int:
    client = redis_client()
    job = client.lpop(QUEUE_KEY)
    if not job:
        return 0

    payload = json.loads(job)
    if payload.get("type") != "expire_sessions":
        return 0

    db = SessionLocal()
    try:
        count = expire_stale_sessions(db)
        db.commit()
        return count
    finally:
        db.close()
