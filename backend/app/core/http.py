"""Client HTTP partagé (httpx) et garde-fou SSRF."""
from __future__ import annotations

import ipaddress
import socket
from functools import lru_cache
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

ALLOWED_SCHEMES = {"http", "https"}


class StreamFetchError(Exception):
    """Erreur de récupération d'un flux distant."""


def validate_remote_url(url: str) -> str:
    """Valide un schéma et bloque les adresses internes (protection SSRF)."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seules les URL http/https sont autorisées")
    if not parsed.hostname:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "URL invalide : hôte manquant")
    if settings.ALLOW_PRIVATE_STREAM_HOSTS:
        return url
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Hôte introuvable : {parsed.hostname}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Adresse réseau privée non autorisée")
    return url


@lru_cache
def get_http_client() -> httpx.Client:
    """Client partagé avec pool de connexions et limites de taille."""
    return httpx.Client(
        timeout=httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS),
        headers={"User-Agent": settings.HTTP_USER_AGENT, "Accept": "*/*"},
        follow_redirects=True,
        limits=httpx.Limits(max_connections=64, max_keepalive_connections=16),
    )


def fetch_text(url: str, *, max_bytes: int | None = None, headers: dict[str, str] | None = None) -> str:
    """Télécharge un document texte (playlist, XMLTV) avec plafond de taille."""
    max_bytes = max_bytes or settings.MAX_PLAYLIST_BYTES
    try:
        with get_http_client().stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise StreamFetchError(f"Document trop volumineux (> {max_bytes} octets)")
                chunks.append(chunk)
            raw = b"".join(chunks)
    except httpx.HTTPStatusError as exc:
        raise StreamFetchError(f"HTTP {exc.response.status_code} pour {url}") from exc
    except httpx.HTTPError as exc:
        raise StreamFetchError(f"Impossible de télécharger {url}: {exc}") from exc

    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def head_or_get_status(url: str, timeout: float | None = None) -> int | None:
    """Teste l'accessibilité d'un flux (HEAD puis GET Range si HEAD refusé)."""
    timeout = timeout or settings.PROBE_TIMEOUT_SECONDS
    try:
        response = get_http_client().head(url, timeout=timeout)
        if response.status_code < 400:
            return response.status_code
        response = get_http_client().get(url, timeout=timeout, headers={"Range": "bytes=0-1024"})
        return response.status_code
    except httpx.HTTPError:
        return None


def close_http_client() -> None:
    get_http_client().close()
    get_http_client.cache_clear()
