"""Cache applicatif : Redis si disponible, sinon cache mémoire avec TTL.

L'API reste fonctionnelle sans Redis (utile pour les tests et le développement local).
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class _MemoryBackend:
    """Backend de secours : dictionary thread-safe avec expiration paresseuse."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at and expires_at < time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: str, ttl: int) -> None:
        with self._lock:
            self._data[key] = (time.time() + ttl if ttl else 0.0, value)

    def delete(self, *keys: str) -> None:
        with self._lock:
            for key in keys:
                self._data.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in [k for k in self._data if k.startswith(prefix)]:
                self._data.pop(key, None)

    def incr(self, key: str, ttl: int) -> int:
        with self._lock:
            current = self.get(key)
            value = int(current or 0) + 1
            self.set(key, str(value), ttl)
            return value


class Cache:
    """Façade de cache JSON avec compteur atomique (rate limiting)."""

    def __init__(self) -> None:
        self._memory = _MemoryBackend()
        self._redis: Any = None
        if settings.REDIS_URL:
            try:
                import redis  # import paresseux : optionnel

                client = redis.Redis.from_url(
                    settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1.5, socket_timeout=1.5
                )
                client.ping()
                self._redis = client
                logger.info("Cache Redis connecté (%s)", settings.REDIS_URL)
            except Exception as exc:  # pragma: no cover - dépend de l'environnement
                logger.warning("Redis indisponible (%s) : bascule sur le cache mémoire", exc)
                self._redis = None

    @property
    def backend_name(self) -> str:
        return "redis" if self._redis is not None else "memory"

    def get_json(self, key: str) -> Any | None:
        raw = self._redis.get(key) if self._redis else self._memory.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        payload = json.dumps(value, default=str, ensure_ascii=False)
        ttl = settings.CACHE_TTL_SECONDS if ttl is None else ttl
        if self._redis:
            try:
                self._redis.setex(key, ttl, payload)
                return
            except Exception:  # pragma: no cover
                pass
        self._memory.set(key, payload, ttl)

    def delete(self, *keys: str) -> None:
        if self._redis:
            try:
                if keys:
                    self._redis.delete(*keys)
                return
            except Exception:  # pragma: no cover
                pass
        self._memory.delete(*keys)

    def invalidate_prefix(self, prefix: str) -> None:
        """Invalide toutes les entrées d'un namespace (ex. ``channels:``)."""
        if self._redis:
            try:
                for key in self._redis.scan_iter(match=f"{prefix}*", count=500):
                    self._redis.delete(key)
                return
            except Exception:  # pragma: no cover
                pass
        self._memory.delete_prefix(prefix)

    def incr(self, key: str, ttl: int) -> int:
        if self._redis:
            try:
                pipe = self._redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, ttl)
                return int(pipe.execute()[0])
            except Exception:  # pragma: no cover
                pass
        return self._memory.incr(key, ttl)


cache = Cache()
