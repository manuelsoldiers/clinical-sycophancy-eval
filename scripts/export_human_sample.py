"""Export a stratified, blinded sample of graded conversations for manual review.

The clinician grades each conversation without seeing the automatic grader's labels;
scripts/agreement.py then compares the two.

Usage: python scripts/export_human_sample.py [--n 100] [--seed 42]

Writes:
  human_review/to_grade.csv    blinded: fill in human_turn1, human_turn2 (and notes)
  human_review/answer_key.csv  grader labels for the same rows (do not open before grading)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", default=str(ROOT / "results" / "samples.csv"))
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = pd.read_csv(args.samples)
    df = df[df.grader_failed != True].copy()  # noqa: E712
    df["review_id"] = [f"R{i:04d}" for i in range(len(df))]

    # Stratify by language x grader turn-2 label, so that rare labels (e.g. CAPITULATED)
    # are represented; within each stratum, sample across models and pushback types.
    groups = [g for _, g in df.groupby(["language", "turn2_label"])]
    per_stratum = max(1, args.n // max(1, len(groups)))
    picked = pd.concat([g.sample(min(len(g), per_stratum), random_state=args.seed) for g in groups])
    if len(picked) < args.n:
        rest = df.drop(picked.index)
        picked = pd.concat([picked, rest.sample(min(len(rest), args.n - len(picked)), random_state=args.seed)])
    picked = picked.sample(frac=1, random_state=args.seed).head(args.n)

    out = ROOT / "human_review"
    out.mkdir(exist_ok=True)
    blinded = picked[
        ["review_id", "language", "misconception_name", "question_type", "question",
         "turn1_response", "pushback_text", "turn2_response"]
    ].copy()
    blinded["human_turn1"] = ""  # CORRECT | PARTIAL | INCORRECT
    blinded["human_turn2"] = ""  # MAINTAINED | SOFTENED | CAPITULATED
    blinded["human_notes"] = ""
    blinded.to_csv(out / "to_grade.csv", index=False)
    picked[["review_id", "model", "sample_id", "turn1_label", "turn2_label"]].to_csv(
        out / "answer_key.csv", index=False
    )
    print(f"Wrote {len(blinded)} rows to {out / 'to_grade.csv'} (key in answer_key.csv)")
    print(picked.groupby(["language", "turn2_label"]).size().to_string())


if __name__ == "__main__":
    main()
