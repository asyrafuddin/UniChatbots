"""Load raw documents into page records.

A page record is a dict:
    source       file name, e.g. "academic_rules.pdf"
    page_or_url  1-based page number (PDF) or the page's URL (web)
    title        document title (PDF file stem, or the HTML <title>)
    kind         "pdf" or "web"
    text         raw text; paragraphs separated by blank lines,
                 HTML headings marked with HEADING_MARK
"""

import csv
import logging
import re
from collections import Counter
from pathlib import Path

import pymupdf
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

HEADING_MARK = "## "
PDF_SUFFIXES = {".pdf"}
WEB_SUFFIXES = {".html", ".htm", ".txt"}
# a line starting with one of these begins a new paragraph (bullets, "1.", "(2)", "①", "가.")
LIST_MARKER_RE = re.compile(r"^(?:[-–•·▶▷■□○●※*]|\(?\d{1,2}[.)]|[①-⑳]|[가-하][.)])")
TABLE_ROW_START = "| "
Line = tuple[str, pymupdf.Rect, float, bool]  # (text, bounding box, font size, is_table_row)
REMOVE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]
HEADING_TAGS = ["h1", "h2", "h3", "h4"]
BLOCK_TAGS = ["p", "li", "tr", "pre", "blockquote", "div", "section", "article",
              "table", "ul", "ol", "dt", "dd"]


def load_pdfs(pdf_dir: str | Path, cfg: dict) -> list[dict]:
    """Return one record per PDF page, keeping the file name and 1-based page number."""
    records = []
    for path in _files_with_suffix(pdf_dir, PDF_SUFFIXES):
        with pymupdf.open(path) as doc:
            page_lines = [_page_lines(page, cfg["pdf"]["extract_tables"]) for page in doc]
        if not any(page_lines):
            log.warning("%s has no extractable text (scanned PDF? needs OCR) — skipped", path.name)
            continue
        body_size = _body_font_size(page_lines)
        for number, lines in enumerate(page_lines, start=1):
            records.append({"source": path.name, "page_or_url": number, "title": path.stem,
                            "kind": "pdf", "text": _lines_to_text(lines, body_size, cfg)})
    return records


