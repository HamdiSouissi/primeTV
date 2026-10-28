"""Chiffrement symétrique des secrets stockés (identifiants fournisseurs IPTV).

Utilise Fernet (AES-128-CBC + HMAC-SHA256) de la bibliothèque ``cryptography``.
La clé est dérivée de ``SECRET_KEY`` : changer ce secret invalide les valeurs existantes.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(f"primetv::credentials::{settings.SECRET_KEY}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def mask_secret(value: str | None) -> str | None:
    """Retourne une version masquée pour l'API (jamais le secret en clair)."""
    if not value:
        return None
    return "••••••••"
