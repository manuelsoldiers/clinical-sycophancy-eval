"""Inline SVG figures shared by the showcase page and the paper (same data, same look).

Every function returns an SVG string sized by viewBox; text uses the page's fonts.
Colours: English/Italian use the validated categorical pair (blue/orange); single-series
charts use the page accent with direct value labels.
"""

from __future__ import annotations

from html import escape

EN, IT = "#2a78d6", "#eb6834"
ACCENT, INK, MUTED, GRID, LINE = "#0f6e63", "#17221f", "#55635f", "#e4e9e7", "#c9d3cf"
MODEL_LABEL = {
    "claude-sonnet-5.5": "Claude Sonnet 5.5",
    "claude-haiku-5.5": "Claude Haiku 5.5",
    "gpt-oss-120b": "gpt-oss-120b",
    "gpt-oss-20b": "gpt-oss-20b",
}
CATEGORY_LABEL = {
    "CTRL": "“Are you sure?”",
    "EMO": "Emotional pressure",
    "AUTH": "Patient cites an authority",
    "CLIN": "User claims to be a clinician",
    "CIT": "Fabricated study or guideline",
}


def _t(x, y, s, size=13, anchor="start", weight=400, fill=INK, family="sans", italic=False):
    fam = {"sans": "IBM Plex Sans, sans-serif", "mono": "IBM Plex Mono, monospace", "serif": "IBM Plex Serif, serif"}[family]
    style = ' font-style="italic"' if italic else ""
    return (f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill}"{style}>{escape(str(s))}</text>')


def flowchart() -> str:
    """Study pipeline with the validation loop that chose and refined the grader."""
    w, h = 1000, 470
    bw, bh, gap, y0 = 172, 132, 30, 52
    xs = [6 + i * (bw + gap) for i in range(5)]
    boxes = [
        ("DATASET", ["6 misconceptions", "× 4 questions", "× 10 pushbacks", "× English / Italian"]),
        ("4 MODELS · OPENROUTER", ["Claude Sonnet 5.5", "Claude Haiku 5.5", "gpt-oss-120b", "gpt-oss-20b"]),
        ("TWO-TURN CONVERSATION", ["1 patient asks", "2 model answers", "3 patient pushes back", "4 model answers"]),
        ("GRADERS", ["Claude Opus 5.5", "(primary)", "gpt-oss-120b", "(cross-family check)"]),
        ("OUTCOME", ["Yielded: softened or", "capitulated, after a", "correct first answer", "+ 95% Wilson CI"]),
    ]
    out = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" '
           'aria-label="Study pipeline: a bilingual dataset of 480 conversations per model is run on four models; '
           'each two-turn conversation is graded by Claude Opus 5.5 and gpt-oss-120b. Before the main run, a pilot '
           'and a physiotherapist\'s blind grading selected the grader and added a rule to its rubric.">',
           '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           f'<path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker>'
           '<marker id="aha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           f'<path d="M0,0 L10,5 L0,10 z" fill="{ACCENT}"/></marker></defs>',
           _t(10, 26, "MAIN RUN · 1,920 CONVERSATIONS", 12, weight=500, fill=MUTED, family="mono")]
    for i, (x, (title, lines)) in enumerate(zip(xs, boxes)):
        out.append(f'<rect x="{x}" y="{y0}" width="{bw}" height="{bh}" rx="10" fill="#ffffff" stroke="{LINE}" stroke-width="1.5"/>')
        out.append(_t(x + 14, y0 + 26, title, 11.5, weight=500, fill=ACCENT, family="mono"))
        for j, line in enumerate(lines):
            out.append(_t(x + 14, y0 + 52 + j * 21, line, 14))
        if i < 4:
            ax = x + bw
            out.append(f'<line x1="{ax + 3}" y1="{y0 + bh / 2}" x2="{ax + gap - 3}" y2="{y0 + bh / 2}" stroke="{MUTED}" stroke-width="1.5" marker-end="url(#ah)"/>')
    # Validation loop
    ly, lh = 300, 110
    out.append(_t(10, ly - 22, "VALIDATION LOOP · BEFORE THE MAIN RUN", 12, weight=500, fill=ACCENT, family="mono"))
    loop = [
        (xs[1], "PILOT", ["80 conversations", "4 candidate graders", "(Opus, Gemini,", "Mistral, gpt-oss)"]),
        (xs[2], "BLIND CLINICAL GRADING", ["40 conversations", "graded by a", "physiotherapist,", "labels hidden"]),
        (xs[3], "GRADER CHOSEN + RUBRIC", ["Opus agreed best", "new rule: a fabricated", "source accepted", "→ at most SOFTENED"]),
    ]
    for x, title, lines in loop:
        out.append(f'<rect x="{x}" y="{ly}" width="{bw}" height="{lh + 22}" rx="10" fill="#e2f0ed" stroke="{ACCENT}" stroke-width="1.5"/>')
        out.append(_t(x + 14, ly + 24, title, 11, weight=500, fill=ACCENT, family="mono"))
        for j, line in enumerate(lines):
            out.append(_t(x + 14, ly + 48 + j * 20, line, 13.5))
    out.append(f'<line x1="{xs[1] + bw / 2}" y1="{y0 + bh + 4}" x2="{xs[1] + bw / 2}" y2="{ly - 32}" stroke="{ACCENT}" stroke-width="1.5" stroke-dasharray="4 4" marker-end="url(#aha)"/>')
    out.append(_t(xs[1] + bw / 2 + 8, y0 + bh + 34, "pilot sample", 10.5, fill=ACCENT))
    for a, b in [(xs[1], xs[2]), (xs[2], xs[3])]:
        out.append(f'<line x1="{a + bw + 3}" y1="{ly + (lh + 22) / 2}" x2="{b - 3}" y2="{ly + (lh + 22) / 2}" stroke="{ACCENT}" stroke-width="1.5" marker-end="url(#aha)"/>')
    out.append(f'<line x1="{xs[3] + bw / 2}" y1="{ly - 6}" x2="{xs[3] + bw / 2}" y2="{y0 + bh + 6}" stroke="{ACCENT}" stroke-width="1.5" marker-end="url(#aha)"/>')
    out.append(_t(xs[3] + bw / 2 + 8, y0 + bh + 34, "κ 0.30 → 0.38", 10.5, fill=ACCENT))
    out.append("</svg>")
    return "".join(out)


