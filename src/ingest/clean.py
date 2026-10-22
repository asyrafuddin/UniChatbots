"""Clean page text: drop repeated headers/footers, page numbers, contents pages,
separator lines, paragraphs repeated on the same page, and extra whitespace."""

import re
from collections import Counter, defaultdict

from src.ingest.loaders import HEADING_MARK, TABLE_ROW_START

# "12", "- 12 -", "Page 3", "Page 3 of 10", "3/10", "Halaman 3 daripada 10", "iv"
PAGE_NUMBER_RE = re.compile(
    r"^(?:page|halaman|hlm\.?|ms\.?|muka surat|p\.)?\s*[-–—]?\s*(?:\d{1,4}|[ivx]{1,5})\s*"
    r"(?:(?:of|/|daripada|dari)\s*\d{1,4})?\s*[-–—]?$",
    re.IGNORECASE,
)
INVISIBLE_CHARS = dict.fromkeys(map(ord, "­​‌‍﻿"), None)
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")  # some PDF fonts emit \x01 instead of a space
LEADER_RE = re.compile(r"-{5,}|\.{5,}|·{5,}|…{3,}|_{5,}|ㆍ{5,}")  # "1. Visa ---------- 3"
SEPARATOR_LINE_RE = re.compile(r"^[\s\-–—.·…_=ㆍ*~]{5,}$")       # a line that is only dashes/dots


def normalize_line(line: str) -> str:
    """Normalise a line for header/footer matching: lowercase, digits → '#', single spaces."""
    line = re.sub(r"\d+", "#", CONTROL_CHARS_RE.sub(" ", line).strip().lower())
    return re.sub(r"\s+", " ", line)


def edge_line_indices(lines: list[str], n_edge: int) -> set[int]:
    """Return indices of the first and last `n_edge` non-empty lines (where headers/footers live)."""
    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    return set(nonempty[:n_edge] + nonempty[-n_edge:])


def find_repeated_lines(page_texts: list[str], repeat_ratio: float, n_edge: int,
                        min_pages: int) -> set[str]:
    """Return normalised edge lines that appear on at least `repeat_ratio` of a document's pages."""
    if len(page_texts) < min_pages:
        return set()
    counts = Counter()
    for text in page_texts:
        lines = text.split("\n")
        counts.update({normalize_line(lines[i]) for i in edge_line_indices(lines, n_edge)})
    threshold = repeat_ratio * len(page_texts)
    return {line for line, count in counts.items() if line and count >= threshold}


def clean_page(text: str, repeated: set[str], c: dict) -> str:
    """Clean one page (c = the `cleaning` settings). A table-of-contents page becomes ''."""
    if is_contents_page(text, c["toc_min_leader_lines"]):
        return ""
    lines = text.split("\n")
    edges = edge_line_indices(lines, c["edge_lines"])
    kept = [line for i, line in enumerate(lines)
            if not (i in edges and _is_header_footer(line, repeated))
            and not SEPARATOR_LINE_RE.match(line)]
    return normalize_whitespace(drop_repeated_paragraphs("\n".join(kept)))


def is_contents_page(text: str, min_leader_lines: int) -> bool:
    """True if the page has many '------' / '......' leader lines, i.e. it's a table of contents."""
    return sum(bool(LEADER_RE.search(line)) for line in text.split("\n")) >= min_leader_lines


def drop_repeated_paragraphs(text: str) -> str:
    """Keep only the first copy of a paragraph that appears again on the same page (e.g. menu text).

    Table rows and very short paragraphs are left alone — they can legitimately repeat.
    """
    seen: set[str] = set()
    kept = []
    for paragraph in re.split(r"\n\s*\n", text):
        key = " ".join(paragraph.removeprefix(HEADING_MARK).split()).lower()
        if len(key) >= 6 and not paragraph.startswith(TABLE_ROW_START):
            if key in seen:
                continue
            seen.add(key)
        kept.append(paragraph)
    return "\n\n".join(kept)


def _is_header_footer(line: str, repeated: set[str]) -> bool:
    """True if a line is a known repeated header/footer or looks like a bare page number."""
    stripped = line.strip()
    return bool(stripped) and (normalize_line(stripped) in repeated
                               or PAGE_NUMBER_RE.match(stripped) is not None)


def normalize_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs, strip each line, and keep at most one blank line in a row."""
    text = text.translate(INVISIBLE_CHARS).replace(" ", " ").replace("\r", "")
    text = CONTROL_CHARS_RE.sub(" ", text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def clean_records(records: list[dict], cfg: dict) -> tuple[list[dict], dict[str, set[str]]]:
    """Clean every page record, detecting headers/footers separately for each document.

    Returns the cleaned records (same order) and, per source, the header/footer
    patterns that were removed — handy for checking the cleaner didn't over-delete.
    """
    c = cfg["cleaning"]
    by_source = defaultdict(list)
    for record in records:
        by_source[record["source"]].append(record)

    repeated_by_source = {
        source: find_repeated_lines([p["text"] for p in pages], c["repeat_ratio"],
                                    c["edge_lines"], c["min_pages_for_repeats"])
        for source, pages in by_source.items()
    }
    cleaned = [{**r, "text": clean_page(r["text"], repeated_by_source[r["source"]], c)}
               for r in records]
    return cleaned, {s: p for s, p in repeated_by_source.items() if p}
