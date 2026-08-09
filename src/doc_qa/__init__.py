"""doc_qa: grounded document Q&A over the Atlas Fluid Systems pilot corpus.

Answers natural-language questions from mixed-format documents (PDF, DOCX, PPTX,
CSV, TXT) and cites every answer back to its source document and page/slide.
No ungrounded answers: if the corpus doesn't contain the answer, the system says so.

LLM access goes exclusively through the vendored ``llm_gateway`` package.
"""

__version__ = "0.1.0"
