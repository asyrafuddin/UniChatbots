"""Remove duplicate chunks (same text after normalising case and whitespace)."""

import hashlib
import re


def text_fingerprint(text: str) -> str:
    """Hash of the text after lowercasing and collapsing whitespace."""
    normalised = re.sub(r"\s+", " ", text.lower()).strip()
    return hashlib.sha1(normalised.encode("utf-8")).hexdigest()


def dedupe_chunks(chunks: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep the first occurrence of each chunk text. Returns (kept, removed)."""
    seen: set[str] = set()
    kept, removed = [], []
    for chunk in chunks:
        fingerprint = text_fingerprint(chunk["text"])
        (removed if fingerprint in seen else kept).append(chunk)
        seen.add(fingerprint)
    return kept, removed