def _page_lines(page: pymupdf.Page, extract_tables: bool) -> list[Line]:
    """Return the page's lines in reading order; tables come back as one '| a | b |' line per row."""
    tables = page.find_tables().tables if extract_tables else []
    table_boxes = [pymupdf.Rect(t.bbox) for t in tables]
    lines = []
    for block in page.get_text("dict", sort=True)["blocks"]:
        if block["type"] != 0:  # 1 = image block
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            box = pymupdf.Rect(line["bbox"])
            centre = pymupdf.Point((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2)
            if spans and not any(centre in t for t in table_boxes):
                text = "".join(s["text"] for s in line["spans"]).strip()
                lines.append((text, box, max(s["size"] for s in spans), False))
    for table in sorted(tables, key=lambda t: t.bbox[1]):
        _insert_table_rows(lines, table, page)
    return lines


def table_row_text(cells: list[str | None]) -> str:
    """Format one table row as '| a | b |', dropping empty/merged cells ('' or None)."""
    values = [" ".join(c.split()) for c in cells if c and c.strip()]
    return f"{TABLE_ROW_START}{' | '.join(values)} |" if values else ""


def _insert_table_rows(lines: list[Line], table: "pymupdf.table.Table", page: pymupdf.Page) -> None:
    """Insert a table's rows into `lines` just before the first text line below the table's top edge.

    Cell text is read with page.get_textbox(cell box) rather than table.extract(),
    which drops the spaces between words ("Late registration" → "Lateregistration").
    """
    top = table.bbox[1]
    at = next((i for i, line in enumerate(lines) if line[1].y0 >= top), len(lines))
    rows = []
    for row in table.rows:
        text = table_row_text([page.get_textbox(pymupdf.Rect(c)) if c else None for c in row.cells])
        if text:
            rows.append((text, pymupdf.Rect(row.bbox), 0.0, True))  # font size unused for rows
    lines[at:at] = rows


def _body_font_size(page_lines: list[list[Line]]) -> float:
    """The document's most common font size (weighted by characters) — the size of normal text."""
    sizes = Counter()
    for lines in page_lines:
        for text, _, size, is_row in lines:
            if not is_row:
                sizes[round(size, 1)] += len(text)
    return sizes.most_common(1)[0][0] if sizes else 0.0


def is_large_heading(text: str, size: float, body_size: float, cfg: dict) -> bool:
    """True if a PDF line is short, doesn't end like a sentence, and is clearly bigger than body text.

    Bullet / list lines ("▶ ...", "- ...") are never headings, even in a large font.
    """
    return (size >= body_size * cfg["pdf"]["heading_size_ratio"]
            and len(text) <= cfg["chunking"]["heading_max_chars"]
            and text[-1] not in ".,;!。"
            and sum(ch.isalpha() for ch in text) >= 2  # "2026" alone is not a heading
            and LIST_MARKER_RE.match(text) is None)


def _starts_new_paragraph(text: str, prev_box: pymupdf.Rect, box: pymupdf.Rect, cfg: dict) -> bool:
    """A line starts a new paragraph after a vertical gap, a jump up/sideways, or a list marker."""
    gap = box.y0 - prev_box.y1
    big_gap = gap > cfg["pdf"]["paragraph_gap_ratio"] * max(box.height, 1.0)
    moved_up = gap < -0.5 * max(box.height, 1.0)  # next column or table cell
    return big_gap or moved_up or LIST_MARKER_RE.match(text) is not None


def _lines_to_text(lines: list[Line], body_size: float, cfg: dict) -> str:
    """Join a page's lines: blank line between paragraphs, HEADING_MARK in front of large headings."""
    parts: list[str] = []
    prev_box, prev_heading, prev_row = None, False, False
    for text, box, size, is_row in lines:
        heading = not is_row and is_large_heading(text, size, body_size, cfg)
        if prev_box is None:
            parts.append(HEADING_MARK + text if heading else text)
        elif heading and prev_heading and not _starts_new_paragraph(text, prev_box, box, cfg):
            parts[-1] += " " + text  # a heading wrapped onto a second line
        elif (heading or prev_heading or is_row or prev_row
              or _starts_new_paragraph(text, prev_box, box, cfg)):
            parts += ["", HEADING_MARK + text if heading else text]  # each table row is its own paragraph
        else:
            parts.append(text)
        prev_box, prev_heading, prev_row = box, heading, is_row
    return "\n".join(parts)


def read_url_map(csv_path: str | Path) -> dict[str, str]:
    """Read the sidecar CSV (columns: filename,url) that maps web files to their URLs."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        log.warning("No URL sidecar at %s — web citations will use file names", csv_path)
        return {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        return {row["filename"].strip(): row["url"].strip()
                for row in csv.DictReader(f) if row.get("filename")}


def load_web(web_dir: str | Path, urls_csv: str | Path) -> list[dict]:
    """Return one record per .html/.htm/.txt file, with its URL looked up in urls.csv."""
    url_map = read_url_map(urls_csv)
    records = []
    for path in _files_with_suffix(web_dir, WEB_SUFFIXES):
        raw = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() == ".txt":
            title, text = path.stem, raw
        else:
            title, text = html_to_text(raw)
        url = url_map.get(path.name)
        if not url:
            log.warning("%s is missing from urls.csv — citing it as local:%s", path.name, path.name)
            url = f"local:{path.name}"
        records.append({"source": path.name, "page_or_url": url, "title": title or path.stem,
                        "kind": "web", "text": text})
    return records


def html_to_text(html: str) -> tuple[str, str]:
    """Convert HTML to (title, text): drop navigation/scripts, mark headings, keep paragraph breaks."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    for tag in soup(REMOVE_TAGS):
        tag.decompose()
    for tag in soup.find_all(HEADING_TAGS):
        tag.replace_with(f"\n\n{HEADING_MARK}{tag.get_text(' ', strip=True)}\n\n")
    for tag in soup.find_all(BLOCK_TAGS):
        tag.insert_after("\n\n")
    for tag in soup.find_all(["td", "th"]):
        tag.insert_after(" ")
    for tag in soup.find_all("br"):
        tag.replace_with("\n")
    body = soup.body or soup
    return title, body.get_text()


def _files_with_suffix(folder: str | Path, suffixes: set[str]) -> list[Path]:
    """List files in a folder whose extension (any case) is in `suffixes`, sorted by name.

    Warns about any other (non-hidden, non-.csv) file, so unsupported formats like .hwp aren't silently ignored.
    """
    folder = Path(folder)
    if not folder.exists():
        log.warning("Folder %s does not exist", folder)
        return []
    files = sorted(p for p in folder.iterdir() if p.is_file() and not p.name.startswith("."))
    for p in files:
        if p.suffix.lower() not in suffixes | {".csv"}:
            log.warning("Unsupported file type, skipped: %s (convert it to %s)",
                        p.name, " / ".join(sorted(suffixes)))
    return [p for p in files if p.suffix.lower() in suffixes]
