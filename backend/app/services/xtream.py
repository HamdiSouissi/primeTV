"""Client Xtream Codes (API player_api.php) — compatible avec les panels standards.

Les identifiants sont fournis par l'utilisateur pour son propre abonnement. Aucun
contournement n'est effectué : les flux protégés restent soumis à l'abonnement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import quote, urlparse

import httpx

from app.core.config import settings
from app.core.http import get_http_client
from app.services.m3u import ParsedChannel
from app.services.streams import detect_stream_type


class XtreamError(Exception):
    """Erreur de communication avec un serveur Xtream."""


@dataclass
class XtreamResult:
    channels: list[ParsedChannel] = field(default_factory=list)
    epg_urls: list[str] = field(default_factory=list)
    bouquets: list[dict] = field(default_factory=list)
    server_info: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def normalize_base_url(base_url: str) -> str:
    """Nettoie l'URL du portail (retire player_api.php, get.php, slash final)."""
    base_url = base_url.strip()
    if "://" not in base_url:
        base_url = f"http://{base_url}"
    parsed = urlparse(base_url)
    path = parsed.path
    for marker in ("/player_api.php", "/get.php", "/xmltv.php", "/panel_api.php"):
        if marker in path:
            path = path.split(marker)[0]
    path = path.rstrip("/")
    if path in {"/c", "/c/"}:
        path = "/c"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _api(base_url: str, username: str, password: str, action: str | None = None) -> str:
    base = normalize_base_url(base_url)
    url = f"{base}/player_api.php?username={quote(username)}&password={quote(password)}"
    if action:
        url += f"&action={action}"
    return url


def fetch_xtream(base_url: str, username: str, password: str) -> XtreamResult:
    """Récupère catégories, chaînes live, radios et EPG d'un serveur Xtream."""
    result = XtreamResult()
    client = get_http_client()

    try:
        auth = client.get(_api(base_url, username, password), timeout=settings.HTTP_TIMEOUT_SECONDS).json()
    except (httpx.HTTPError, ValueError) as exc:
        raise XtreamError(f"Connexion Xtream impossible : {exc}") from exc

    user_info = (auth or {}).get("user_info") or {}
    if str(user_info.get("auth", 1)) in {"0", "False", "false"} or (auth or {}).get("user_info") is None:
        raise XtreamError("Identifiants Xtream refusés par le serveur")
    result.server_info = (auth or {}).get("server_info") or {}

    categories: dict[str, str] = {}
    try:
        for category in client.get(_api(base_url, username, password, "get_live_categories")).json() or []:
            categories[str(category.get("category_id"))] = category.get("category_name") or "Live"
            result.bouquets.append({"id": str(category.get("category_id")), "name": category.get("category_name")})
    except (httpx.HTTPError, ValueError):
        result.warnings.append("Catégories Xtream indisponibles")

    base = normalize_base_url(base_url)

    def _append(item: dict, category_name: str | None, is_radio: bool) -> None:
        stream_id = item.get("stream_id") or item.get("series_id")
        name = (item.get("name") or "").strip()
        if not stream_id or not name:
            return
        ext = item.get("container_extension") or "m3u8"
        kind = "live" if not is_radio else "live"
        url = f"{base}/live/{quote(username)}/{quote(password)}/{stream_id}.{ext}"
        if item.get("stream_type") == "radio" or is_radio:
            url = f"{base}/radio/{quote(username)}/{quote(password)}/{stream_id}.{ext}"
        result.channels.append(
            ParsedChannel(
                name=name,
                url=url,
                group=category_name,
                logo=item.get("stream_icon") or item.get("cover"),
                tvg_id=str(item.get("epg_channel_id") or item.get("stream_id") or ""),
                extras={
                    "xtream_stream_id": stream_id,
                    "xtream_category_id": item.get("category_id"),
                    "xtream_kind": kind,
                },
                stream_type="audio" if is_radio else detect_stream_type(url),
                is_radio=is_radio,
            )
        )

    try:
        live = client.get(_api(base_url, username, password, "get_live_streams")).json() or []
        for item in live:
            _append(item, categories.get(str(item.get("category_id"))), is_radio=False)
    except (httpx.HTTPError, ValueError) as exc:
        result.warnings.append(f"Chaînes live Xtream illisibles : {exc}")

    try:
        streams = client.get(_api(base_url, username, password, "get_radio_streams")).json() or []
        for item in streams:
            _append(item, "Radio", is_radio=True)
    except (httpx.HTTPError, ValueError):
        pass  # endpoint optionnel

    result.epg_urls.append(f"{base}/xmltv.php?username={quote(username)}&password={quote(password)}")
    return result
