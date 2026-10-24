#!/usr/bin/env bash
# Start the backend AND the Cloudflare tunnel together, so the Vercel site can reach this Mac.
# Usage (from anywhere):  ~/UniChatbots/scripts/start_public.sh      Stop both with Ctrl+C.
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate

uvicorn src.api.main:app --port 8000 &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null' EXIT

echo "Loading the models (~30 s)…"
until curl -s localhost:8000/api/health >/dev/null; do
  kill -0 $BACKEND 2>/dev/null || { echo "The backend failed to start — see the error above."; exit 1; }
  sleep 2
done

python -m src.api.tunnel   # keeps running; Ctrl+C stops the tunnel, then the trap stops the backend
