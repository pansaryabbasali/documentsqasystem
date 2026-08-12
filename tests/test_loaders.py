"""Loader contract and PDF extraction tests (offline; run against the committed dataset)."""

from pathlib import Path

import pytest

from doc_qa.errors import UnsupportedFormatError
from doc_qa.loaders import DocumentLoader, PdfLoader, TextBlock, loader_for

DATASET = Path(__file__).resolve().parent.parent / "dataset"
WARRANTY_PDF = DATASET / "policies" / "Warranty_and_Service_Policy.pdf"
TROUBLESHOOTING_PDF = DATASET / "product_manuals" / "AF-4500_Troubleshooting_Guide.pdf"


def test_loader_for_dispatches_pdf() -> None:
    assert isinstance(loader_for(WARRANTY_PDF), PdfLoader)


def test_loader_for_rejects_unknown_format() -> None:
    with pytest.raises(UnsupportedFormatError, match="xlsx"):
        loader_for(Path("Financials.xlsx"))


def test_all_registered_loaders_satisfy_protocol() -> None:
    for suffix in (".pdf", ".docx", ".pptx", ".csv", ".txt"):
        assert isinstance(loader_for(Path(f"any{suffix}")), DocumentLoader)


def test_pdf_loader_satisfies_protocol() -> None:
    assert isinstance(PdfLoader(), DocumentLoader)


def test_pdf_extraction_yields_paged_blocks() -> None:
    blocks = list(PdfLoader().load(WARRANTY_PDF))
    assert blocks, "no text extracted from a text-native PDF"
    assert all(isinstance(b, TextBlock) for b in blocks)
    assert all(b.source == "Warranty_and_Service_Policy.pdf" for b in blocks)
    assert all(b.text.strip() for b in blocks)
    assert blocks[0].locator == "page 1"
    pages = [int(b.locator.removeprefix("page ")) for b in blocks]
    assert pages == sorted(pages), "pages must arrive in reading order"


def test_pdf_extraction_survives_overlapping_table_text() -> None:
    """Regression: geometric char-sorting interleaved overlapping table cells.

    The troubleshooting guide's symptom table draws cell text that overflows
    into the next column; drawing-order extraction must keep each cell intact.
    """
    text = " ".join(b.text for b in PdfLoader().load(TROUBLESHOOTING_PDF))
    assert "Cavitation (insufficient NPSH available)" in text
    assert "(cid:" not in text, "unmapped-glyph artifacts must be normalized"


def test_docx_sections_from_bold_headings() -> None:
    """This corpus (like most real offices) bolds headings instead of styling them."""
    hr_docx = DATASET / "policies" / "HR_Leave_and_Time_Off_Policy.docx"
    blocks = list(loader_for(hr_docx).load(hr_docx))
    carry = next(b for b in blocks if b.locator == 'section "Carry-Over Policy"')
    assert "maximum of 5 unused annual leave days" in carry.text
    assert any(b.locator.startswith("table") for b in blocks)


def test_pptx_slides_capture_tables() -> None:
    q2_pptx = DATASET / "reports_and_presentations" / "Q2_2026_Business_Review.pptx"
    blocks = list(loader_for(q2_pptx).load(q2_pptx))
    assert [b.locator for b in blocks[:3]] == ["slide 1", "slide 2", "slide 3"]
    slide4 = next(b for b in blocks if b.locator == "slide 4")
    assert "EMEA" in slide4.text and "52.1" in slide4.text, "table cells must be captured"


def test_csv_rows_are_self_describing() -> None:
    spec_csv = DATASET / "specifications" / "AF-4500_Series_Spec_Sheet.csv"
    blocks = list(loader_for(spec_csv).load(spec_csv))
    assert [b.locator for b in blocks] == ["row 1", "row 2", "row 3"]
    assert "Model: AF-4530" in blocks[2].text
    assert "Max_Flow_m3h: 850" in blocks[2].text, "rows must carry their column names"


def test_txt_is_one_honest_block() -> None:
    ecn_txt = DATASET / "engineering" / "ECN-2031_Impeller_Material_Change.txt"
    blocks = list(loader_for(ecn_txt).load(ecn_txt))
    assert len(blocks) == 1
    assert blocks[0].locator == "full document"
    assert "AF4520-2026-0500" in blocks[0].text
