"""Scaffold sanity: the project package is importable and versioned."""

import doc_qa


def test_doc_qa_imports_with_version() -> None:
    assert doc_qa.__version__ == "0.1.0"
