from __future__ import annotations

from collections.abc import Generator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/linkedwifi"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    otp_expiry_seconds: int = 300
    mpesa_base_url: str = "https://sandbox.safaricom.co.ke"
    mpesa_consumer_key: str = "change-me"
    mpesa_consumer_secret: str = "change-me"
    mpesa_passkey: str = "change-me"
    mpesa_shortcode: str = "174379"
    mpesa_callback_url: str = "http://localhost:8000/payments/mpesa/callback"
    mpesa_callback_secret: str | None = None
    radius_db_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
