"""Détection du type de flux et analyse du chiffrement/DRM.

⚠️ PrimeTV ne contourne aucun système de protection. Cette analyse sert uniquement à :
  * afficher un badge « chiffré / DRM » dans l'interface ;
  * permettre la lecture de contenus **libres** protégés par AES-128 ou ClearKey
    dont l'utilisateur possède légitimement les clés ;
  * exclure du scan automatique les flux DRM (Widevine/PlayReady/FairPlay).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

DRM_SCHEMES = {
    "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed": "widevine",
    "urn:uuid:9a04f079-9840-4286-ab92-e65be0885f95": "playready",
    "urn:uuid:94ce86fb-07ff-4f43-adb8-93d2fa968ca2": "fairplay",
    "urn:uuid:e2719d58-a985-b3c9-781a-b030af78d30e": "clearkey",
    "urn:uuid:1077efec-c0b2-4d02-ace3-3c1e52e2fb4b": "clearkey",
}

_ENCRYPTION_RANK = {
    "none": 0,
    "unknown": 1,
    "aes-128": 2,
    "clearkey": 3,
    "sample-aes": 4,
    "fairplay": 5,
    "playready": 5,
    "widevine": 5,
}

_ATTR_RE = re.compile(r'([A-Za-z0-9\-_]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s,]+))')


def parse_tag_attributes(line: str) -> dict[str, str]:
    """Extrait les attributs d'une balise HLS/DASH (valeurs entre guillemets ou nues)."""
    attributes: dict[str, str] = {}
    for key, double_quoted, single_quoted, bare in _ATTR_RE.findall(line):
        attributes[key.upper()] = double_quoted or single_quoted or bare
    return attributes


@dataclass
class Variant:
    """Variante de qualité d'un manifeste HLS."""

    bandwidth: int = 0
    resolution: str | None = None
    codecs: str | None = None
    url: str | None = None

    @property
    def label(self) -> str:
        if self.resolution:
            return self.resolution
        if self.bandwidth:
            return f"{round(self.bandwidth / 1000)} kbps"
        return "auto"


@dataclass
class StreamAnalysis:
    """Résultat de l'analyse d'un manifeste HLS/DASH."""

    encryption: str = "unknown"
    is_encrypted: bool = False
    drm_systems: list[str] = field(default_factory=list)
    key_uri: str | None = None
    variants: list[Variant] = field(default_factory=list)
    subtitles: list[str] = field(default_factory=list)
    audio_tracks: list[str] = field(default_factory=list)

    def merge(self, other: StreamAnalysis) -> StreamAnalysis:
        """Fusionne deux analyses en conservant le niveau de protection le plus élevé."""
        if _ENCRYPTION_RANK.get(other.encryption, 0) > _ENCRYPTION_RANK.get(self.encryption, 0):
            self.encryption = other.encryption
            self.key_uri = other.key_uri or self.key_uri
        self.is_encrypted = self.is_encrypted or other.is_encrypted
        for system in other.drm_systems:
            if system not in self.drm_systems:
                self.drm_systems.append(system)
        self.variants.extend(v for v in other.variants if v.url not in {existing.url for existing in self.variants})
        for subtitle in other.subtitles:
            if subtitle not in self.subtitles:
                self.subtitles.append(subtitle)
        for track in other.audio_tracks:
            if track not in self.audio_tracks:
                self.audio_tracks.append(track)
        return self

    def as_dict(self) -> dict:
        return {
            "encryption": self.encryption,
            "is_encrypted": self.is_encrypted,
            "drm_systems": self.drm_systems,
            "key_uri": self.key_uri,
            "variants": [
                {"bandwidth": v.bandwidth, "resolution": v.resolution, "codecs": v.codecs, "url": v.url, "label": v.label}
                for v in self.variants
            ],
            "subtitles": self.subtitles,
            "audio_tracks": self.audio_tracks,
        }


def detect_stream_type(url: str) -> str:
    """Déduit le type de flux à partir de l'URL (hls, dash, mp4, mpegts, audio...)."""
    path = urlparse(url).path.lower()
    query = urlparse(url).query.lower()
    if path.endswith((".m3u8", ".m3u")) or "m3u8" in query:
        return "hls"
    if path.endswith(".mpd"):
        return "dash"
    if path.endswith((".mp4", ".m4v", ".webm", ".mkv")):
        return "mp4"
    if path.endswith((".ts", ".mts", ".m2ts")):
        return "mpegts"
    if path.endswith((".mp3", ".aac", ".ogg", ".opus", ".m4a", ".flac")):
        return "audio"
    # Radios et proxys audio sans extension : « …/groovesalad-128-mp3 », « ?format=aac ».
    if path.endswith(("-mp3", "-aac", "-ogg")) or query in {"mp3", "aac", "ogg"}:
        return "audio"
    if path.endswith(".mpd") or "/dash" in path:
        return "dash"
    if any(token in path for token in ("/live/", "/hls/", "/stream/")):
        return "hls"
    return "other"


