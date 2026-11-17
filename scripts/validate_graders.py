"""Compare the clinician's blind labels with grader labels from one or more log directories.

Used after scripts/rescore.py to check a change to the grader prompt or settings
against the clinician, next to the original pilot labels (answer_key.csv).

Usage:
  python scripts/validate_graders.py --log-dirs logs/rescore logs/rescore-opus logs/rescore-low
Writes human_review/validation.md
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd
from inspect_ai.log import list_eval_logs, read_eval_log

ROOT = Path(__file__).resolve().parent.parent
LABELS = {
    "turn1": ["CORRECT", "PARTIAL", "INCORRECT"],
    "turn2": ["MAINTAINED", "SOFTENED", "CAPITULATED"],
}


def kappa(a: pd.Series, b: pd.Series, labels: list[str]) -> float:
    if len(a) == 0:
        return math.nan
    po = (a.values == b.values).mean()
    pe = sum((a == lab).mean() * (b == lab).mean() for lab in labels)
    return math.nan if pe == 1 else (po - pe) / (1 - pe)


def load_grades(log_dirs: list[str]) -> pd.DataFrame:
    rows = []
    for log_dir in log_dirs:
        for info in list_eval_logs(log_dir):
            log = read_eval_log(info)
            model = (log.eval.metadata or {}).get("target_key") or log.eval.model
            for s in log.samples or []:
                score = next(iter((s.scores or {}).values()), None)
                for grader, g in ((score.metadata or {}).get("grades") or {}).items() if score else []:
                    if not g.get("grader_failed"):
                        rows.append({"model": model, "sample_id": s.id, "grader": f"{grader} (updated rubric)",
                                     "turn1": g["turn1_label"], "turn2": g["turn2_label"]})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-dirs", nargs="+", required=True)
    args = parser.parse_args()

    human = pd.read_csv(ROOT / "human_review" / "to_grade.csv")
    key = pd.read_csv(ROOT / "human_review" / "answer_key.csv")
    base = human.merge(key, on="review_id")[["review_id", "model", "sample_id", "language", "human_turn1", "human_turn2"]
                                             + [c for c in key.columns if c.startswith("turn")]]

    # Original pilot grades (pilot rubric), from the answer key.
    long = []
    for col in [c for c in key.columns if c.startswith("turn1_label__")]:
        grader = col.split("__", 1)[1]
        long.append(base.assign(grader=f"{grader} (pilot rubric)", turn1=base[col],
                                turn2=base[f"turn2_label__{grader}"])[["model", "sample_id", "grader", "turn1", "turn2"]])
    grades = pd.concat(long + [load_grades(args.log_dirs)], ignore_index=True)

    lines = ["# Grader validation against the clinician\n",
             "Same 40 conversations, graded blind by the clinician. Cohen's kappa and raw agreement.\n",
             "| grader | n | turn-1 agreement | turn-1 kappa | turn-2 agreement | turn-2 kappa | turn-2 kappa EN | turn-2 kappa IT | turn-2 labels (M/S/C) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for grader, g in grades.groupby("grader", sort=True):
        d = base.merge(g, on=["model", "sample_id"])
        if d.empty:
            continue
        k_lang = {lang: kappa(x.human_turn2, x.turn2, LABELS["turn2"]) for lang, x in d.groupby("language")}
        counts = d.turn2.value_counts()
        lines.append(
            f"| {grader} | {len(d)} | {(d.human_turn1 == d.turn1).mean():.0%} | "
            f"{kappa(d.human_turn1, d.turn1, LABELS['turn1']):.2f} | {(d.human_turn2 == d.turn2).mean():.0%} | "
            f"{kappa(d.human_turn2, d.turn2, LABELS['turn2']):.2f} | {k_lang.get('en', math.nan):.2f} | "
            f"{k_lang.get('it', math.nan):.2f} | "
            f"{counts.get('MAINTAINED', 0)}/{counts.get('SOFTENED', 0)}/{counts.get('CAPITULATED', 0)} |"
        )
    hc = base.human_turn2.value_counts()
    lines.append(f"\nClinician turn-2 labels (M/S/C): {hc.get('MAINTAINED', 0)}/{hc.get('SOFTENED', 0)}/{hc.get('CAPITULATED', 0)}\n")
    report = "\n".join(lines) + "\n"
    (ROOT / "human_review" / "validation.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
