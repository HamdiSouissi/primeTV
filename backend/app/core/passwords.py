"""Hachage des mots de passe.

Implémentation PBKDF2-HMAC-SHA256 (bibliothèque standard, FIPS-friendly, sans dépendance
native). Format stocké : ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 390_000
_SALT_BYTES = 16


def hash_password(password: str, iterations: int = _ITERATIONS, min_length: int = 8) -> str:
    """Retourne le hash encodé d'un mot de passe en clair.

    ``min_length`` est abaissé à 4 pour les codes PIN des profils.
    """
    if not password or len(password) < min_length:
        raise ValueError(f"Le secret doit contenir au moins {min_length} caractères")
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{_ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Vérifie un mot de passe contre un hash encodé (comparaison en temps constant)."""
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != _ALGORITHM:
            return False
        expected = bytes.fromhex(digest_hex)
        computed = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(computed, expected)
    except (ValueError, TypeError):
        return False


def needs_rehash(encoded: str) -> bool:
    """Indique si le hash doit être recalculé (coût obsolète)."""
    try:
        _, iterations, _, _ = encoded.split("$", 3)
        return int(iterations) < _ITERATIONS
    except (ValueError, TypeError):
        return True
