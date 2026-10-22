"""Split cleaned pages into token-limited chunks that follow the document's structure.

Order of splitting: section headings → paragraphs → sentences → (last resort) words.
PDF chunks never cross a page boundary, so every chunk cites exactly one page.
The current section heading carries over from one page to the next, and the
heading line itself stays in the text of the chunk that starts the section.
"""

import re
from collections.abc import Callable
from itertools import groupby

from src.ingest.loaders import HEADING_MARK

TokenCounter = Callable[[str], int]

# "1. Fees", "2.1 Tuition", "IV. Rules", "Ⅱ. 학사", "(3) 연체 및 분실", "3) 문의", "제1조(목적)", "Chapter 2"
NUMBERED_HEADING_RE = re.compile(
    r"^(?:(?:\d{1,2}\.(?:\d{1,2}\.?)*|\d{1,2}(?:\.\d{1,2})+|[IVX]{1,4}\.|[Ⅰ-Ⅻ]{1,3}\.?|\(\d{1,2}\)|\d{1,2}\)"
    r"|(?i:chapter|section|part|bab|bahagian)\s+[\dIVX]+[.:]?)\s+|제\s?\d{1,3}\s?[조장절관]\s*)\S"
)
# a boundary is ". " + capital/digit/Hangul (English, Malay, Korean), or after 。！？ (Chinese)
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'“‘(\[]?[A-Z0-9가-힣])|(?<=[。！？])\s*(?=\S)")
ABBREVIATIONS = {"dr", "prof", "mr", "mrs", "ms", "no", "nos", "e.g", "i.e", "vs", "sdn", "bhd",
                 "st", "hj", "bil", "cf", "approx", "dept", "fig", "jan", "feb", "mar", "apr",
                 "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"}


# ---------- structure ----------

