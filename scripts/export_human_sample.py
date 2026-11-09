"""Export a stratified, blinded sample of graded conversations for manual review.

The clinician grades each conversation without seeing the automatic grader's labels;
scripts/agreement.py then compares the two.

Usage: python scripts/export_human_sample.py [--n 100] [--seed 42] [--mode label|disagreement]

Modes (both balance the two languages):
  label         stratify by the primary grader's turn-2 label (default)
  disagreement  enrich with conversations on which the graders disagree (up to 60% per
                language), filling the rest at random with agreed ones; used to compare
                graders, since agreed cases cannot tell graders apart

Writes:
  human_review/to_grade.csv    blinded: fill in human_turn1, human_turn2 (and notes)
  human_review/answer_key.csv  every grader's labels for the same rows (do not open before grading)
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
    parser.add_argument("--mode", choices=["label", "disagreement"], default="label")
    parser.add_argument("--max-disagreement-share", type=float, default=0.6)
    args = parser.parse_args()

    long = pd.read_csv(args.samples)
    long = long[long.grader_failed != True]  # noqa: E712
    # One row per conversation (stratified on the primary grader's labels) ...
    df = long[long.is_primary_grader == True].copy()  # noqa: E712
    df["review_id"] = [f"R{i:04d}" for i in range(len(df))]
    # ... and every grader's labels side by side for the answer key.
    wide = long.pivot_table(
        index=["model", "sample_id"], columns="grader", values=["turn1_label", "turn2_label"], aggfunc="first"
    )
    wide.columns = [f"{label}__{grader}" for label, grader in wide.columns]
    wide = wide.reset_index()

    labels_wide = long.pivot_table(
        index=["model", "sample_id"], columns="grader", values=["turn1_label", "turn2_label"], aggfunc="first"
    )
    disagree = (labels_wide["turn1_label"].nunique(axis=1) > 1) | (labels_wide["turn2_label"].nunique(axis=1) > 1)
    df["graders_disagree"] = [bool(disagree.get((m, sid), False)) for m, sid in zip(df.model, df.sample_id)]

    per_language = args.n // 2
    parts = []
    for lang, g in df.groupby("language"):
        if args.mode == "disagreement":
            dis, agr = g[g.graders_disagree], g[~g.graders_disagree]
            k = min(len(dis), round(per_language * args.max_disagreement_share))
            pick = pd.concat([dis.sample(k, random_state=args.seed),
                              agr.sample(min(len(agr), per_language - k), random_state=args.seed)])
            pick = pick.assign(selection=["disagreement" if x else "agreement" for x in pick.graders_disagree])
        else:
            strata = [s for _, s in g.groupby("turn2_label")]
            each = max(1, per_language // max(1, len(strata)))
            pick = pd.concat([s.sample(min(len(s), each), random_state=args.seed) for s in strata])
            if len(pick) < per_language:
                rest = g.drop(pick.index)
                pick = pd.concat([pick, rest.sample(min(len(rest), per_language - len(pick)), random_state=args.seed)])
            pick = pick.assign(selection="label-stratified")
        parts.append(pick.head(per_language))
    picked = pd.concat(parts).sample(frac=1, random_state=args.seed)

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
    key = picked[["review_id", "model", "sample_id", "selection"]].merge(wide, on=["model", "sample_id"], how="left")
    key.to_csv(out / "answer_key.csv", index=False)
    print(f"Wrote {len(blinded)} rows to {out / 'to_grade.csv'} (key in answer_key.csv)")
    print(picked.groupby(["language", "selection"]).size().to_string())


if __name__ == "__main__":
    main()
