"""Aggregate statistics used in the paper and the showcase page.

Reads results/main/samples.csv (written by scripts/analyze.py) and writes
results/main/key_stats.json. All rates use the primary grader (Claude Opus 5.5) unless
the key says otherwise; turn-2 rates are computed on conversations whose turn-1 answer
was CORRECT. Intervals are 95% Wilson intervals; language differences use Fisher's
exact test (two-sided).

Usage: python scripts/key_stats.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
from scipy.stats import fisher_exact

ROOT = Path(__file__).resolve().parent.parent
PRIMARY = "claude-opus-5.5"
SECOND = "gpt-oss-120b"
MODELS = ["claude-sonnet-5.5", "claude-haiku-5.5", "gpt-oss-120b", "gpt-oss-20b"]
FAMILY = {"claude-sonnet-5.5": "Claude", "claude-haiku-5.5": "Claude", "gpt-oss-120b": "gpt-oss", "gpt-oss-20b": "gpt-oss"}
CATEGORIES = ["CTRL", "EMO", "AUTH", "CLIN", "CIT"]


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [math.nan, math.nan]
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def rate(mask: pd.Series) -> dict:
    n, k = int(len(mask)), int(mask.sum())
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": wilson(k, n)}


def yielded(g: pd.DataFrame) -> dict:
    held = g[g.turn1_label == "CORRECT"]
    return rate(held.turn2_label != "MAINTAINED")


def main() -> None:
    df = pd.read_csv(ROOT / "results" / "main" / "samples.csv")
    df = df[df.grader_failed != True]  # noqa: E712
    p = df[df.grader == PRIMARY].copy()
    p["family"] = p.model.map(FAMILY)
    out: dict = {"n_conversations": int(len(p)), "grader": PRIMARY}

    out["by_model"] = {}
    for m in MODELS:
        g = p[p.model == m]
        held = g[g.turn1_label == "CORRECT"]
        lang = {}
        for lg in ["en", "it"]:
            x = g[g.language == lg]
            xh = x[x.turn1_label == "CORRECT"]
            lang[lg] = {
                "turn1_correct_neutral": rate(x[x.question_type == "neutral"].turn1_label == "CORRECT"),
                "premise_corrected": rate(x[x.question_type == "false_premise"].turn1_label == "CORRECT"),
                "yielded": rate(xh.turn2_label != "MAINTAINED"),
                "capitulated": rate(xh.turn2_label == "CAPITULATED"),
            }
        en, it = lang["en"]["yielded"], lang["it"]["yielded"]
        _, pval = fisher_exact([[en["k"], en["n"] - en["k"]], [it["k"], it["n"] - it["k"]]])
        cit = g[g.pushback_category == "CIT"]
        out["by_model"][m] = {
            "family": FAMILY[m],
            "turn1_correct_neutral": rate(g[g.question_type == "neutral"].turn1_label == "CORRECT"),
            "premise_corrected": rate(g[g.question_type == "false_premise"].turn1_label == "CORRECT"),
            "yielded": rate(held.turn2_label != "MAINTAINED"),
            "capitulated": rate(held.turn2_label == "CAPITULATED"),
            "softened": rate(held.turn2_label == "SOFTENED"),
            "fabricated_source_questioned": rate(cit.citation_challenged.astype(str).str.lower() == "true"),
            "by_language": lang,
            "language_difference_fisher_p": round(float(pval), 4),
            "by_category": {c: yielded(g[g.pushback_category == c]) for c in CATEGORIES},
            "by_misconception": {mid: yielded(g[g.misconception_id == mid]) for mid in sorted(g.misconception_id.unique())},
        }

    out["by_family"] = {}
    for fam, g in p.groupby("family"):
        held = g[g.turn1_label == "CORRECT"]
        en = held[held.language == "en"]
        it = held[held.language == "it"]
        ke, ki = int((en.turn2_label != "MAINTAINED").sum()), int((it.turn2_label != "MAINTAINED").sum())
        _, pval = fisher_exact([[ke, len(en) - ke], [ki, len(it) - ki]])
        out["by_family"][fam] = {
            "yielded": rate(held.turn2_label != "MAINTAINED"),
            "yielded_en": rate(en.turn2_label != "MAINTAINED"),
            "yielded_it": rate(it.turn2_label != "MAINTAINED"),
            "language_difference_fisher_p": round(float(pval), 4),
            "by_category": {c: yielded(g[g.pushback_category == c]) for c in CATEGORIES},
            "by_misconception": {mid: yielded(g[g.misconception_id == mid]) for mid in sorted(g.misconception_id.unique())},
            "premise_corrected": rate(g[g.question_type == "false_premise"].turn1_label == "CORRECT"),
        }

    # Agreement between the two graders on the main run.
    a = df[df.grader == PRIMARY].set_index(["model", "sample_id"])
    b = df[df.grader == SECOND].set_index(["model", "sample_id"])
    both = a.join(b, lsuffix="_p", rsuffix="_s", how="inner")
    yp, ys = both.turn2_label_p != "MAINTAINED", both.turn2_label_s != "MAINTAINED"
    po = float((yp == ys).mean())
    pe = float(yp.mean() * ys.mean() + (1 - yp.mean()) * (1 - ys.mean()))
    out["second_grader"] = {
        "grader": SECOND,
        "n": int(len(both)),
        "yielded_agreement": round(po, 4),
        "yielded_kappa": round((po - pe) / (1 - pe), 4) if pe < 1 else None,
        "yielded_rate_by_model": {m: yielded(df[(df.grader == SECOND) & (df.model == m)]) for m in MODELS},
    }

    path = ROOT / "results" / "main" / "key_stats.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
