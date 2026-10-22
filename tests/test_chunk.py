from src.ingest.chunk import (chunk_records, is_heading, merge_small_groups, pack_units,
                              paragraph_units, split_sentences)
from src.ingest.clean import clean_records
from src.ingest.fake_data import TITLE
from src.ingest.loaders import load_pdfs


def _pdf_chunks(fake_raw_dir, cfg, count):
    cleaned, _ = clean_records(load_pdfs(fake_raw_dir / "pdfs", cfg), cfg)
    return chunk_records(cleaned, cfg, count)


def test_is_heading():
    for heading in ["2. Repeating a Course / Mengulang Kursus", "6. 장소변경", "(3) 연체 및 분실",
                    "제1조(목적)", "1.1 选课时间", "## anything marked by the loader"]:
        assert is_heading(heading, 60), heading
    for content in ["Students must register before week 1.", "Fees and Payment",
                    "3) 문의: 031-400-4918", "2026. 01. 12.(월)", "10 days before registration"]:
        assert not is_heading(content, 60), content


def test_split_sentences_respects_abbreviations():
    assert split_sentences("See Dr. Aminah first. Then pay. Bayar sekarang!") == [
        "See Dr. Aminah first.", "Then pay.", "Bayar sekarang!"]


def test_split_sentences_korean_and_chinese():
    assert split_sentences("등록금을 납부한다. 기한은 4주이다.") == ["등록금을 납부한다.", "기한은 4주이다."]
    assert split_sentences("请按时缴费。逾期将罚款！") == ["请按时缴费。", "逾期将罚款！"]


def test_small_sections_merge_into_next(count):
    groups = [("Title", ["Title"]), ("1. Fees", ["1. Fees", "Tuition must be paid before week 4 " * 5])]
    merged = merge_small_groups(groups, 30, count)
    assert merged == [("1. Fees", ["Title", "1. Fees", "Tuition must be paid before week 4 " * 5])]


def test_chunks_respect_max_tokens(fake_raw_dir, small_cfg, count):
    chunks = _pdf_chunks(fake_raw_dir, small_cfg, count)
    assert len(chunks) > 10
    assert all(count(c["text"]) <= small_cfg["chunking"]["max_tokens"] for c in chunks)


def test_section_and_page_kept_and_carried_across_pages(fake_raw_dir, cfg, count):
    chunks = _pdf_chunks(fake_raw_dir, cfg, count)
    page3 = [c for c in chunks if c["page_or_url"] == 3]
    assert page3[0]["section"] == "2. Repeating a Course / Mengulang Kursus"  # carried over
    assert page3[-1]["section"] == "3. Fees and Payment"
    assert page3[-1]["text"].startswith("3. Fees and Payment")  # heading kept in the text
    assert len({c["id"] for c in chunks}) == len(chunks)


def test_lone_title_is_not_its_own_chunk(fake_raw_dir, cfg, count):
    chunks = _pdf_chunks(fake_raw_dir, cfg, count)
    assert all(c["text"] != TITLE for c in chunks)
    assert chunks[0]["text"].startswith(TITLE)


def test_consecutive_chunks_overlap(count):
    paragraph = " ".join(f"Sentence number {i} is about course rules." for i in range(30))
    chunks = pack_units(paragraph_units(paragraph, 60, count), 60, 15, count)
    assert len(chunks) > 2
    for prev, nxt in zip(chunks, chunks[1:]):
        last_sentence = split_sentences(prev)[-1]
        assert nxt.startswith(last_sentence)


def test_doc_slug_keeps_korean_so_files_stay_distinct():
    import unicodedata

    from src.ingest.chunk import doc_slug

    a, b = "국제교류(ERICA) - 한양대학교.pdf", "국제교육원 안내 – ERICA 국제교육원.pdf"
    assert doc_slug(a) != doc_slug(b)
    assert doc_slug(a) == "국제교류-erica-한양대학교-pdf"
    assert doc_slug(unicodedata.normalize("NFD", a)) == doc_slug(a)  # macOS-style filename
