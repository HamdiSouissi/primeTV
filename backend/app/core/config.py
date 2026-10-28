"""Configuration centralisée (12-factor) chargée depuis l'environnement / .env."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Tous les réglages de la plateforme.

    Chaque valeur peut être surchargée par une variable d'environnement du même nom
    (voir `.env.example` et `docs/CONFIGURATION.md`).
    """

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore", case_sensitive=False)

    # --- Application ---
    APP_NAME: str = "PrimeTV"
    APP_VERSION: str = "1.0.0"
    ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    PUBLIC_BASE_URL: str = "http://localhost:8080"
    DOCS_ENABLED: bool = True

    # --- Sécurité ---
    SECRET_KEY: str = "dev-only-change-me-please-0123456789abcdef"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    ALLOW_REGISTRATION: bool = True
    CORS_ORIGINS: str = "*"
    TRUSTED_HOSTS: str = "*"
    SECURE_HEADERS: bool = True
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 300
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # --- Base de données ---
    DATABASE_URL: str = "sqlite:///./primetv_local.db"
    DB_ECHO: bool = False
    AUTO_CREATE_SCHEMA: bool = True
    FORCE_HTTPS: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- Cache / Redis ---
    REDIS_URL: str = ""  # vide => cache mémoire intégré (dev/tests)
    CACHE_TTL_SECONDS: int = 60
    CACHE_ENABLED: bool = True

    # --- Réseau / import ---
    HTTP_TIMEOUT_SECONDS: float = 25.0
    HTTP_USER_AGENT: str = "PrimeTV/1.0 (+https://github.com/HamdiSouissi/primeTV)"
    MAX_PLAYLIST_BYTES: int = 40 * 1024 * 1024
    MAX_IMPORT_CHANNELS: int = 60000
    PROBE_CONCURRENCY: int = 8
    PROBE_TIMEOUT_SECONDS: float = 8.0
    SCAN_MAX_CHANNELS: int = 5000
    ALLOW_PRIVATE_STREAM_HOSTS: bool = False

    # --- Priorisation de l'interface ---
    PRIORITY_SPORT: int = 40
    PRIORITY_ARABIC: int = 35
    PRIORITY_NEWS: int = 20
    PRIORITY_FRENCH: int = 10

    # --- Divers ---
    DEFAULT_ADMIN_EMAIL: str = "admin@primetv.io"
    DEFAULT_ADMIN_PASSWORD: str = "PrimeTV#2026"
    SEED_DEMO_DATA: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_key_length(cls, value: str) -> str:
        if len(value) < 16:
            raise ValueError("SECRET_KEY doit contenir au moins 16 caractères")
        return value

    @property
    def cors_origins(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",") if host.strip()] or ["*"]

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def database_url(self) -> str:
        """Normalise l'URL pour SQLAlchemy (postgres:// -> postgresql+psycopg://)."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Instance unique des réglages (mise en cache pour éviter de relire le .env)."""
    return Settings()


settings = get_settings()