def split_paragraphs(text: str) -> list[str]:
    """Split on blank lines; join a paragraph's wrapped lines with single spaces."""
    return [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def is_heading(paragraph: str, max_chars: int) -> bool:
    """A heading is either marked by the loader (HTML tag / large PDF font) or a short numbered line.

    Works for any language because it doesn't rely on capital letters. A numbered line
    with a colon inside ("3) 문의: 031-...") or a sentence ending is treated as content.
    """
    if paragraph.startswith(HEADING_MARK):
        return True
    if len(paragraph) > max_chars or paragraph[-1] in ".,;!。" or re.search(r"[:：].", paragraph):
        return False
    return NUMBERED_HEADING_RE.match(paragraph) is not None


def group_by_section(paragraphs: list[str], section: str, max_chars: int) -> tuple[list[tuple[str, list[str]]], str]:
    """Group paragraphs under the heading they follow; the heading is the group's first paragraph.

    Returns ([(section, [paragraphs]), ...], last_section) so the caller can
    carry the heading over to the next page.
    """
    groups: list[tuple[str, list[str]]] = []
    for paragraph in paragraphs:
        if is_heading(paragraph, max_chars):
            section = paragraph.removeprefix(HEADING_MARK).strip()
            groups.append((section, [section]))
        elif groups and groups[-1][0] == section:
            groups[-1][1].append(paragraph)
        else:
            groups.append((section, [paragraph]))
    return groups, section


def merge_small_groups(groups: list[tuple[str, list[str]]], min_tokens: int,
                       count: TokenCounter) -> list[tuple[str, list[str]]]:
    """Merge sections smaller than min_tokens (lone headings, table scraps) into the next section.

    A small section at the very end of the page is merged into the previous one instead.
    """
    merged: list[tuple[str, list[str]]] = []
    carry: list[str] = []
    carry_section = ""
    for section, paragraphs in groups:
        paragraphs = carry + paragraphs
        carry_section = carry_section if carry else section
        if count("\n\n".join(paragraphs)) < min_tokens:
            carry = paragraphs
            continue
        merged.append((section, paragraphs))
        carry = []
    if carry and merged:
        merged[-1][1].extend(carry)
    elif carry:
        merged.append((carry_section, carry))
    return merged


# ---------- sentences & units ----------

def split_sentences(text: str) -> list[str]:
    """Split text into sentences, without breaking after abbreviations like 'Dr.' or 'No.'."""
    sentences: list[str] = []
    for piece in SENTENCE_BOUNDARY_RE.split(text):
        if sentences and _ends_with_abbreviation(sentences[-1]):
            sentences[-1] += " " + piece
        else:
            sentences.append(piece)
    return sentences


def _ends_with_abbreviation(sentence: str) -> bool:
    """True if the sentence's last word (without its final dot) is a known abbreviation."""
    last_word = sentence.rsplit(None, 1)[-1].rstrip(".").lower()
    return last_word in ABBREVIATIONS


def split_by_words(text: str, max_tokens: int, count: TokenCounter) -> list[str]:
    """Last resort for a single over-long sentence: cut it into word runs of <= max_tokens."""
    pieces, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and count(candidate) > max_tokens:
            pieces.append(current)
            current = word
        else:
            current = candidate
    return pieces + [current] if current else pieces


def paragraph_units(paragraph: str, max_tokens: int, count: TokenCounter) -> list[tuple[str, bool]]:
    """Break a paragraph into pieces that each fit in max_tokens.

    Returns (text, starts_new_paragraph) pairs: the whole paragraph if it fits,
    otherwise its sentences (with over-long sentences split by words).
    """
    if count(paragraph) <= max_tokens:
        return [(paragraph, True)]
    pieces = []
    for sentence in split_sentences(paragraph):
        pieces.extend([sentence] if count(sentence) <= max_tokens
                      else split_by_words(sentence, max_tokens, count))
    return [(piece, i == 0) for i, piece in enumerate(pieces)]


# ---------- packing ----------

def overlap_tail(text: str, overlap_tokens: int, count: TokenCounter) -> str:
    """Return the last whole sentences of `text` that together fit in overlap_tokens (may be '')."""
    sentences = [s for p in split_paragraphs(text) for s in split_sentences(p)]
    tail: list[str] = []
    for sentence in reversed(sentences):
        if count(" ".join([sentence] + tail)) > overlap_tokens:
            break
        tail.insert(0, sentence)
    return " ".join(tail)


def pack_units(units: list[tuple[str, bool]], max_tokens: int, overlap_tokens: int,
               count: TokenCounter) -> list[str]:
    """Greedily pack units into chunks of <= max_tokens, starting each new chunk with a sentence overlap."""
    chunks: list[str] = []
    current = ""
    for text, new_paragraph in units:
        sep = "\n\n" if new_paragraph else " "
        if not current or count(current + sep + text) <= max_tokens:
            current = current + sep + text if current else text
            continue
        chunks.append(current)
        tail = overlap_tail(current, overlap_tokens, count)
        with_tail = tail + sep + text
        current = with_tail if tail and count(with_tail) <= max_tokens else text
    if current:
        chunks.append(current)
    return chunks


# ---------- documents ----------

def chunk_document(pages: list[dict], cfg: dict, count: TokenCounter) -> list[dict]:
    """Chunk one document's page records (in page order) into chunk dicts."""
    c = cfg["chunking"]
    max_tokens = c["max_tokens"]
    overlap_tokens = int(max_tokens * c["overlap_ratio"])
    section = pages[0]["title"]
    doc_slug = re.sub(r"[^a-z0-9]+", "-", pages[0]["source"].lower()).strip("-")
    chunks: list[dict] = []

    for page in pages:
        groups, section = group_by_section(split_paragraphs(page["text"]), section,
                                           c["heading_max_chars"])
        for group_section, paragraphs in merge_small_groups(groups, c["min_chunk_tokens"], count):
            units = [u for p in paragraphs for u in paragraph_units(p, max_tokens, count)]
            for text in pack_units(units, max_tokens, overlap_tokens, count):
                location = f"p{page['page_or_url']}" if page["kind"] == "pdf" else "web"
                chunks.append({
                    "id": f"{doc_slug}-{location}-{len(chunks):03d}",
                    "text": text,
                    "source": page["source"],
                    "page_or_url": page["page_or_url"],
                    "section": group_section,
                })
    return chunks


def chunk_records(records: list[dict], cfg: dict, count: TokenCounter) -> list[dict]:
    """Chunk all cleaned page records, one document (source) at a time."""
    chunks = []
    for _, pages in groupby(records, key=lambda r: r["source"]):
        chunks.extend(chunk_document(list(pages), cfg, count))
    return chunks
