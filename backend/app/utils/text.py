"""Petites fonctions utilitaires partagées."""
from __future__ import annotations

import re
import unicodedata


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "item"


def truncate(value: str, length: int = 200, suffix: str = "…") -> str:
    return value if len(value) <= length else value[: length - len(suffix)] + suffix
