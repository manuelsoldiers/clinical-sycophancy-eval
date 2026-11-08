"""Build data/dataset.jsonl from the source files in data/source/.

One row per (language, misconception, question, pushback):
2 languages x 6 misconceptions x 4 questions x 15 pushbacks = 720 rows.

Usage: python scripts/build_dataset.py
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "source"
OUT = ROOT / "data" / "dataset.jsonl"

LANGS = ("en", "it")
PLACEHOLDER = re.compile(r"\{[A-Z_]+\}")


def fill(template: str, claim: str, action: str) -> str:
    text = template.replace("{CLAIM}", claim).replace("{ACTION}", action)
    leftover = PLACEHOLDER.findall(text)
    if leftover:
        raise ValueError(f"Unfilled placeholder(s) {leftover} in: {text}")
    return text


def main() -> None:
    misconceptions = json.loads((SRC / "misconceptions.json").read_text(encoding="utf-8"))
    pushbacks = json.loads((SRC / "pushbacks.json").read_text(encoding="utf-8"))

    rows = []
    for lang in LANGS:
        for m in misconceptions:
            claim, action = m["claim"][lang], m["action"][lang]
            for qid, q in m["questions"].items():
                for p in pushbacks:
                    rows.append(
                        {
                            "id": f"{lang}-{m['id']}-{qid}-{p['id']}",
                            "input": q[lang],
                            "metadata": {
                                "language": lang,
                                "misconception_id": m["id"],
                                "misconception_name": m["name"]["en"],
                                "question_id": qid,
                                "question_type": q["type"],
                                "pushback_id": p["id"],
                                "pushback_category": p["category"],
                                "pushback_text": fill(p[lang], claim, action),
                                "claim": claim,
                                "action": action,
                                "reference_position": m["reference_position"],
                                "capitulation_criteria": m["capitulation_criteria"],
                            },
                        }
                    )

    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate sample ids"

    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    by_lang = Counter(r["metadata"]["language"] for r in rows)
    by_type = Counter(r["metadata"]["question_type"] for r in rows)
    print(f"Wrote {len(rows)} samples to {OUT.relative_to(ROOT)}")
    print(f"  by language: {dict(by_lang)}")
    print(f"  by question type: {dict(by_type)}")


if __name__ == "__main__":
    main()
