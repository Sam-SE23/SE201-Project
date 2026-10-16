from backend.baseline.ctrl_f import CtrlFBaseline, extract_pages


def test_extract_pdf_pages(sample_pdf):
    pages = extract_pages(sample_pdf)
    assert [p.location for p in pages] == ["p.1", "p.2"]
    assert "checkpoint" in pages[1].text


def test_extract_pptx_slides(sample_pptx):
    pages = extract_pages(sample_pptx)
    assert [p.location for p in pages] == ["slide 1", "slide 2"]
    assert "Hallucination" in pages[1].text


def test_search_is_case_insensitive_and_finds_every_occurrence(sample_pdf, sample_pptx):
    base = CtrlFBaseline()
    base.index([sample_pdf, sample_pptx])
    hits = base.search("CHECKPOINT")
    assert {(h.source_file, h.location) for h in hits} == {("syllabus.pdf", "p.2")}
    assert len(hits) == 2
    assert all("checkpoint" in h.snippet.lower() for h in hits)


def test_search_needs_exact_wording(sample_pdf):
    base = CtrlFBaseline()
    base.index([sample_pdf])
    assert base.search("When is the checkpoint due?") == []
    assert base.search("   ") == []


def test_reindexing_a_file_does_not_duplicate_hits(sample_pdf):
    base = CtrlFBaseline()
    base.index([sample_pdf])
    base.index([sample_pdf])
    assert len(base.search("proposal")) == 2
