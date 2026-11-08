"""Agreement between the clinician's manual labels and the automatic grader.

Usage: python scripts/agreement.py [--graded human_review/to_grade.csv]

Reports, for each automatic grader, raw agreement and Cohen's kappa with the
clinician for turn 1 and turn 2, overall and per language, plus confusion
matrices. Writes human_review/agreement.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LABELS = {
    "turn1": ["CORRECT", "PARTIAL", "INCORRECT"],
    "turn2": ["MAINTAINED", "SOFTENED", "CAPITULATED"],
}


def cohen_kappa(a: pd.Series, b: pd.Series, labels: list[str]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = (a.values == b.values).mean()
    pe = sum((a == lab).mean() * (b == lab).mean() for lab in labels)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graded", default=str(ROOT / "human_review" / "to_grade.csv"))
    parser.add_argument("--key", default=str(ROOT / "human_review" / "answer_key.csv"))
    args = parser.parse_args()

    human = pd.read_csv(args.graded)
    key = pd.read_csv(args.key)
    df = human.merge(key, on="review_id")
    for col in ("human_turn1", "human_turn2"):
        df[col] = df[col].astype(str).str.strip().str.upper()
    df = df[df.human_turn1.isin(LABELS["turn1"]) & df.human_turn2.isin(LABELS["turn2"])]
    if df.empty:
        raise SystemExit("No rows with valid human labels yet.")

    graders = sorted({c.split("__", 1)[1] for c in df.columns if c.startswith("turn1_label__")})
    lines = ["# Clinician vs automatic graders: agreement\n", f"Rows with valid human labels: {len(df)}\n"]
    for grader in graders:
        lines.append(f"## Grader: {grader}\n")
        for turn in ("turn1", "turn2"):
            h, g = f"human_{turn}", f"{turn}_label__{grader}"
            valid = df[df[g].isin(LABELS[turn])]
            lines.append(f"### {turn}\n")
            lines.append("| subset | n | raw agreement | Cohen's kappa |\n|---|---|---|---|")
            for name, sub in [("all", valid)] + [(lang, d) for lang, d in valid.groupby("language")]:
                agree = (sub[h] == sub[g]).mean()
                kappa = cohen_kappa(sub[h], sub[g], LABELS[turn])
                lines.append(f"| {name} | {len(sub)} | {agree:.0%} | {kappa:.2f} |")
            cm = pd.crosstab(valid[h], valid[g]).reindex(index=LABELS[turn], columns=LABELS[turn], fill_value=0)
            cm.index.name, cm.columns.name = "clinician \\ grader", None
            lines.append("\nConfusion matrix (rows: clinician, columns: grader):\n")
            lines.append(cm.to_markdown())
            lines.append("")

    report = "\n".join(lines) + "\n"
    out = ROOT / "human_review" / "agreement.md"
    out.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
