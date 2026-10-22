from src.ingest.clean import clean_records, normalize_whitespace
from src.ingest.fake_data import FOOTER, HEADER
from src.ingest.loaders import load_pdfs


def test_headers_footers_and_page_numbers_removed(fake_raw_dir, cfg):
    cleaned, patterns = clean_records(load_pdfs(fake_raw_dir / "pdfs", cfg), cfg)
    assert len(patterns["fake_regulations.pdf"]) == 3
    for page in cleaned:
        assert HEADER not in page["text"]
        assert FOOTER not in page["text"]
        assert "Page " not in page["text"]
    assert "Course Registration" in cleaned[0]["text"]  # body text survives


def test_short_documents_are_not_searched_for_repeats(cfg):
    pages = [{"source": "a.pdf", "text": "Same line\n\nBody one"},
             {"source": "a.pdf", "text": "Same line\n\nBody two"}]
    cleaned, patterns = clean_records(pages, cfg)  # 2 pages < min_pages_for_repeats
    assert patterns == {}
    assert cleaned[0]["text"].startswith("Same line")


def test_normalize_whitespace():
    assert normalize_whitespace("  a \t b c \n\n\n\n d ") == "a b c\n\nd"


def test_contents_page_is_dropped(cfg):
    toc = "\n".join(f"{i}. Chapter {i} ---------------- {i * 3}" for i in range(1, 7))
    pages = [{"source": "a.pdf", "text": toc}, {"source": "a.pdf", "text": "Real content."}]
    cleaned, _ = clean_records(pages, cfg)
    assert [p["text"] for p in cleaned] == ["", "Real content."]


def test_separator_lines_and_repeated_paragraphs_removed(cfg):
    text = "## Online Registration\n\nOnline Registration\n\n-----------\n\nRegister online.\n\n| 3개 |\n\n| 3개 |"
    (page,), _ = clean_records([{"source": "a.pdf", "text": text}], cfg)
    assert page["text"] == "## Online Registration\n\nRegister online.\n\n| 3개 |\n\n| 3개 |"


def test_control_characters_become_spaces():
    assert normalize_whitespace("전형별\x01 모집인원") == "전형별 모집인원"
