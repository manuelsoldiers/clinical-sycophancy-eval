"""Write the clinician's labels from the review page back into human_review/to_grade.csv.

Accepts either format:
  - a list of documents from the page's database: [{"review_id": ..., "turn1": ..., "turn2": ..., "note": ...}, ...]
  - the page's "Copy all answers" export: {"R0001": {"turn1": ..., "turn2": ..., "note": ...}, ...}

Usage: python scripts/import_review_labels.py labels.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        labels = {rid: v for rid, v in raw.items()}
    else:
        labels = {d["review_id"]: d for d in raw}

    path = ROOT / "human_review" / "to_grade.csv"
    df = pd.read_csv(path).fillna("")
    for col in ("human_turn1", "human_turn2", "human_notes"):
        df[col] = df[col].astype(str)
    for i, rid in df.review_id.items():
        lab = labels.get(rid)
        if lab:
            df.at[i, "human_turn1"] = lab.get("turn1", "") or ""
            df.at[i, "human_turn2"] = lab.get("turn2", "") or ""
            df.at[i, "human_notes"] = lab.get("note", "") or ""
    df.to_csv(path, index=False)
    done = ((df.human_turn1 != "") & (df.human_turn2 != "")).sum()
    print(f"Imported labels: {done} of {len(df)} conversations fully graded.")


if __name__ == "__main__":
    main()
