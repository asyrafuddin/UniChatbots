"""Tunnel address parsing and publishing (no cloudflared or Supabase needed)."""

from src.api.tunnel import find_tunnel_url, publish_url
from tests.test_supabase_store import FakeClient


def test_find_tunnel_url_in_cloudflared_log():
    line = "2026-10-23T15:00:01Z INF |  https://brave-lion-sun-moon.trycloudflare.com                |"
    assert find_tunnel_url(line) == "https://brave-lion-sun-moon.trycloudflare.com"
    assert find_tunnel_url("INF Requesting new quick Tunnel on trycloudflare.com...") is None


def test_publish_and_remove_url(cfg):
    client = FakeClient()
    publish_url(client, cfg, "https://x.trycloudflare.com")
    publish_url(client, cfg, None)
    calls = [(name, args) for name, args in client.log]
    assert calls[0][0] == "upsert" and calls[0][1][0]["value"] == "https://x.trycloudflare.com"
    assert ("delete", ()) in calls
