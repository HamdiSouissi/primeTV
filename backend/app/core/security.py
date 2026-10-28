"""JWT : création et vérification des jetons d'accès / rafraîchissement."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from fastapi import HTTPException, status

from app.core.config import settings

TokenType = Literal["access", "refresh"]


def _encode(subject: str, token_type: TokenType, expires_delta: timedelta, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": str(uuid.uuid4()),
        "iss": settings.APP_NAME,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, role: str = "user") -> str:
    return _encode(subject, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), {"role": role})


def create_refresh_token(subject: str) -> str:
    return _encode(subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Décode et valide un JWT ; lève une HTTPException 401 si invalide/expiré."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.APP_NAME,
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton expiré", {"WWW-Authenticate": "Bearer"}) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton invalide", {"WWW-Authenticate": "Bearer"}) from exc

    if expected_type and payload.get("type") != expected_type:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Type de jeton inattendu")
    return payload
