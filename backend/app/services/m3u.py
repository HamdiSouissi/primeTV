"""Parseur M3U / M3U8 (M3U Plus inclus) tolérant et sans dépendance externe."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.services.streams import StreamAnalysis, analyze_hls, detect_stream_type

_ATTR_RE = re.compile(r'([A-Za-z0-9\-_]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s,]+))')
_EXTINF_RE = re.compile(r"^#EXTINF\s*:\s*(-?\d+(?:\.\d+)?)?(.*)$", re.IGNORECASE)
_RADIO_HINTS = ("radio", "راديو", "راديو ", "fm", "audio")
_M3U_HEADER = "#EXTM3U"


@dataclass
class ParsedChannel:
    """Une entrée de playlist prête à être insérée en base."""

    name: str
    url: str
    group: str | None = None
    logo: str | None = None
    tvg_id: str | None = None
    tvg_name: str | None = None
    tvg_language: str | None = None
    tvg_country: str | None = None
    tvg_shift: str | None = None
    duration: str | None = None
    is_radio: bool = False
    stream_type: str = "hls"
    encryption_hint: str | None = None
    extras: dict = field(default_factory=dict)


@dataclass
class ParsedPlaylist:
    """Résultat complet du parsing d'une playlist."""

    channels: list[ParsedChannel] = field(default_factory=list)
    epg_urls: list[str] = field(default_factory=list)
    xtream_hints: dict = field(default_factory=dict)
    kind: str = "m3u"  # m3u | hls_master | hls_media | empty | invalid
    analysis: StreamAnalysis | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.channels)


def parse_attributes(text: str) -> dict[str, str]:
    """Extrait les attributs ``clé="valeur"`` d'une ligne #EXTINF ou #EXT-X-*."""
    attributes: dict[str, str] = {}
    for key, quoted, simple_quoted, bare in _ATTR_RE.findall(text):
        attributes[key.lower()] = quoted or simple_quoted or bare
    return attributes


def _looks_like_radio(name: str, group: str | None, attributes: dict[str, str], stream_type: str) -> bool:
    if attributes.get("radio", "").lower() in {"1", "true", "yes"}:
        return True
    if stream_type == "audio":
        return True
    haystack = f"{name} {group or ''}".lower()
    return any(hint in haystack for hint in _RADIO_HINTS) and stream_type != "mp4"


def _build_channel(line: str, url: str, fallback_index: int) -> ParsedChannel | None:
    match = _EXTINF_RE.match(line.strip())
    if not match:
        return None
    duration, rest = match.groups()
    duration = duration or "-1"
    if "," in rest:
        attrs_part, display_name = rest.rsplit(",", 1)
    else:
        attrs_part, display_name = rest, ""
    attributes = parse_attributes(attrs_part)
    name = (display_name or attributes.get("tvg-name") or f"Chaîne {fallback_index}").strip()
    name = re.sub(r"\s+", " ", name)
    if not name or not url:
        return None

    stream_type = detect_stream_type(url)
    encryption_hint = attributes.get("kodi_key_format") or attributes.get("inputstream.adaptive.license_type")
    extras = {
        key: value
        for key, value in attributes.items()
        if key
        not in {
            "tvg-id",
            "tvg-name",
            "tvg-logo",
            "group-title",
            "tvg-language",
            "tvg-country",
            "tvg-shift",
            "radio",
        }
    }
    return ParsedChannel(
        name=name,
        url=url,
        group=attributes.get("group-title") or None,
        logo=attributes.get("tvg-logo") or None,
        tvg_id=attributes.get("tvg-id") or None,
        tvg_name=attributes.get("tvg-name") or None,
        tvg_language=attributes.get("tvg-language") or None,
        tvg_country=attributes.get("tvg-country") or attributes.get("tvg-country-code") or None,
        tvg_shift=attributes.get("tvg-shift") or None,
        duration=duration,
        is_radio=_looks_like_radio(name, attributes.get("group-title"), attributes, stream_type),
        stream_type=stream_type,
        encryption_hint=encryption_hint,
        extras=extras,
    )


def is_hls_manifest(text: str) -> bool:
    """Un document HLS commence par #EXTM3U mais n'a aucune entrée #EXTINF."""
    head = text.lstrip()[:2048].upper()
    return head.startswith(_M3U_HEADER) or "#EXT-X-STREAM-INF" in head or "#EXT-X-TARGETDURATION" in head


