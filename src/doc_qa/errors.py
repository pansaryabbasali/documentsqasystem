"""Typed exceptions for doc_qa."""


class DocQAError(Exception):
    """Base class for all doc_qa errors."""


class UnsupportedFormatError(DocQAError):
    """Raised when no loader is registered for a file's format."""
