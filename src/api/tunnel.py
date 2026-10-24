"""Put the local backend on the internet with a free Cloudflare quick tunnel.

A quick tunnel needs no account but gets a new random https://….trycloudflare.com address each
start, so this script saves the address in Supabase (public_config table). The website reads it
from there, so you never have to change Vercel settings. Stop with Ctrl+C (the address is removed).

Usage (from the project root, with the .venv active, while the backend runs in another terminal):
    python -m src.api.tunnel
"""

import re
import subprocess
import time
import urllib.request
from datetime import datetime, timezone

from src.config import load_config
from src.retrieve.supabase_store import get_supabase

URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def find_tunnel_url(line: str) -> str | None:
    """The public address in a line of cloudflared's log output, if there is one."""
    match = URL_PATTERN.search(line)
    return match.group(0) if match else None


def backend_is_up(local_url: str) -> bool:
    """True if the local backend answers its health check."""
    try:
        with urllib.request.urlopen(f"{local_url}/api/health", timeout=5) as res:
            return res.status == 200
    except OSError:
        return False


def publish_url(client, cfg: dict, url: str | None) -> None:
    """Save the tunnel address for the website, or delete it (url=None) so the site shows "offline"."""
    s = cfg["supabase"]
    table = client.table(s["public_config_table"])
    if url is None:
        table.delete().eq("key", s["api_url_key"]).execute()
    else:
        table.upsert({"key": s["api_url_key"], "value": url,
                      "updated_at": datetime.now(timezone.utc).isoformat()}).execute()


def main() -> None:
    """Start cloudflared, publish its address, and keep running until Ctrl+C."""
    cfg = load_config()
    t = cfg["tunnel"]
    if not backend_is_up(t["local_url"]):
        print(f"Warning: no backend at {t['local_url']} yet — start it with: uvicorn src.api.main:app --port 8000")
    client = get_supabase()
    proc = subprocess.Popen(["cloudflared", "tunnel", "--no-autoupdate", "--url", t["local_url"]],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        deadline, url = time.monotonic() + t["url_timeout_s"], None
        for line in proc.stdout:
            url = find_tunnel_url(line)
            if url or time.monotonic() > deadline:
                break
        if not url:
            raise RuntimeError("cloudflared didn't report a tunnel address — check your internet connection")
        publish_url(client, cfg, url)
        print(f"Backend is public at {url}  (saved to Supabase; the website will find it)")
        print("Keep this terminal open. Press Ctrl+C to stop.")
        proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        publish_url(client, cfg, None)
        print("\nTunnel stopped; address removed from Supabase.")


if __name__ == "__main__":
    main()
