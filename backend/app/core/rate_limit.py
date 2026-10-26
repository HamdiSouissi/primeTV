"""Rate limiting simple et sans dépendance lourde (fenêtre fixe, Redis ou mémoire)."""
from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.core.cache import cache
from app.core.config import settings


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    user_id = getattr(request.state, "user_id", None)
    return f"user:{user_id}" if user_id else f"ip:{ip}"


async def rate_limit_middleware(request: Request, call_next):
    """Limite les requêtes par client ; les endpoints de santé sont exemptés."""
    if not settings.RATE_LIMIT_ENABLED or request.url.path in {"/healthz", "/readyz", "/metrics"}:
        return await call_next(request)

    key = f"ratelimit:{_client_key(request)}:{int(__import__('time').time()) // settings.RATE_LIMIT_WINDOW_SECONDS}"
    count = cache.incr(key, ttl=settings.RATE_LIMIT_WINDOW_SECONDS * 2)
    if count > settings.RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de requêtes, merci de patienter avant de réessayer.",
            headers={"Retry-After": str(settings.RATE_LIMIT_WINDOW_SECONDS)},
        )
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(max(0, settings.RATE_LIMIT_REQUESTS - count))
    return response
