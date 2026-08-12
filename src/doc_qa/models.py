"""Answer contract: every grounded answer carries verifiable citations.

`grounded=False` is the refusal path — the pilot's hard rule is *no
ungrounded answers*, so "I don't know" is a first-class, typed outcome,
not an error.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A resolvable reference into the corpus: document + page/slide/row."""

    source: str
    locator: str

    @property
    def ref(self) -> str:
        return f"{self.source} — {self.locator}"


class Answer(BaseModel):
    """What the QA system returns for every question — answer or refusal."""

    text: str
    citations: list[Citation] = Field(default_factory=list)
    grounded: bool
    provider: str | None = None  # which LLM served it (observability, from the gateway envelope)
    model: str | None = None
