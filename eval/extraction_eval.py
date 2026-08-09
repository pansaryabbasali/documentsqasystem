"""M2 extraction-accuracy harness: known-string survival rate.

Ground truth (eval/known_strings.json) is ~20 exact strings chosen from the
dataset's cross-document facts — spec values, part numbers, policy terms that
the spec-sheet CSV, ECN memo, and README establish independently of any PDF's
rendering. Each string must appear in the text extracted from its PDF after
normalization (whitespace collapsed, dash variants unified, case-folded), so
layout noise can't mask content loss. Target: >=95% survival.

Run:  python eval/extraction_eval.py    (writes eval/extraction_accuracy_M2.md;
                                         exit code 1 if below target)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from doc_qa.loaders import loader_for

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "eval" / "known_strings.json"
REPORT = ROOT / "eval" / "extraction_accuracy_M2.md"
TARGET_PERCENT = 95.0


def normalize(text: str) -> str:
    """Collapse whitespace, unify dashes, casefold — layout must not mask content."""
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    rows: list[tuple[str, str, bool]] = []
    for entry in json.loads(FIXTURE.read_text()):
        pdf = ROOT / "dataset" / entry["file"]
        extracted = normalize(" ".join(b.text for b in loader_for(pdf).load(pdf)))
        rows.extend(
            (entry["file"], needle, normalize(needle) in extracted)
            for needle in entry["strings"]
        )

    hits = sum(found for _, _, found in rows)
    rate = 100 * hits / len(rows)
    verdict = "PASS" if rate >= TARGET_PERCENT else "FAIL"
    lines = [
        "# Extraction accuracy — M2 (known-string survival)",
        "",
        f"**Result: {hits}/{len(rows)} strings found — {rate:.1f}% "
        f"({verdict}, target ≥{TARGET_PERCENT:.0f}%)**",
        "",
        "| Document | Known string | Found |",
        "|---|---|---|",
    ]
    lines += [
        f"| {Path(file).name} | `{needle}` | {'✅' if found else '❌'} |"
        for file, needle, found in rows
    ]
    REPORT.write_text("\n".join(lines) + "\n")
    print(f"{hits}/{len(rows)} = {rate:.1f}% [{verdict}] → {REPORT.relative_to(ROOT)}")
    return 0 if rate >= TARGET_PERCENT else 1


if __name__ == "__main__":
    sys.exit(main())
