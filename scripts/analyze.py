"""Turn Inspect eval logs into tables and figures.

Usage: python scripts/analyze.py [--log-dir logs/runs] [--out results]

Outputs:
  results/samples.csv                  one row per graded conversation
  results/summary.md                   tables (overall, by pushback, by misconception, citations)
  results/figures/capitulation_by_pushback.png
  results/figures/capitulation_by_misconception.png

Main metric: capitulation rate at turn 2 among conversations where the turn-1 answer
was CORRECT (a model cannot "give in" on a position it never held).
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from inspect_ai.log import list_eval_logs, read_eval_log  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CATEGORY_ORDER = ["CTRL", "EMO", "AUTH", "CLIN", "CIT"]
CATEGORY_LABEL = {
    "CTRL": "Control\n(\"are you sure?\")",
    "EMO": "Emotional",
    "AUTH": "Patient cites\nauthority",
    "CLIN": "Self-declared\nclinician",
    "CIT": "Fabricated\ncitation",
}
LANG_COLOR = {"en": "#2a78d6", "it": "#eb6834"}  # validated categorical slots 1-2
LANG_LABEL = {"en": "English", "it": "Italian"}
TEXT_PRIMARY, TEXT_SECONDARY, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def load_rows(log_dir: Path) -> pd.DataFrame:
    rows = []
    for info in list_eval_logs(str(log_dir)):
        log = read_eval_log(info)
        if log.status != "success" or not log.samples:
            print(f"skipping {info.name} (status {log.status})")
            continue
        model = log.eval.model
        grader = (log.eval.model_roles or {}).get("grader")
        grader_name = getattr(grader, "model", None) or str(grader)
        for s in log.samples:
            md = s.metadata or {}
            score = next(iter((s.scores or {}).values()), None)
            smd = (score.metadata or {}) if score else {}
            rows.append(
                {
                    "model": model,
                    "grader": grader_name,
                    "sample_id": s.id,
                    "language": md.get("language"),
                    "misconception_id": md.get("misconception_id"),
                    "misconception_name": md.get("misconception_name"),
                    "question_id": md.get("question_id"),
                    "question_type": md.get("question_type"),
                    "pushback_id": md.get("pushback_id"),
                    "pushback_category": md.get("pushback_category"),
                    "question": s.input if isinstance(s.input, str) else "",
                    "pushback_text": md.get("pushback_text"),
                    "turn1_response": smd.get("turn1_response", ""),
                    "turn2_response": smd.get("turn2_response", ""),
                    "turn1_label": smd.get("turn1_label"),
                    "turn2_label": smd.get("turn2_label"),
                    "citation_challenged": smd.get("citation_challenged"),
                    "referral": smd.get("referral"),
                    "opposite_error": smd.get("opposite_error"),
                    "grader_failed": smd.get("grader_failed", True),
                    "grader_rationale": score.explanation if score else "",
                }
            )
    return pd.DataFrame(rows)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def pct(k: int, n: int) -> str:
    if n == 0:
        return "–"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.0f}% [{100 * lo:.0f}–{100 * hi:.0f}] (n={n})"


def rate_table(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Capitulation / softened / maintained among turn-1-correct conversations."""
    held = df[df.turn1_label == "CORRECT"].copy()
    if "pushback_category" in by:
        held["pushback_category"] = pd.Categorical(held.pushback_category, CATEGORY_ORDER, ordered=True)
    out = []
    for keys, g in held.groupby(by, sort=True, observed=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        n = len(g)
        out.append(
            {
                **dict(zip(by, keys)),
                "capitulated": pct((g.turn2_label == "CAPITULATED").sum(), n),
                "softened": pct((g.turn2_label == "SOFTENED").sum(), n),
                "maintained": pct((g.turn2_label == "MAINTAINED").sum(), n),
            }
        )
    return pd.DataFrame(out)


def overall_table(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (model, lang), g in df.groupby(["model", "language"], sort=True):
        neutral = g[g.question_type == "neutral"]
        premise = g[g.question_type == "false_premise"]
        held = g[g.turn1_label == "CORRECT"]
        out.append(
            {
                "model": model,
                "language": lang,
                "turn-1 correct (neutral Q1-Q3)": pct((neutral.turn1_label == "CORRECT").sum(), len(neutral)),
                "false premise corrected (Q4)": pct((premise.turn1_label == "CORRECT").sum(), len(premise)),
                "capitulated (turn-1 correct)": pct((held.turn2_label == "CAPITULATED").sum(), len(held)),
                "softened (turn-1 correct)": pct((held.turn2_label == "SOFTENED").sum(), len(held)),
            }
        )
    return pd.DataFrame(out)


def citation_table(df: pd.DataFrame) -> pd.DataFrame:
    cit = df[df.pushback_category == "CIT"]
    out = []
    for (model, lang), g in cit.groupby(["model", "language"], sort=True):
        out.append(
            {
                "model": model,
                "language": lang,
                "fabricated source questioned": pct(int(g.citation_challenged.fillna(False).sum()), len(g)),
            }
        )
    return pd.DataFrame(out)


def bar_figure(df: pd.DataFrame, by: str, order: list[str], labels: dict[str, str], title: str, path: Path) -> None:
    held = df[df.turn1_label == "CORRECT"]
    models = sorted(held.model.unique())
    if not models:
        return
    fig, axes = plt.subplots(
        len(models), 1, figsize=(9, 3.2 * len(models)), squeeze=False, sharey=True, facecolor="#fcfcfb"
    )
    width = 0.38
    for ax, model in zip(axes[:, 0], models):
        ax.set_facecolor("#fcfcfb")
        sub = held[held.model == model]
        for j, lang in enumerate(["en", "it"]):
            xs, ys, err_lo, err_hi = [], [], [], []
            for i, key in enumerate(order):
                g = sub[(sub[by] == key) & (sub.language == lang)]
                n, k = len(g), int((g.turn2_label == "CAPITULATED").sum())
                if n == 0:
                    continue
                lo, hi = wilson(k, n)
                p = k / n
                xs.append(i + (j - 0.5) * (width + 0.02))
                ys.append(100 * p)
                err_lo.append(100 * (p - lo))
                err_hi.append(100 * (hi - p))
            ax.bar(xs, ys, width=width, color=LANG_COLOR[lang], label=LANG_LABEL[lang], zorder=2)
            ax.errorbar(xs, ys, yerr=[err_lo, err_hi], fmt="none", ecolor=TEXT_SECONDARY, elinewidth=1, capsize=2, zorder=3)
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels([labels.get(k, k) for k in order], color=TEXT_SECONDARY, fontsize=9)
        ax.set_ylim(0, 100)
        ax.set_ylabel("Capitulated (%)", color=TEXT_SECONDARY, fontsize=9)
        ax.set_title(model, loc="left", color=TEXT_PRIMARY, fontsize=11, fontweight="bold")
        ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
        ax.tick_params(colors=TEXT_SECONDARY, length=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.legend(frameon=False, loc="upper right", fontsize=9, labelcolor=TEXT_PRIMARY)
    fig.suptitle(title, x=0.01, ha="left", color=TEXT_PRIMARY, fontsize=12)
    fig.text(
        0.01, 0.005,
        "Turn-2 capitulation among conversations with a correct turn-1 answer. Error bars: 95% Wilson intervals.",
        color=TEXT_SECONDARY, fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-dir", default=str(ROOT / "logs" / "runs"))
    parser.add_argument("--out", default=str(ROOT / "results"))
    args = parser.parse_args()

    out = Path(args.out)
    (out / "figures").mkdir(parents=True, exist_ok=True)

    df = load_rows(Path(args.log_dir))
    if df.empty:
        raise SystemExit(f"No successful eval logs found in {args.log_dir}")
    df.to_csv(out / "samples.csv", index=False)

    failed = df[df.grader_failed == True]  # noqa: E712
    graded = df[df.grader_failed != True]  # noqa: E712

    misconception_order = sorted(graded.misconception_id.dropna().unique())
    misconception_labels = (
        graded.drop_duplicates("misconception_id").set_index("misconception_id").misconception_name.to_dict()
    )
    misconception_labels = {k: f"{k}\n{v[:22]}" for k, v in misconception_labels.items()}

    sections = [
        "# Results\n",
        f"Graded conversations: {len(graded)} (grader failures: {len(failed)}).\n",
        "Percentages with 95% Wilson intervals. Turn-2 rates are computed only on conversations "
        "where the turn-1 answer was CORRECT.\n",
        "## Overall\n",
        overall_table(graded).to_markdown(index=False),
        "\n## By pushback category\n",
        rate_table(graded, ["model", "language", "pushback_category"]).to_markdown(index=False),
        "\n## By misconception\n",
        rate_table(graded, ["model", "language", "misconception_id"]).to_markdown(index=False),
        "\n## Fabricated citations (CIT pushbacks)\n",
        citation_table(graded).to_markdown(index=False),
    ]
    (out / "summary.md").write_text("\n".join(sections) + "\n", encoding="utf-8")

    bar_figure(
        graded, "pushback_category", CATEGORY_ORDER, CATEGORY_LABEL,
        "Capitulation by pushback type", out / "figures" / "capitulation_by_pushback.png",
    )
    bar_figure(
        graded, "misconception_id", misconception_order, misconception_labels,
        "Capitulation by misconception", out / "figures" / "capitulation_by_misconception.png",
    )
    print(f"Wrote {out / 'samples.csv'}, {out / 'summary.md'} and figures ({len(graded)} graded rows).")


if __name__ == "__main__":
    main()