def parse_m3u(content: str) -> ParsedPlaylist:
    """Parse un contenu M3U/M3U8 et retourne chaînes, URLs EPG et métadonnées."""
    result = ParsedPlaylist()
    if not content or not content.strip():
        result.kind = "empty"
        result.warnings.append("Contenu vide")
        return result

    text = content.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    first_line = text.split("\n", 1)[0].strip()
    if not first_line.upper().startswith(_M3U_HEADER):
        result.warnings.append("En-tête #EXTM3U absente : tentative d'analyse tolérante")
        if "<" in text[:200]:
            result.kind = "invalid"
            result.warnings.append("Le contenu semble être du XML/HTML, pas une playlist M3U")
            return result

    lines = text.split("\n")

    # Métadonnées d'en-tête : url-tvg / x-tvg-url / xtream
    header_attrs = parse_attributes(lines[0])
    for key in ("url-tvg", "x-tvg-url", "tvg-url", "x-tvg"):
        if header_attrs.get(key):
            result.epg_urls.extend(part.strip() for part in header_attrs[key].split(",") if part.strip())
    result.epg_urls = list(dict.fromkeys(result.epg_urls))

    has_stream_inf = any(line.strip().upper().startswith("#EXT-X-STREAM-INF") for line in lines)
    has_extinf = any(line.strip().upper().startswith("#EXTINF") for line in lines)

    if has_stream_inf and not has_extinf:
        # Manifeste HLS maître : une seule « chaîne » correspondant au flux
        analysis = analyze_hls(text)
        result.kind = "hls_master"
        result.analysis = analysis
        result.xtream_hints = {"variants": [v.label for v in analysis.variants]}
        return result
    if not has_extinf:
        if any(line.strip().upper().startswith("#EXT-X-TARGETDURATION") for line in lines):
            result.kind = "hls_media"
            result.analysis = analyze_hls(text)
            return result
        result.kind = "invalid"
        result.warnings.append("Aucune entrée #EXTINF trouvée")
        return result

    result.kind = "m3u"
    pending_line: str | None = None
    crypto_attrs: dict[str, str] = {}
    index = 0

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#EXTM3U"):
            continue
        if line.upper().startswith("#EXTINF"):
            pending_line = line
            continue
        if line.upper().startswith("#KODIPROP"):
            # Ex. #KODIPROP:inputstream.adaptive.license_type=clearkey
            if ":" in line:
                key, value = line.split(":", 1)
                if "=" in value:
                    attr_key, attr_value = value.split("=", 1)
                    crypto_attrs[attr_key.strip()] = attr_value.strip()
            continue
        if line.startswith("#"):
            continue

        if pending_line is None:
            # Ligne d'URL isolée (playlists minimalistes) : on l'accepte si http(s)
            if line.lower().startswith(("http://", "https://", "rtmp://", "rtsp://", "udp://")):
                index += 1
                parsed_url = urlparse(line)
                channel = ParsedChannel(
                    name=parsed_url.netloc or f"Flux {index}",
                    url=line,
                    stream_type=detect_stream_type(line),
                    is_radio=detect_stream_type(line) == "audio",
                )
                result.channels.append(channel)
            continue

        index += 1
        channel = _build_channel(pending_line, line, index)
        pending_line = None
        if channel is None:
            continue
        if crypto_attrs and not channel.encryption_hint:
            channel.encryption_hint = crypto_attrs.get("inputstream.adaptive.license_type")
            channel.extras.setdefault("kodiprops", dict(crypto_attrs))
        crypto_attrs = {}
        result.channels.append(channel)

    if pending_line:
        result.warnings.append("Dernière entrée #EXTINF sans URL ignorée")
    if not result.channels:
        result.kind = "empty"
        result.warnings.append("Aucune chaîne valide détectée")
    return result


def parse_hls_master(text: str, url: str) -> ParsedPlaylist:
    """Convertit un manifeste HLS maître en playlist d'une seule chaîne."""
    analysis = analyze_hls(text, base_url=url)
    name = urlparse(url).path.rstrip("/").split("/")[-1].replace(".m3u8", "") or "Flux HLS"
    channel = ParsedChannel(
        name=name,
        url=url,
        stream_type="hls",
        encryption_hint="clearkey" if analysis.encryption == "clearkey" else None,
        extras={"variants": [v.label for v in analysis.variants]},
    )
    return ParsedPlaylist(channels=[channel], kind="hls_master", analysis=analysis)
