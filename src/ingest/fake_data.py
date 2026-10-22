"""Generate a small FAKE university corpus (1 PDF + 3 web pages) for tests and dry runs.

Everything here is invented. Usage:
    python -m src.ingest.fake_data data/sample_raw
"""

import sys
from pathlib import Path

import pymupdf

HEADER = "Universiti Contoh Malaysia - Academic Regulations 2026"
TITLE = "Academic Regulations Handbook"  # printed in a large font on page 1
FOOTER = "Office of the Registrar | Fake document for testing"
DUPLICATE_NOTICE = ("The student portal will be closed for maintenance on 1 March 2026 "
                    "from 10 pm to 2 am. Sistem portal pelajar akan ditutup sementara.")

FEE_TABLE = [["Item", "Fee (RM)", "Due"],
             ["Late registration", "50", "Week 2"],
             ["Transcript", "10", "Any time"]]  # drawn as a grid table on page 1

_REPEAT_RULES = [
    "A student who fails a course may repeat it in the following semester.",
    "Pelajar yang gagal sesuatu kursus boleh mengulang kursus tersebut pada semester berikutnya.",
    "A course may be repeated at most two times, and the highest grade is used for the CGPA.",
    "Kursus yang diulang akan dikenakan yuran penuh mengikut kadar semasa.",
    "Students on academic probation must meet their advisor before re-registering.",
]


def _repeat_paragraph(i: int) -> str:
    """Build the i-th (made-up) paragraph of the long 'repeating a course' section."""
    rules = " ".join(_REPEAT_RULES[(i + k) % len(_REPEAT_RULES)] for k in range(3))
    return f"Rule 2.{i}: {rules}"


PAGES = [
    ["1. Course Registration",
     "Students must register for courses through the student portal before the end of week 1. "
     "Dr. Aminah Yusof, Dean of Students, approves all late registrations.",
     "Late registration is allowed until week 2 with a penalty of RM50. "
     "Pendaftaran lewat dikenakan denda RM50."],
    ["2. Repeating a Course / Mengulang Kursus"] + [_repeat_paragraph(i) for i in range(1, 9)],
    [_repeat_paragraph(i) for i in range(9, 13)]
    + ["3. Fees and Payment",
       "Tuition fees must be paid before week 4 of each semester. Yuran pengajian mesti dibayar "
       "sebelum minggu keempat."],
]

WEB_PAGES = {
    "library_hours.html": ("https://example.edu.my/library/hours", """<html><head><title>Library Opening Hours</title></head>
<body><nav>Home | About | Contact</nav>
<h1>Library Opening Hours</h1>
<p>The main library opens from 8 am to 10 pm on weekdays and 9 am to 5 pm on weekends.</p>
<h2>Portal Maintenance</h2>
<p>""" + DUPLICATE_NOTICE + """</p>
<footer>Copyright 2026 Universiti Contoh</footer></body></html>"""),
    "biasiswa.html": ("https://example.edu.my/biasiswa", """<html><head><title>Biasiswa Pelajar</title></head>
<body><h1>Biasiswa Pelajar</h1>
<p>Pelajar dengan CGPA 3.50 ke atas layak memohon Biasiswa Dekan.<br>Permohonan dibuka pada bulan Januari.</p>
<ul><li>Salinan transkrip</li><li>Surat sokongan pensyarah</li></ul></body></html>"""),
    "portal_notice.txt": ("https://example.edu.my/notices/portal",
                          "## Portal Maintenance\n\n" + DUPLICATE_NOTICE + "\n"),
}


def make_fake_pdf(path: str | Path) -> Path:
    """Write a 3-page fake regulations PDF with a repeated header, footer and page numbers."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for number, paragraphs in enumerate(PAGES, start=1):
        page = doc.new_page()  # A4-ish: 595 x 842 pt
        page.insert_text((50, 40), HEADER, fontsize=8)
        y = 70.0
        sized = [(TITLE, 14)] * (number == 1) + [(text, 9) for text in paragraphs]
        for text, fontsize in sized:
            box = pymupdf.Rect(50, y, 545, 780)
            spare = page.insert_textbox(box, text, fontsize=fontsize)
            if spare < 0:
                raise ValueError(f"Fake PDF page {number} overflows; shorten its text")
            y = box.y1 - spare + 10
        if number == 1:
            _draw_table(page, y + 10, FEE_TABLE)
        page.insert_text((50, 805), FOOTER, fontsize=8)
        page.insert_text((280, 822), f"Page {number} of {len(PAGES)}", fontsize=8)
    doc.save(path)
    doc.close()
    return path


def _draw_table(page: pymupdf.Page, top: float, rows: list[list[str]],
                col_width: float = 120, row_height: float = 18) -> None:
    """Draw a simple ruled table (grid lines + cell text) starting at y=top."""
    for r, row in enumerate(rows):
        for col, cell in enumerate(row):
            cell_box = pymupdf.Rect(50 + col * col_width, top + r * row_height,
                                    50 + (col + 1) * col_width, top + (r + 1) * row_height)
            page.draw_rect(cell_box, width=0.5)
            page.insert_text((cell_box.x0 + 4, cell_box.y1 - 5), cell, fontsize=9)


def make_fake_web(web_dir: str | Path) -> Path:
    """Write the fake web pages plus their urls.csv sidecar into `web_dir`."""
    web_dir = Path(web_dir)
    web_dir.mkdir(parents=True, exist_ok=True)
    rows = ["filename,url"]
    for name, (url, content) in WEB_PAGES.items():
        (web_dir / name).write_text(content, encoding="utf-8")
        rows.append(f"{name},{url}")
    (web_dir / "urls.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return web_dir


def make_fake_corpus(raw_dir: str | Path) -> Path:
    """Create raw_dir/pdfs/fake_regulations.pdf and raw_dir/web/* (same layout as data/raw)."""
    raw_dir = Path(raw_dir)
    make_fake_pdf(raw_dir / "pdfs" / "fake_regulations.pdf")
    make_fake_web(raw_dir / "web")
    return raw_dir


if __name__ == "__main__":
    target = make_fake_corpus(sys.argv[1] if len(sys.argv) > 1 else "data/sample_raw")
    print(f"Fake corpus written to {target}")
