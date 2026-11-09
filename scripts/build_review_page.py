"""Build the blinded review page from human_review/to_grade.csv.

The page shows each conversation (no model name, no grader labels) with the same
labels the automatic graders use, and saves the clinician's choices in the page's
database. Afterwards, scripts/import_review_labels.py writes them back into
human_review/to_grade.csv for scripts/agreement.py.

Usage: python scripts/build_review_page.py
Writes: human_review/review_page.html
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    cases = pd.read_csv(ROOT / "human_review" / "to_grade.csv").fillna("")
    misconceptions = json.loads((ROOT / "data" / "source" / "misconceptions.json").read_text(encoding="utf-8"))
    reference = {m["name"]["en"]: m["reference_position"] for m in misconceptions}

    fields = ["review_id", "language", "misconception_name", "question_type", "question",
              "turn1_response", "pushback_text", "turn2_response"]
    payload = [{**{f: str(row[f]) for f in fields}, "reference_position": reference.get(row["misconception_name"], "")}
               for _, row in cases.iterrows()]

    template = (ROOT / "scripts" / "review_page_template.html").read_text(encoding="utf-8")
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")  # keep </script> out of the JSON
    page = template.replace("/*__CASES__*/[]", data, 1)
    assert data in page, "placeholder not found in template"

    out = ROOT / "human_review" / "review_page.html"
    out.write_text(page, encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)} with {len(payload)} conversations ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
