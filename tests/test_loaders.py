"""Loader contract and PDF extraction tests (offline; run against the committed dataset)."""

from pathlib import Path

import pytest

from doc_qa.errors import UnsupportedFormatError
from doc_qa.loaders import DocumentLoader, PdfLoader, TextBlock, loader_for

DATASET = Path(__file__).resolve().parent.parent / "dataset"
WARRANTY_PDF = DATASET / "policies" / "Warranty_and_Service_Policy.pdf"


def test_loader_for_dispatches_pdf() -> None:
    assert isinstance(loader_for(WARRANTY_PDF), PdfLoader)


def test_loader_for_rejects_unknown_format() -> None:
    with pytest.raises(UnsupportedFormatError, match="docx"):
        loader_for(Path("policies/HR_Leave_and_Time_Off_Policy.docx"))


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
