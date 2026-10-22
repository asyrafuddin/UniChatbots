import logging

from src.ingest.fake_data import TITLE
from src.ingest.loaders import HEADING_MARK, html_to_text, load_pdfs, load_web, table_row_text


def test_load_pdfs_keeps_file_name_and_page_numbers(fake_raw_dir, cfg):
    pages = load_pdfs(fake_raw_dir / "pdfs", cfg)
    assert [p["page_or_url"] for p in pages] == [1, 2, 3]
    assert {p["source"] for p in pages} == {"fake_regulations.pdf"}
    assert "Course Registration" in pages[0]["text"]


def test_large_font_line_is_marked_as_heading(fake_raw_dir, cfg):
    first_page = load_pdfs(fake_raw_dir / "pdfs", cfg)[0]["text"]
    assert f"{HEADING_MARK}{TITLE}" in first_page
    assert f"{HEADING_MARK}1. Course Registration" not in first_page  # same size as body text


def test_wrapped_lines_stay_in_one_paragraph(fake_raw_dir, cfg):
    first_page = load_pdfs(fake_raw_dir / "pdfs", cfg)[0]["text"]
    paragraphs = first_page.split("\n\n")
    assert any(p.startswith("Students must register") and "approves all late registrations." in p
               for p in paragraphs)


def test_tables_become_one_row_per_paragraph(fake_raw_dir, cfg):
    first_page = load_pdfs(fake_raw_dir / "pdfs", cfg)[0]["text"]
    paragraphs = first_page.split("\n\n")
    assert "| Late registration | 50 | Week 2 |" in paragraphs
    assert first_page.count("Transcript") == 1  # cell text isn't also left as loose lines


def test_table_row_text_drops_empty_cells():
    assert table_row_text(["대학원생", None, "", " 20책 ", "30일"]) == "| 대학원생 | 20책 | 30일 |"
    assert table_row_text([None, "", "  "]) == ""


def test_unsupported_files_are_reported(tmp_path, cfg, caplog):
    (tmp_path / "rules.hwp").write_bytes(b"not a pdf")
    with caplog.at_level(logging.WARNING):
        assert load_pdfs(tmp_path, cfg) == []
    assert "rules.hwp" in caplog.text


def test_load_web_uses_urls_csv(fake_raw_dir):
    docs = {d["source"]: d for d in load_web(fake_raw_dir / "web", fake_raw_dir / "web" / "urls.csv")}
    assert docs["library_hours.html"]["page_or_url"] == "https://example.edu.my/library/hours"
    assert docs["portal_notice.txt"]["page_or_url"] == "https://example.edu.my/notices/portal"


def test_web_file_missing_from_csv_gets_local_fallback(tmp_path):
    (tmp_path / "orphan.txt").write_text("Hello", encoding="utf-8")
    (docs,) = load_web(tmp_path, tmp_path / "urls.csv")
    assert docs["page_or_url"] == "local:orphan.txt"


def test_html_to_text_drops_nav_and_marks_headings():
    title, text = html_to_text("<title>T</title><nav>Menu</nav><h2>Fees</h2><p>Pay RM100.</p>")
    assert title == "T"
    assert "Menu" not in text
    assert f"{HEADING_MARK}Fees" in text
    assert "Pay RM100." in text
