"""Parseur XMLTV robuste (streaming, tolérant aux fichiers mal formés)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime

_TZ_RE = re.compile(r"^([+-])(\d{2})(\d{2})$")
_TIME_RE = re.compile(
    r"^\s*(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?\s*(?:([+-]\d{4})|\s+([A-Za-z/_+-]+))?"
)
_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


@dataclass
class ParsedProgramme:
    xmltv_id: str
    title: str
    start_at: datetime
    stop_at: datetime
    subtitle: str | None = None
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    rating: str | None = None


@dataclass
class ParsedEpg:
    channels: dict[str, dict] = field(default_factory=dict)  # xmltv_id -> {name, icon, url}
    programmes: list[ParsedProgramme] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_xmltv_datetime(value: str | None) -> datetime | None:
    """Convertit une date XMLTV (``20260101120000 +0100``) en datetime UTC."""
    if not value:
        return None
    match = _TIME_RE.match(value)
    if not match:
        return None
    year, month, day, hour, minute, second, offset, tzname = match.groups()
    try:
        moment = datetime(
            int(year), int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0), tzinfo=UTC
        )
    except ValueError:
        return None
    tz_offset = _TZ_RE.match(offset or "")
    if tz_offset:
        sign = -1 if tz_offset.group(1) == "-" else 1
        delta_minutes = int(tz_offset.group(2)) * 60 + int(tz_offset.group(3))
        from datetime import timedelta

        moment = moment.replace(tzinfo=None) - sign * timedelta(minutes=delta_minutes)
        return moment.replace(tzinfo=UTC)
    if tzname:
        # Fuseaux nommés : on ne tente pas d'être exhaustif, on garde l'heure locale en UTC
        return moment
    return moment


def _text(element: ET.Element | None, default: str | None = None) -> str | None:
    if element is None:
        return default
    value = "".join(element.itertext()).strip()
    return value or default


def iter_xmltv(content: str) -> Iterator[ET.Element]:
    """Itère sur les éléments racines (streaming pour les gros fichiers)."""
    try:
        for _, element in ET.iterparse(_BytesReader(content), events=("end",)):
            yield element
    except ET.ParseError as exc:
        raise ValueError(f"XMLTV invalide : {exc}") from exc


class _BytesReader:
    """Petit adaptateur pour fournir un flux d'octets à iterparse."""

    def __init__(self, content: str) -> None:
        import io

        self._stream = io.BytesIO(content.encode("utf-8", errors="replace"))

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)


def parse_xmltv(content: str, *, max_programmes: int = 200_000) -> ParsedEpg:
    """Parse un document XMLTV complet, avec déduplication et garde-fous."""
    result = ParsedEpg()
    lowered = content.lstrip()[:300].lower()
    if not lowered.startswith("<?xml") and "<tv" not in lowered:
        raise ValueError("Le document ne ressemble pas à un fichier XMLTV (<tv>)")

    try:
        for _event, element in ET.iterparse(_BytesReader(content), events=("end",)):
            tag = element.tag.split("}")[-1]
            if tag == "channel":
                xmltv_id = element.get("id") or ""
                if not xmltv_id:
                    element.clear()
                    continue
                icon = element.find("icon")
                result.channels[xmltv_id] = {
                    "id": xmltv_id,
                    "name": _text(element.find("display-name"), xmltv_id),
                    "icon": icon.get("src") if icon is not None else None,
                    "url": _text(element.find("url")),
                }
                element.clear()
            elif tag == "programme":
                if len(result.programmes) >= max_programmes:
                    result.warnings.append(f"Limite de {max_programmes} programmes atteinte")
                    break
                xmltv_id = element.get("channel") or ""
                start = parse_xmltv_datetime(element.get("start"))
                stop = parse_xmltv_datetime(element.get("stop"))
                title = _text(element.find("title"))
                if not xmltv_id or not start or not title:
                    element.clear()
                    continue
                if not stop:
                    stop = start
                rating_el = element.find("rating/value")
                icon_el = element.find("icon")
                programme = ParsedProgramme(
                    xmltv_id=xmltv_id,
                    title=title[:300],
                    start_at=start,
                    stop_at=stop,
                    subtitle=(_text(element.find("sub-title")) or None),
                    description=_text(element.find("desc")),
                    category=_text(element.find("category")),
                    icon=icon_el.get("src") if icon_el is not None else None,
                    rating=_text(rating_el),
                )
                result.programmes.append(programme)
                element.clear()
    except ET.ParseError as exc:
        raise ValueError(f"XMLTV invalide : {exc}") from exc

    # Déduplication sur (xmltv_id, start)
    seen: set[tuple[str, datetime]] = set()
    unique: list[ParsedProgramme] = []
    for programme in result.programmes:
        key = (programme.xmltv_id, programme.start_at)
        if key in seen:
            continue
        seen.add(key)
        unique.append(programme)
    result.programmes = unique
    return result