def analyze_hls(text: str, base_url: str | None = None) -> StreamAnalysis:
    """Analyse un manifeste HLS (master ou média) : chiffrement, variantes, pistes."""
    analysis = StreamAnalysis(encryption="none")
    pending_variant: dict | None = None
    media_lines = text.splitlines()

    for raw_line in media_lines:
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper()

        if upper.startswith("#EXT-X-STREAM-INF"):
            attributes = parse_tag_attributes(line)
            bandwidth = attributes.get("BANDWIDTH") or attributes.get("AVERAGE-BANDWIDTH") or "0"
            pending_variant = {
                "bandwidth": int(bandwidth) if str(bandwidth).isdigit() else 0,
                "resolution": attributes.get("RESOLUTION"),
                "codecs": attributes.get("CODECS"),
            }
            continue

        if upper.startswith("#EXT-X-MEDIA"):
            attributes = parse_tag_attributes(line)
            media_type = (attributes.get("TYPE") or "").upper()
            name = attributes.get("NAME") or attributes.get("LANGUAGE") or "piste"
            if media_type == "SUBTITLES":
                analysis.subtitles.append(name)
            elif media_type == "AUDIO":
                analysis.audio_tracks.append(name)
            continue

        if upper.startswith("#EXT-X-KEY"):
            attributes = parse_tag_attributes(line)
            method = (attributes.get("METHOD") or "NONE").upper()
            key_uri = attributes.get("URI")
            if key_uri and base_url:
                key_uri = urljoin(base_url, key_uri)
            if method in {"NONE", ""}:
                continue
            analysis.is_encrypted = True
            if method.startswith("SAMPLE-AES"):
                analysis.encryption = "sample-aes"
                analysis.drm_systems = sorted(set(analysis.drm_systems + ["fairplay"]))
            elif method == "AES-128":
                analysis.encryption = "aes-128"
            else:  # pragma: no cover - méthodes exotiques
                analysis.encryption = "unknown"
            if key_uri and key_uri.startswith("data:") and "clearkey" in key_uri.lower():
                analysis.encryption = "clearkey"
                analysis.drm_systems = sorted(set(analysis.drm_systems + ["clearkey"]))
            analysis.key_uri = key_uri or analysis.key_uri
            continue

        if pending_variant is not None and not line.startswith("#"):
            analysis.variants.append(Variant(url=urljoin(base_url, line) if base_url else line, **pending_variant))
            pending_variant = None

    # Master playlist avec uniquement des variantes : pas de clé au niveau racine,
    # la protection se vérifie dans chaque média playlist (fait par le scanner).
    if analysis.variants and not analysis.is_encrypted:
        analysis.encryption = "none"
    return analysis


def analyze_dash(manifest: str) -> StreamAnalysis:
    """Analyse un manifeste MPD (MPEG-DASH) : ContentProtection et systèmes DRM."""
    analysis = StreamAnalysis(encryption="none")
    lowered = manifest.lower()
    for scheme, system in DRM_SCHEMES.items():
        if scheme in lowered:
            analysis.drm_systems.append(system)
    if "urn:mpeg:dash:mp4protection" in lowered and not analysis.drm_systems:
        analysis.encryption = "unknown"
        analysis.is_encrypted = True
    if analysis.drm_systems:
        analysis.is_encrypted = True
        analysis.encryption = "clearkey" if analysis.drm_systems == ["clearkey"] else "widevine"
    # URLs de variantes basiques (Representation @id + bandwidth)
    for match in re.finditer(r'<Representation[^>]*?(?:id="([^"]*)")?[^>]*?bandwidth="(\d+)"', manifest):
        analysis.variants.append(Variant(bandwidth=int(match.group(2)), resolution=match.group(1)))
    return analysis


def merge_hint(analysis: StreamAnalysis, encryption_hint: str | None) -> StreamAnalysis:
    """Applique un indice KODIPROP/license_type trouvé dans la playlist M3U."""
    if not encryption_hint:
        return analysis
    hint = encryption_hint.lower()
    analysis.is_encrypted = True
    if "clearkey" in hint:
        analysis.encryption = "clearkey"
        analysis.drm_systems = sorted(set(analysis.drm_systems + ["clearkey"]))
    elif "widevine" in hint:
        analysis.encryption = "widevine"
        analysis.drm_systems = sorted(set(analysis.drm_systems + ["widevine"]))
    elif "playready" in hint:
        analysis.encryption = "playready"
        analysis.drm_systems = sorted(set(analysis.drm_systems + ["playready"]))
    elif "fairplay" in hint:
        analysis.encryption = "fairplay"
        analysis.drm_systems = sorted(set(analysis.drm_systems + ["fairplay"]))
    return analysis
