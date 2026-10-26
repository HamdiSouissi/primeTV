"""Proxy de lecture HLS/DASH.

Objectif : rendre lisibles les flux distants qui n'envoient pas d'en-têtes CORS,
et réécrire les manifestes pour que le lecteur web puisse suivre les segments et les clés.
Aucun déchiffrement n'est effectué ici : les clés fournies par l'utilisateur (ClearKey /
AES-128 sur du contenu qu'il est en droit de lire) sont simplement relayées au lecteur.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote, urljoin, urlparse

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.http import get_http_client

_ATTR_RE = re.compile(r'([A-Za-z0-9\-_]+)\s*=\s*"([^"]*)"')


@dataclass
class ProxyContext:
    channel_id: str | None
    base_domain: str | None


def proxy_url(url: str, channel_id: str | None = None) -> str:
    """Construit l'URL (relative) du proxy pour une ressource.

    Le chemin est relatif à l'origine de l'API : la web app et Nginx
    fonctionnent ainsi en même-origine, sans dépendre d'un nom d'hôte.
    """
    path = f"{settings.API_V1_PREFIX}/streams/proxy?url={quote(url, safe='')}"
    if channel_id:
        path += f"&channel_id={quote(channel_id)}"
    return path


def key_url(key_uri: str, channel_id: str | None) -> str:
    path = f"{settings.API_V1_PREFIX}/streams/key?uri={quote(key_uri, safe='')}"
    if channel_id:
        path += f"&channel_id={quote(channel_id)}"
    return path


def assert_host_allowed(url: str, base_domain: str | None) -> None:
    """Empêche l'utilisation du proxy comme relais ouvert (anti-SSRF / abus)."""
    if not base_domain:
        return
    host = (urlparse(url).hostname or "").lower()
    if not host:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "URL de ressource invalide")
    allowed = host == base_domain or host.endswith(f".{base_domain}") or base_domain.endswith(f".{host}")
    if not allowed and base_domain not in url:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Hôte non autorisé par le proxy de lecture")


def rewrite_hls(text: str, base_url: str, channel_id: str | None) -> str:
    """Réécrit un manifeste HLS : variantes, segments, clés et sous-titres via le proxy."""
    lines = text.splitlines()
    output: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            output.append(raw)
            continue
        if line.startswith("#"):
            upper = line.upper()
            if upper.startswith(("#EXT-X-KEY", "#EXT-X-SESSION-KEY")):
                attributes = dict(_ATTR_RE.findall(line))
                uri = attributes.get("URI")
                if uri:
                    resolved = urljoin(base_url, uri)
                    new_uri = key_url(resolved, channel_id)
                    line = re.sub(r'URI="[^"]*"', f'URI="{new_uri}"', line, count=1)
                output.append(line)
                continue
            if upper.startswith("#EXT-X-MAP") or upper.startswith("#EXT-X-MEDIA"):
                attributes = dict(_ATTR_RE.findall(line))
                uri = attributes.get("URI")
                if uri:
                    line = re.sub(
                        r'URI="[^"]*"',
                        f'URI="{proxy_url(urljoin(base_url, uri), channel_id)}"',
                        line,
                        count=1,
                    )
                output.append(line)
                continue
            output.append(line)
            continue
        output.append(proxy_url(urljoin(base_url, line), channel_id))
    return "\n".join(output) + "\n"


def rewrite_dash(manifest: str, base_url: str) -> str:
    """Injecte une BaseURL absolue dans un MPD pour que le lecteur résolve les segments."""
    if "<BaseURL>" in manifest:
        return manifest
    base = base_url.rsplit("/", 1)[0] + "/"
    return re.sub(r"(<MPD[^>]*>)", rf"\1<BaseURL>{base}</BaseURL>", manifest, count=1)


def fetch_manifest(url: str) -> tuple[str, str]:
    """Télécharge un manifeste (texte) et retourne (contenu, content_type)."""
    try:
        response = get_http_client().get(url, timeout=settings.HTTP_TIMEOUT_SECONDS)
    except Exception as exc:  # pragma: no cover - réseau
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Flux injoignable : {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Le serveur source a répondu {response.status_code}")
    return response.text, response.headers.get("content-type", "application/vnd.apple.mpegurl")
