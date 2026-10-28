"""Tests unitaires : parseur M3U, classifieur, analyse HLS/DASH et XMLTV."""
from __future__ import annotations

from datetime import UTC, datetime

from app.services.classifier import detect_category, detect_language, normalize_text
from app.services.m3u import parse_m3u
from app.services.streams import analyze_dash, analyze_hls, detect_stream_type
from app.services.xmltv import parse_xmltv, parse_xmltv_datetime

SAMPLE = """#EXTM3U url-tvg="https://example.com/epg.xml"
#EXTINF:-1 tvg-id="bein1.qa" tvg-name="beIN Sports 1" tvg-logo="https://logo/bein.png" group-title="Sport | Arabic",beIN SPORTS 1 HD
#KODIPROP:inputstream.adaptive.license_type=clearkey
https://example.com/live/bein1.m3u8
#EXTINF:-1 tvg-id="radio.quran" group-title="Religion | Arabic",إذاعة القرآن الكريم
http://example.com/radio/quran.mp3
#EXTINF:-1 tvg-id="tf1.fr" tvg-language="French" group-title="Généraliste",TF1
https://example.com/live/tf1/index.m3u8
"""


def test_parse_m3u_extracts_channels_metadata_and_epg():
    parsed = parse_m3u(SAMPLE)
    assert parsed.kind == "m3u"
    assert parsed.count == 3
    assert parsed.epg_urls == ["https://example.com/epg.xml"]
    first = parsed.channels[0]
    assert first.name == "beIN SPORTS 1 HD"
    assert first.group == "Sport | Arabic"
    assert first.tvg_id == "bein1.qa"
    assert first.stream_type == "hls"
    assert first.encryption_hint == "clearkey"
    assert parsed.channels[1].is_radio is True


def test_parse_hls_master_detection():
    master = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=1280x720,CODECS="avc1.4d401f,mp4a.40.2"
video_720.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2560000,RESOLUTION=1920x1080
video_1080.m3u8
"""
    parsed = parse_m3u(master)
    assert parsed.kind == "hls_master"
    assert parsed.analysis is not None
    assert len(parsed.analysis.variants) == 2


def test_invalid_playlist():
    parsed = parse_m3u("<html><body>Erreur</body></html>")
    assert parsed.kind == "invalid"


def test_hls_encryption_detection():
    media = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-KEY:METHOD=AES-128,URI="https://keys.example.com/k1"
#EXT-X-TARGETDURATION:6
#EXTINF:6.0,
segment1.ts
"""
    analysis = analyze_hls(media, base_url="https://example.com/live/index.m3u8")
    assert analysis.is_encrypted is True
    assert analysis.encryption == "aes-128"
    assert analysis.key_uri == "https://keys.example.com/k1"

    clear = analyze_hls('#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,URI="skd://x"\n')
    assert clear.encryption == "sample-aes"
    assert "fairplay" in clear.drm_systems


def test_dash_drm_detection():
    manifest = """<MPD xmlns="urn:mpeg:dash:schema:mpd:2011">
      <Period><AdaptationSet>
        <ContentProtection schemeIdUri="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"/>
        <Representation id="1080p" bandwidth="5000000"/>
      </AdaptationSet></Period>
    </MPD>"""
    analysis = analyze_dash(manifest)
    assert analysis.is_encrypted is True
    assert "widevine" in analysis.drm_systems
    assert analysis.variants[0].bandwidth == 5000000


def test_detect_stream_type():
    assert detect_stream_type("http://x/y/index.m3u8") == "hls"
    assert detect_stream_type("http://x/y/manifest.mpd") == "dash"
    assert detect_stream_type("http://x/y/movie.mp4") == "mp4"
    assert detect_stream_type("http://x/radio/live.mp3") == "audio"


def test_classifier_prioritises_sport_and_arabic():
    assert detect_category("beIN SPORTS 1 HD", "Sport") == "sport"
    assert detect_category("قناة الجزيرة الإخبارية", "News") == "news"
    assert detect_category("Cartoon Network", "Kids") == "kids"
    assert detect_language("MBC 1", country="SA") == "ar"
    assert detect_language("TF1", country="FR") == "fr"
    assert detect_language("TRT 1", country="TR") == "tr"
    assert normalize_text("Frànçe Télé") == "france tele"


def test_parse_xmltv():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="bein1.qa"><display-name>beIN Sports 1</display-name><icon src="http://logo/1.png"/></channel>
  <programme start="20260101120000 +0100" stop="20260101140000 +0100" channel="bein1.qa">
    <title>Match de football</title><desc>Direct</desc><category>Sport</category>
  </programme>
</tv>"""
    parsed = parse_xmltv(content)
    assert parsed.channels["bein1.qa"]["name"] == "beIN Sports 1"
    assert len(parsed.programmes) == 1
    programme = parsed.programmes[0]
    assert programme.title == "Match de football"
    assert programme.start_at == datetime(2026, 1, 1, 11, 0, tzinfo=UTC)


def test_parse_xmltv_datetime_variants():
    assert parse_xmltv_datetime("20260101120000") == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert parse_xmltv_datetime("20260101120000 -0500") == datetime(2026, 1, 1, 17, 0, tzinfo=UTC)
    assert parse_xmltv_datetime("bad") is None


def test_classifier_handles_plurals_and_radio_fallback():
    """Les groupes au pluriel sont reconnus et une radio générique reste musicale."""
    # « Documentaires » (pluriel) doit être classé documentaire, pas divertissement.
    assert detect_category("NASA TV", "Documentaires") == "documentary"
    assert detect_category("Eurosport", "Sports") == "sport"
    # « radio » n'est plus un mot-clé musical : le groupe décide.
    assert detect_category("franceinfo", "Radio — Actualités") == "news"
    assert detect_category("France Culture", "Radio — Culture") == "culture"
    from app.services.classifier import classify

    assert classify("France Musique", group="Radio — Musique", is_radio_hint=True).category_slug == "music"
    # Repli : radio sans mot-clé identifiable → music (et non entertainment).
    assert classify("France Inter", group="Radio", is_radio_hint=True).category_slug == "music"
    # Une chaîne TV sans indice reste dans « entertainment ».
    assert classify("Ma Chaîne", is_radio_hint=False).category_slug == "entertainment"
