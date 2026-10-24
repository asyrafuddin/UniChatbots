"""Simple in-memory rate limiting, so a public website can't use up the free LLM quota.

Two limits: per visitor (requests in the last 60 s, by IP address) and a total per UTC day.
Counts reset when the server restarts — good enough for a student project, not a security wall.
"""

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """Allow at most `per_minute` requests per client per 60 s, and `per_day` requests in total per day."""

    def __init__(self, per_minute: int, per_day: int, clock=time.time):
        self.per_minute = per_minute
        self.per_day = per_day
        self.clock = clock
        self.recent: dict[str, deque[float]] = defaultdict(deque)
        self.day = None
        self.day_count = 0
        self.lock = threading.Lock()

    def check(self, client: str) -> str | None:
        """Record a request; return None if allowed, or a short reason if it should be refused."""
        with self.lock:
            now = self.clock()
            today = time.strftime("%Y-%m-%d", time.gmtime(now))
            if today != self.day:
                self.day, self.day_count = today, 0
            if self.day_count >= self.per_day:
                return "daily limit reached"
            window = self.recent[client]
            while window and now - window[0] >= 60:
                window.popleft()
            if len(window) >= self.per_minute:
                return "too many questions per minute"
            window.append(now)
            self.day_count += 1
            return None


def client_id(headers, fallback: str) -> str:
    """The visitor's IP. Through a Cloudflare tunnel every request comes from localhost, so use
    Cloudflare's CF-Connecting-IP header; behind other proxies, the first X-Forwarded-For entry."""
    forwarded = headers.get("cf-connecting-ip") or headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or fallback
