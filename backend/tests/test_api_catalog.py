"""Tests d'intégration : import de playlists, recherche, favoris, historique, EPG, scan."""
from __future__ import annotations

PLAYLIST = """#EXTM3U
#EXTINF:-1 tvg-id="test.sport.1" tvg-logo="https://logo/1.png" group-title="Sport | Arabic",beIN SPORTS 1 HD
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8
#EXTINF:-1 tvg-id="test.news.1" group-title="News | Arabic",الجزيرة مباشر
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8?news
#EXTINF:-1 tvg-id="test.music.1" group-title="Music | Radio",Radio Soleil
https://ice2.somafm.com/groovesalad-128-mp3
#EXTINF:-1 tvg-id="test.enc.1" group-title="Sport | French",beIN SPORTS 2 chiffré
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8?enc
"""


def _import_playlist(client, headers, name="Playlist de test"):
    response = client.post(
        "/api/v1/playlists",
        json={"name": name, "source_type": "text", "content": PLAYLIST, "replace": True},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_import_playlist_text(client, admin_headers, user_headers):
    result = _import_playlist(client, user_headers)
    assert result["total"] == 4
    assert result["created"] >= 4
    assert result["radios"] == 1
    assert result["categories"]["sport"] >= 1
    assert result["playlist"]["channel_count"] == 4
    assert result["epg_urls"] == []


def test_playlist_sync_and_listing(client, user_headers):
    sync = client.post(f"/api/v1/playlists/{_playlist_id(client, user_headers)}/sync", headers=user_headers)
    assert sync.status_code == 200, sync.text
    assert sync.json()["playlist"]["channel_count"] == 4
    playlists = client.get("/api/v1/playlists", headers=user_headers)
    assert playlists.status_code == 200
    assert len(playlists.json()) >= 1


def _playlist_id(client, headers) -> str:
    return client.get("/api/v1/playlists", headers=headers).json()[0]["id"]


def test_channels_search_and_filters(client, user_headers):
    search = client.get("/api/v1/channels?q=bein&page_size=50", headers=user_headers)
    assert search.status_code == 200
    names = [item["name"] for item in search.json()["items"]]
    assert any("beIN" in name for name in names)

    sport = client.get("/api/v1/channels?category=sport&page_size=50", headers=user_headers)
    assert sport.status_code == 200
    assert all(item["category"]["slug"] == "sport" for item in sport.json()["items"])

    arabic = client.get("/api/v1/channels?language=ar&page_size=50", headers=user_headers)
    assert arabic.status_code == 200
    assert all(item["language"]["code"] == "ar" for item in arabic.json()["items"])

    radios = client.get("/api/v1/channels?radio=true&page_size=50", headers=user_headers)
    assert all(item["is_radio"] for item in radios.json()["items"])

    page = client.get("/api/v1/channels?page=1&page_size=2", headers=user_headers)
    body = page.json()
    assert body["page"] == 1 and body["page_size"] == 2 and len(body["items"]) == 2


def test_priority_puts_sport_and_arabic_first(client, user_headers):
    response = client.get("/api/v1/channels?page_size=100", headers=user_headers)
    items = response.json()["items"]
    priorities = [item["priority"] for item in items]
    assert priorities == sorted(priorities, reverse=True)
    top = items[0]
    assert top["category"]["slug"] == "sport" or top["language"]["code"] == "ar"


def test_channel_detail_play_and_keys(client, user_headers):
    channel = client.get("/api/v1/channels?q=beIN%20SPORTS%201&page_size=1", headers=user_headers).json()["items"][0]
    detail = client.get(f"/api/v1/channels/{channel['id']}", headers=user_headers)
    assert detail.status_code == 200
    assert detail.json()["stream_url"].startswith("https://")

    play = client.get(f"/api/v1/channels/{channel['id']}/play", headers=user_headers)
    assert play.status_code == 200
    body = play.json()
    assert body["stream_type"] == "hls"
    assert body["direct_url"].startswith("https://")
    assert "/streams/proxy" in body["url"]

    key = "0123456789abcdef0123456789abcdef"
    kid = "fedcba9876543210fedcba9876543210"
    stored = client.put(
        f"/api/v1/channels/{channel['id']}/keys",
        json={"kid": kid, "key": key},
        headers=user_headers,
    )
    assert stored.status_code == 200, stored.text
    play_again = client.get(f"/api/v1/channels/{channel['id']}/play", headers=user_headers)
    assert play_again.json()["has_keys"] is True
    assert play_again.json()["key_system"] == "clearkey"

    removed = client.delete(f"/api/v1/channels/{channel['id']}/keys/{kid}", headers=user_headers)
    assert removed.status_code == 200


def test_channel_update(client, user_headers):
    channel = client.get("/api/v1/channels?q=Radio%20Soleil&page_size=1", headers=user_headers).json()["items"][0]
    response = client.patch(
        f"/api/v1/channels/{channel['id']}",
        json={"name": "Radio Soleil FM", "category_slug": "music", "language_code": "fr"},
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Radio Soleil FM"
    assert response.json()["category"]["slug"] == "music"


def test_catalog_facets(client, user_headers):
    facets = client.get("/api/v1/catalog/facets", headers=user_headers)
    assert facets.status_code == 200
    body = facets.json()
    assert body["totals"]["channels"] > 0
    assert any(item["slug"] == "sport" for item in body["categories"])
    assert any(item["code"] == "ar" for item in body["languages"])

    quick = client.get("/api/v1/catalog/quick-filters", headers=user_headers)
    assert quick.status_code == 200


def test_favorites_flow(client, user_headers):
    channel = client.get("/api/v1/channels?page_size=1", headers=user_headers).json()["items"][0]
    added = client.post("/api/v1/favorites", json={"channel_id": channel["id"]}, headers=user_headers)
    assert added.status_code == 201, added.text
    duplicate = client.post("/api/v1/favorites", json={"channel_id": channel["id"]}, headers=user_headers)
    assert duplicate.status_code == 201

    listing = client.get("/api/v1/favorites", headers=user_headers)
    assert any(item["channel_id"] == channel["id"] for item in listing.json())

    synced = client.put(
        "/api/v1/favorites/sync", json=[{"channel_id": channel["id"]}], headers=user_headers
    )
    assert synced.status_code == 200
    assert len(synced.json()) == 1

    removed = client.delete(f"/api/v1/favorites/{channel['id']}", headers=user_headers)
    assert removed.status_code == 200


def test_history_flow(client, user_headers):
    channel = client.get("/api/v1/channels?page_size=1", headers=user_headers).json()["items"][0]
    created = client.post(
        "/api/v1/history",
        json={"channel_id": channel["id"], "position_seconds": 42, "duration_seconds": 3600, "device": "web"},
        headers=user_headers,
    )
    assert created.status_code == 201, created.text
    continue_list = client.get("/api/v1/history/continue", headers=user_headers)
    assert continue_list.status_code == 200
    assert continue_list.json()[0]["channel_id"] == channel["id"]
    recent = client.get("/api/v1/history/recent", headers=user_headers)
    assert recent.status_code == 200
    cleared = client.delete("/api/v1/history", headers=user_headers)
    assert cleared.status_code == 200


def test_epg_import_and_now_next(client, user_headers):
    xmltv = """<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="test.sport.1"><display-name>beIN SPORTS 1 HD</display-name></channel>
  <programme start="20200101120000 +0000" stop="20350101140000 +0000" channel="test.sport.1">
    <title>Match en direct</title><desc>Football</desc><category>Sport</category>
  </programme>
</tv>"""
    response = client.post(
        "/api/v1/epg/upload",
        files={"file": ("epg.xml", xmltv.encode("utf-8"), "application/xml")},
        data={"name": "EPG de test"},
        headers=user_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["programmes"] >= 1
    assert body["source"]["name"] == "EPG de test"

    channel = client.get("/api/v1/channels?q=beIN%20SPORTS%201&page_size=1", headers=user_headers).json()["items"][0]
    now_next = client.get(f"/api/v1/channels/{channel['id']}/epg", headers=user_headers)
    assert now_next.status_code == 200
    assert now_next.json()["current"]["title"] == "Match en direct"

    guide = client.get("/api/v1/epg/guide?hours=48", headers=user_headers)
    assert guide.status_code == 200


def test_scan_without_probe(client, user_headers):
    response = client.post("/api/v1/scan", json={"probe": False}, headers=user_headers)
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    job = client.get(f"/api/v1/scan/jobs/{job_id}", headers=user_headers)
    assert job.status_code == 200
    assert job.json()["status"] in {"done", "running"}
    latest = client.get("/api/v1/scan/latest", headers=user_headers)
    assert latest.status_code == 200


def test_provider_crud(client, user_headers):
    created = client.post(
        "/api/v1/providers",
        json={"name": "Mon fournisseur", "kind": "m3u", "notes": "test"},
        headers=user_headers,
    )
    assert created.status_code == 201, created.text
    provider = created.json()
    assert provider["has_password"] is False

    listed = client.get("/api/v1/providers", headers=user_headers)
    assert listed.status_code == 200

    updated = client.patch(
        f"/api/v1/providers/{provider['id']}", json={"name": "Mon fournisseur 2"}, headers=user_headers
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Mon fournisseur 2"

    deleted = client.delete(f"/api/v1/providers/{provider['id']}", headers=user_headers)
    assert deleted.status_code == 200


def test_dashboard_stats(client, user_headers):
    response = client.get("/api/v1/stats/dashboard", headers=user_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["channels"] > 0
    assert body["by_category"]
    assert body["by_language"]
    assert "active_streams" in body

    activity = client.get("/api/v1/stats/activity", headers=user_headers)
    assert activity.status_code == 200


def test_settings(client, user_headers):
    saved = client.put(
        "/api/v1/settings", json={"key": "theme", "value": {"mode": "dark"}}, headers=user_headers
    )
    assert saved.status_code == 200, saved.text
    listed = client.get("/api/v1/settings", headers=user_headers)
    assert any(item["key"] == "theme" for item in listed.json())
    deleted = client.delete("/api/v1/settings/theme", headers=user_headers)
    assert deleted.status_code == 200


def test_proxy_rejects_foreign_host(client, user_headers):
    channel = client.get("/api/v1/channels?page_size=1", headers=user_headers).json()["items"][0]
    response = client.get(
        f"/api/v1/streams/proxy?url=https://evil.example.com/stream.m3u8&channel_id={channel['id']}",
        headers=user_headers,
    )
    assert response.status_code == 403


def test_public_config(client):
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    body = response.json()
    assert body["app_name"] == "PrimeTV"
    assert any(category["slug"] == "sport" for category in body["categories"])


def test_admin_requires_role(client, user_headers):
    response = client.get("/api/v1/admin/users", headers=user_headers)
    assert response.status_code == 403
