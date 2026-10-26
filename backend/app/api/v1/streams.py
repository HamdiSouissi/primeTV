"""Proxy de lecture HLS/DASH et distribution des clés fournies par l'utilisateur."""
from __future__ import annotations

import base64
import binascii
from urllib.parse import unquote, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.core.http import get_http_client, validate_remote_url
from app.db.session import get_db
from app.models.catalog import Channel
from app.models.user import User
from app.services.proxy import assert_host_allowed, fetch_manifest, rewrite_dash, rewrite_hls

router = APIRouter()


def _load_channel(channel_id: str | None, db: Session) -> Channel | None:
    if not channel_id:
        return None
    return db.get(Channel, channel_id)


def _base_domain(channel: Channel | None) -> str | None:
    if not channel:
        return None
    host = (urlparse(channel.stream_url).hostname or "").lower()
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


@router.get("/proxy", summary="Relayer un flux (manifeste, segment, clé)")
def proxy(
    url: str = Query(..., description="URL absolue de la ressource d'origine"),
    channel_id: str | None = Query(None, description="Identifiant de la chaîne (restreint les hôtes)"),
    request: Request = None,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Proxy transparent avec réécriture des manifestes HLS/DASH.

    Sécurité : si ``channel_id`` est fourni, seuls les hôtes du même domaine que le flux
    d'origine sont autorisés (protection contre l'usage en relais ouvert).
    """
    target = unquote(url).strip()
    if not target.startswith(("http://", "https://")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "URL invalide")
    channel = _load_channel(channel_id, db)
    if channel_id and not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")
    if channel:
        assert_host_allowed(target, _base_domain(channel))
    else:
        validate_remote_url(target)

    lower_path = target.split("?")[0].lower()
    is_manifest = lower_path.endswith((".m3u8", ".m3u", ".mpd"))

    if is_manifest:
        text, content_type = fetch_manifest(target)
        if lower_path.endswith(".mpd") or "<MPD" in text:
            body = rewrite_dash(text, target)
            media_type = "application/dash+xml"
        else:
            body = rewrite_hls(text, target, channel_id)
            media_type = "application/vnd.apple.mpegurl"
        return Response(
            content=body,
            media_type=media_type,
            headers={
                "Cache-Control": "no-store",
                "Access-Control-Allow-Origin": "*",
                "Content-Type": f"{media_type}; charset=utf-8",
            },
        )

    # Segments / clés / sous-titres : streaming direct
    try:
        upstream = get_http_client().send(
            get_http_client().build_request("GET", target), stream=True
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Flux injoignable : {exc}") from exc
    if upstream.status_code >= 400:
        upstream.close()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Source HTTP {upstream.status_code}")

    def iterator():
        try:
            yield from upstream.iter_bytes()
        finally:
            upstream.close()

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-cache",
        "Accept-Ranges": upstream.headers.get("accept-ranges", "none"),
    }
    if upstream.headers.get("content-length"):
        headers["Content-Length"] = upstream.headers["content-length"]
    return StreamingResponse(
        iterator(),
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/octet-stream"),
        headers=headers,
    )


def _key_from_clear_keys(channel: Channel, uri: str) -> bytes | None:
    keys: dict[str, str] = channel.clear_keys or {}
    if not keys:
        return None
    if uri.startswith("data:"):
        try:
            _, payload = uri.split(",", 1)
            decoded = base64.b64decode(payload).decode("utf-8", errors="replace").strip()
            if ":" in decoded:
                _, key_hex = decoded.split(":", 1)
                return bytes.fromhex(key_hex.strip())
        except (ValueError, binascii.Error):
            pass
    if len(keys) == 1:
        return bytes.fromhex(next(iter(keys.values())))
    return None


@router.get("/key", summary="Servir une clé AES-128/ClearKey (contenu autorisé)")
def stream_key(
    uri: str = Query(..., description="URI de clé d'origine (ou data: URI)"),
    channel_id: str | None = Query(None),
    kid: str | None = Query(None, description="Key ID si plusieurs clés"),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Relaie une clé détenue par l'utilisateur (ClearKey) ou la clé distante d'origine.

    ⚠️ Aucune clé n'est devinée ni contournée. Si le contenu n'est pas libre, la clé
    distante n'est servie que si la source l'autorise déjà (abonnement de l'utilisateur).
    """
    channel = _load_channel(channel_id, db)
    if channel_id and not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")

    if channel and channel.clear_keys:
        resolved_uri = unquote(uri)
        if kid and kid.lower() in channel.clear_keys:
            return Response(bytes.fromhex(channel.clear_keys[kid.lower()]), media_type="application/octet-stream")
        key_bytes = _key_from_clear_keys(channel, resolved_uri)
        if key_bytes:
            return Response(key_bytes, media_type="application/octet-stream")
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "key_not_found", "message": "Aucune clé correspondante enregistrée"}},
        )

    target = unquote(uri)
    if not target.startswith(("http://", "https://")):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Clé locale indisponible : ajoutez vos clés (KID/KEY) via PUT /channels/{id}/keys",
        )
    if channel:
        assert_host_allowed(target, _base_domain(channel))
    else:
        validate_remote_url(target)
    try:
        response = get_http_client().get(target)
    except httpx.HTTPError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    if response.status_code >= 400:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Clé inaccessible (HTTP {response.status_code})")
    return Response(
        content=response.content,
        media_type="application/octet-stream",
        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "no-store"},
    )
