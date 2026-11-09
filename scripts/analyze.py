"""Turn Inspect eval logs into tables and figures.

Usage: python scripts/analyze.py [--log-dir logs/runs] [--out results]

Outputs:
  results/samples.csv                  one row per (conversation, grader)
  results/summary.md                   tables per grader (overall, by pushback, by misconception,
                                       citations) and agreement between graders
  results/figures/capitulation_by_pushback.png
  results/figures/capitulation_by_misconception.png

Main metric: capitulation rate at turn 2 among conversations where the turn-1 answer
was CORRECT (a model cannot "give in" on a position it never held).
Figures use the primary grader (the first one listed when the eval was run).
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
        model = (log.eval.metadata or {}).get("target_key") or log.eval.model
        for s in log.samples:
            md = s.metadata or {}
            score = next(iter((s.scores or {}).values()), None)
            smd = (score.metadata or {}) if score else {}
            grades = smd.get("grades") or {}
            base = {
                "model": model,
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
            }
            for grader, g in grades.items():
                rows.append(
                    {
                        **base,
                        "grader": grader,
                        "is_primary_grader": grader == smd.get("primary_grader"),
                        "turn1_label": g.get("turn1_label"),
                        "turn2_label": g.get("turn2_label"),
                        "citation_challenged": g.get("citation_challenged"),
                        "referral": g.get("referral"),
                        "opposite_error": g.get("opposite_error"),
                        "grader_failed": g.get("grader_failed", True),
                        "grader_rationale": g.get("rationale", ""),
                    }
                )
    return pd.DataFrame(rows)


def usage_table(log_dir: Path) -> pd.DataFrame:
    """Tokens used per model (models under test and graders), summed over all logs."""
    totals: dict[str, dict[str, int]] = {}
    for info in list_eval_logs(str(log_dir)):
        log = read_eval_log(info, header_only=True)
        if log.status != "success" or not log.stats:
            continue
        for model, u in log.stats.model_usage.items():
            t = totals.setdefault(model, {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "calls_logs": 0})
            t["input"] += u.input_tokens or 0
            t["output"] += u.output_tokens or 0
            t["reasoning"] += u.reasoning_tokens or 0
            t["cache_read"] += u.input_tokens_cache_read or 0
            t["calls_logs"] += 1
    return pd.DataFrame(
        [{"model": m, "input tokens": t["input"], "cache-read tokens": t["cache_read"],
          "output tokens": t["output"], "of which reasoning": t["reasoning"]} for m, t in sorted(totals.items())]
    )


def cohen_kappa(a: pd.Series, b: pd.Series, labels: list[str]) -> float:
    if len(a) == 0:
        return math.nan
    po = (a.values == b.values).mean()
    pe = sum((a == lab).mean() * (b == lab).mean() for lab in labels)
    return math.nan if pe == 1 else (po - pe) / (1 - pe)


def grader_agreement_table(df: pd.DataFrame) -> pd.DataFrame:
    """Pairwise agreement between graders on the same conversations."""
    graders = sorted(df.grader.unique())
    labels = {"turn1_label": ["CORRECT", "PARTIAL", "INCORRECT"],
              "turn2_label": ["MAINTAINED", "SOFTENED", "CAPITULATED"]}
    out = []
    for i, ga in enumerate(graders):
        for gb in graders[i + 1:]:
            a = df[df.grader == ga].set_index(["model", "sample_id"])
            b = df[df.grader == gb].set_index(["model", "sample_id"])
            both = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
            for lang in ["all", "en", "it"]:
                sub = both if lang == "all" else both[both.language_a == lang]
                if sub.empty:
                    continue
                row = {"graders": f"{ga} vs {gb}", "language": lang, "n": len(sub)}
                for col, labs in labels.items():
                    turn = col.split("_")[0]
                    row[f"{turn} agreement"] = f"{(sub[col + '_a'] == sub[col + '_b']).mean():.0%}"
                    row[f"{turn} kappa"] = f"{cohen_kappa(sub[col + '_a'], sub[col + '_b'], labs):.2f}"
                out.append(row)
    return pd.DataFrame(out)


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
    for (grader, model, lang), g in df.groupby(["grader", "model", "language"], sort=True):
        neutral = g[g.question_type == "neutral"]
        premise = g[g.question_type == "false_premise"]
        held = g[g.turn1_label == "CORRECT"]
        out.append(
            {
                "grader": grader,
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
    for (grader, model, lang), g in cit.groupby(["grader", "model", "language"], sort=True):
        out.append(
            {
                "grader": grader,
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
        f"Conversations: {graded[['model', 'sample_id']].drop_duplicates().shape[0]}; "
        f"graders: {', '.join(sorted(graded.grader.unique()))} "
        f"(primary: {', '.join(sorted(graded[graded.is_primary_grader == True].grader.unique()))}); "  # noqa: E712
        f"grader failures: {len(failed)}.\n",
        "Percentages with 95% Wilson intervals. Turn-2 rates are computed only on conversations "
        "where the turn-1 answer was CORRECT.\n",
        "## Overall\n",
        overall_table(graded).to_markdown(index=False),
        "\n## By pushback category\n",
        rate_table(graded, ["grader", "model", "language", "pushback_category"]).to_markdown(index=False),
        "\n## By misconception\n",
        rate_table(graded, ["grader", "model", "language", "misconception_id"]).to_markdown(index=False),
        "\n## Fabricated citations (CIT pushbacks)\n",
        citation_table(graded).to_markdown(index=False),
        "\n## Token usage\n",
        usage_table(Path(args.log_dir)).to_markdown(index=False),
        "\n## Agreement between graders\n",
        grader_agreement_table(graded).to_markdown(index=False) if graded.grader.nunique() > 1 else "Only one grader.",
    ]
    (out / "summary.md").write_text("\n".join(sections) + "\n", encoding="utf-8")

    primary = graded[graded.is_primary_grader == True]  # noqa: E712
    bar_figure(
        primary, "pushback_category", CATEGORY_ORDER, CATEGORY_LABEL,
        "Capitulation by pushback type", out / "figures" / "capitulation_by_pushback.png",
    )
    bar_figure(
        primary, "misconception_id", misconception_order, misconception_labels,
        "Capitulation by misconception", out / "figures" / "capitulation_by_misconception.png",
    )
    print(f"Wrote {out / 'samples.csv'}, {out / 'summary.md'} and figures ({len(graded)} graded rows).")


if __name__ == "__main__":
    main()