def bars_by_model(stats: dict, models: list[str]) -> str:
    """Yielded rate per model, English vs Italian, with 95% Wilson intervals."""
    w, h, left, right, top, bottom = 760, 330, 48, 16, 30, 52
    ymax = 60
    pw, ph = w - left - right, h - top - bottom
    y = lambda v: top + ph * (1 - v / ymax)  # noqa: E731
    out = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" '
           'aria-label="Yielded rate by model: Claude Sonnet 5.5 and Haiku 5.5 about 3 to 7 percent, '
           'gpt-oss-120b and gpt-oss-20b about 34 to 40 percent, with similar values in English and Italian.">']
    for v in range(0, ymax + 1, 10):
        out.append(f'<line x1="{left}" x2="{w - right}" y1="{y(v)}" y2="{y(v)}" stroke="{GRID}" stroke-width="1"/>')
        out.append(_t(left - 8, y(v) + 4, f"{v}%", 11, "end", fill=MUTED, family="mono"))
    group = pw / len(models)
    bw = 46
    for i, m in enumerate(models):
        cx = left + group * (i + 0.5)
        for j, (lang, col) in enumerate([("en", EN), ("it", IT)]):
            r = stats["by_model"][m]["by_language"][lang]["yielded"]
            v, lo, hi = 100 * r["rate"], 100 * r["ci95"][0], 100 * r["ci95"][1]
            x = cx + (j - 1) * (bw + 3) + 1.5
            out.append(f'<path d="M{x},{y(0)} V{y(v) + 4} Q{x},{y(v)} {x + 4},{y(v)} H{x + bw - 4} Q{x + bw},{y(v)} {x + bw},{y(v) + 4} V{y(0)} Z" fill="{col}"/>')
            xm = x + bw / 2
            out.append(f'<line x1="{xm}" x2="{xm}" y1="{y(lo)}" y2="{y(hi)}" stroke="{INK}" stroke-width="1.2" opacity=".55"/>')
            out.append(f'<line x1="{xm - 5}" x2="{xm + 5}" y1="{y(hi)}" y2="{y(hi)}" stroke="{INK}" stroke-width="1.2" opacity=".55"/>')
            out.append(_t(xm, y(hi) - 6, f"{v:.0f}%", 11.5, "middle", 500, INK, "mono"))
        out.append(_t(cx, h - bottom + 22, MODEL_LABEL[m], 12.5, "middle", 500))
    out.append(f'<rect x="{left + 4}" y="6" width="12" height="12" rx="2" fill="{EN}"/>' + _t(left + 22, 16, "English", 12))
    out.append(f'<rect x="{left + 90}" y="6" width="12" height="12" rx="2" fill="{IT}"/>' + _t(left + 108, 16, "Italian", 12))
    out.append("</svg>")
    return "".join(out)


def categories_by_family(stats: dict) -> str:
    """Small multiples: yielded rate by pushback type, Claude models vs gpt-oss models."""
    cats = ["CTRL", "EMO", "AUTH", "CLIN", "CIT"]
    w, h = 760, 300
    panel_w, label_w, top, row = 370, 0, 40, 46
    out = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" '
           'aria-label="Yielded rate by pushback type. Claude models: at most about 11 percent for any type. '
           'gpt-oss models: 72 percent when the patient cites an authority, 50 percent with a fabricated study, '
           '38 percent under emotional pressure, 19 percent when the user claims to be a clinician, 4 percent for are you sure.">']
    for p, (fam, title) in enumerate([("Claude", "Claude models"), ("gpt-oss", "gpt-oss models")]):
        x0 = p * (panel_w + 20)
        bar_x, bar_w = x0 + 186, panel_w - 186 - 46
        out.append(_t(x0, 20, title.upper(), 12, weight=500, fill=MUTED, family="mono"))
        for i, c in enumerate(cats):
            r = stats["by_family"][fam]["by_category"][c]
            v = 100 * r["rate"]
            yy = top + i * row
            out.append(_t(x0, yy + 18, CATEGORY_LABEL[c], 12.5))
            out.append(f'<rect x="{bar_x}" y="{yy + 4}" width="{bar_w}" height="20" rx="4" fill="{GRID}"/>')
            if v > 0:
                out.append(f'<rect x="{bar_x}" y="{yy + 4}" width="{max(3, bar_w * v / 100):.1f}" height="20" rx="4" fill="{ACCENT}"/>')
            out.append(_t(bar_x + bar_w + 8, yy + 19, f"{v:.0f}%", 12, weight=500, family="mono"))
        out.append(_t(bar_x, top + len(cats) * row + 12, "0%", 10.5, fill=MUTED, family="mono"))
        out.append(_t(bar_x + bar_w, top + len(cats) * row + 12, "100%", 10.5, "end", fill=MUTED, family="mono"))
    out.append("</svg>")
    return "".join(out)
