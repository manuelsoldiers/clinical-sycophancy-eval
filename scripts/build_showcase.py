"""Build the showcase page (showcase/index.html) and the paper source (paper/paper.html).

All numbers come from results/main/key_stats.json, human_review/validation.md inputs and
the source data, so the page, the paper and the repository cannot drift apart.
Render the PDF afterwards with: node scripts/render_paper.cjs

Usage: python scripts/build_showcase.py
"""

from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from figures_svg import MODEL_LABEL, bars_by_model, categories_by_family, flowchart  # noqa: E402

K = json.loads((ROOT / "results" / "main" / "key_stats.json").read_text(encoding="utf-8"))
MIS = json.loads((ROOT / "data" / "source" / "misconceptions.json").read_text(encoding="utf-8"))
PUSH = json.loads((ROOT / "data" / "source" / "pushbacks.json").read_text(encoding="utf-8"))
MODELS = ["claude-sonnet-5.5", "claude-haiku-5.5", "gpt-oss-120b", "gpt-oss-20b"]
REPO = "https://github.com/manuelsoldiers/clinical-sycophancy-eval"
PDF_URL = f"{REPO}/blob/main/paper/clinical-sycophancy-eval.pdf"
PDF_RAW = f"{REPO}/raw/main/paper/clinical-sycophancy-eval.pdf"

# Grader validation on the 40 clinician-graded conversations (human_review/validation.md).
VALIDATION = [
    ("Claude Opus 5.5, pilot rubric", 0.30, 0.20, 0.43, "25 / 11 / 4"),
    ("Claude Opus 5.5, updated rubric", 0.38, 0.23, 0.57, "23 / 12 / 5"),
    ("Claude Opus 5.5, low reasoning effort", 0.32, 0.23, 0.43, "24 / 11 / 5"),
    ("Mistral Large 4", 0.23, 0.27, 0.13, "37 / 1 / 2"),
    ("Gemini 3.8 Flash", 0.18, 0.19, 0.14, "32 / 2 / 6"),
    ("gpt-oss-120b", 0.15, 0.16, 0.13, "38 / 0 / 2"),
]
CLINICIAN_DIST = "26 / 13 / 1"
BINARY_KAPPA, BINARY_AGREE = 0.53, 0.78
COSTS = {"pilot_and_validation": 8.13, "main_run": 68.48, "total": 76.93}


def pct(r: dict, ci: bool = False) -> str:
    s = f"{100 * r['rate']:.0f}%"
    if ci:
        s += f" [{100 * r['ci95'][0]:.0f}–{100 * r['ci95'][1]:.0f}]"
    return s


def frac(r: dict) -> str:
    return f"{r['k']}/{r['n']}"


BM = K["by_model"]
FAM = K["by_family"]
SG = K["second_grader"]


# --------------------------------------------------------------------------- shared tables

def model_table(ci: bool = True) -> str:
    rows = []
    for m in MODELS:
        b = BM[m]
        rows.append(
            f"<tr><th scope=\"row\">{MODEL_LABEL[m]}</th>"
            f"<td>{pct(b['turn1_correct_neutral'])}</td>"
            f"<td>{pct(b['premise_corrected'])}</td>"
            f"<td><strong>{pct(b['yielded'], ci)}</strong></td>"
            f"<td>{pct(b['capitulated'])}</td>"
            f"<td>{pct(b['fabricated_source_questioned'])}</td></tr>"
        )
    return ("<table class=\"data\"><thead><tr><th>Model</th><th>First answer correct<br><span>neutral questions</span></th>"
            "<th>False premise corrected<br><span>Q4</span></th><th>Yielded to pushback<br><span>softened or capitulated</span></th>"
            "<th>Capitulated</th><th>Fabricated source questioned</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def validation_table() -> str:
    rows = "".join(
        f"<tr><th scope=\"row\">{escape(n)}</th><td>{a:.2f}</td><td>{e:.2f}</td><td>{i:.2f}</td><td>{d}</td></tr>"
        for n, a, e, i, d in VALIDATION
    )
    return ("<table class=\"data\"><thead><tr><th>Grader</th><th>κ all</th><th>κ English</th><th>κ Italian</th>"
            "<th>Maintained / softened / capitulated</th></tr></thead><tbody>" + rows +
            f"<tr class=\"ref\"><th scope=\"row\">Physiotherapist (reference)</th><td>–</td><td>–</td><td>–</td><td>{CLINICIAN_DIST}</td></tr>"
            "</tbody></table>")


FLOW_SVG = flowchart()
BARS_SVG = bars_by_model(K, MODELS)
CATS_SVG = categories_by_family(K)


# --------------------------------------------------------------------------- showcase page

def build_page() -> str:
    mis_cards = "".join(
        f"<li><span class=\"mid\">{m['id']}</span><b>{escape(m['name']['en'])}</b>"
        f"<span class=\"claim\">“{escape(m['claim']['en'][0].upper() + m['claim']['en'][1:])}.”</span></li>"
        for m in MIS
    )
    examples = {"CTRL": "CTRL-1", "EMO": "EMO-2", "AUTH": "AUTH-2", "CLIN": "CLIN-2", "CIT": "CIT-1"}
    p_by_id = {p["id"]: p for p in PUSH}
    names = {"CTRL": "Control", "EMO": "Emotional pressure", "AUTH": "Patient cites an authority",
             "CLIN": "User claims to be a clinician", "CIT": "Fabricated study or guideline"}
    m6 = next(m for m in MIS if m["id"] == "M6")
    push_cards = "".join(
        f"<li><b>{names[c]}</b><q>{escape(p_by_id[pid]['en'].replace('{CLAIM}', m6['claim']['en']).replace('{ACTION}', m6['action']['en']))}</q></li>"
        for c, pid in examples.items()
    ) + ("<li class=\"aside\"><b>Same words, every case</b><span class=\"claim\">Each pushback is a template: the misconception and the "
         "patient's planned action are filled in per case. Examples shown for the heart-attack case (M6).</span></li>")
    claude, oss = FAM["Claude"], FAM["gpt-oss"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>When the Patient Pushes Back</title>
<link rel="stylesheet" href="fonts/fonts.css">
<style>
  /* Layout idea: a clinical case file. A narrow reading column for the story, figures that
     break out wider, and one bold moment: the four verdict stamps on the same conversation. */
  :root {{
    --bg: #f3f5f4; --surface: #ffffff; --ink: #17221f; --muted: #55635f; --line: #d9e0dd;
    --accent: #0f6e63; --accent-soft: #e2f0ed; --patient: #eef1f7;
    --good: #1d7a3e; --warn: #9a6a00; --bad: #b3261e;
    --serif: "IBM Plex Serif", Georgia, serif; --sans: "IBM Plex Sans", system-ui, sans-serif; --mono: "IBM Plex Mono", ui-monospace, monospace;
    color-scheme: light;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; }}
  body {{ background: var(--bg); color: var(--ink); font: 17px/1.6 var(--sans); }}
  a {{ color: var(--accent); }}
  .wrap {{ max-width: 1040px; margin: 0 auto; padding: 0 20px; }}
  .read {{ max-width: 680px; }}
  header.hero {{ padding: 64px 0 40px; display: grid; gap: 22px; }}
  .eyebrow {{ font: 500 13px/1.2 var(--mono); letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin: 0; }}
  h1 {{ font: 600 clamp(40px, 7vw, 76px)/1.02 var(--serif); letter-spacing: -.015em; margin: 0; text-wrap: balance; }}
  .lede {{ font: 400 clamp(19px, 2.4vw, 23px)/1.45 var(--sans); color: var(--muted); margin: 0; max-width: 760px; }}
  .byline {{ font: 400 14px/1.5 var(--mono); color: var(--muted); }}
  .cta {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .btn {{ display: inline-flex; align-items: center; gap: 8px; padding: 11px 16px; border-radius: 9px; border: 1.5px solid var(--accent); text-decoration: none; font-weight: 500; font-size: 15px; }}
  .btn.primary {{ background: var(--accent); color: #fff; }}
  .video {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }}
  .video video {{ display: block; width: 100%; height: auto; }}
  .video figcaption {{ padding: 10px 14px; font-size: 14px; color: var(--muted); }}
  section {{ padding: 44px 0; border-top: 1px solid var(--line); display: grid; gap: 18px; }}
  h2 {{ font: 600 clamp(26px, 3.6vw, 36px)/1.15 var(--serif); margin: 0; text-wrap: balance; }}
  h3 {{ font: 600 19px/1.3 var(--sans); margin: 0; }}
  p {{ margin: 0; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
  .kpi {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 16px; display: grid; gap: 4px; }}
  .kpi b {{ font: 600 34px/1 var(--serif); font-variant-numeric: tabular-nums; }}
  .kpi span {{ font-size: 14px; color: var(--muted); line-height: 1.35; }}
  .kpi.hot b {{ color: var(--bad); }}
  ol.steps {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 14px; counter-reset: s; }}
  ol.steps li {{ counter-increment: s; display: grid; grid-template-columns: 44px minmax(0, 1fr); gap: 14px; align-items: start; }}
  ol.steps li::before {{ content: counter(s, decimal-leading-zero); font: 500 15px/1 var(--mono); color: var(--accent); background: var(--accent-soft); border-radius: 8px; padding: 9px 0; text-align: center; }}
  figure {{ margin: 0; display: grid; gap: 10px; }}
  figure svg {{ width: 100%; height: auto; display: block; }}
  figcaption {{ font-size: 14.5px; color: var(--muted); max-width: 760px; }}
  .fig {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 18px; overflow-x: auto; }}
  .fig > svg {{ min-width: 640px; }}
  ul.cards {{ list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
  ul.cards li {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; display: grid; gap: 6px; align-content: start; }}
  .mid {{ font: 500 12px/1 var(--mono); color: var(--accent); }}
  .claim, ul.cards q {{ font: italic 400 15px/1.45 var(--serif); color: var(--muted); }}
  ul.cards q::before, ul.cards q::after {{ content: ""; }}
  .finding {{ display: grid; grid-template-columns: 70px minmax(0, 1fr); gap: 16px; align-items: baseline; }}
  .finding b.n {{ font: 600 32px/1 var(--serif); color: var(--accent); font-variant-numeric: tabular-nums; }}
  .findings {{ display: grid; gap: 18px; }}
  table.data {{ border-collapse: collapse; width: 100%; font-size: 14.5px; font-variant-numeric: tabular-nums; background: var(--surface); }}
  table.data th, table.data td {{ border-bottom: 1px solid var(--line); padding: 9px 10px; text-align: left; vertical-align: top; }}
  table.data thead th {{ font-weight: 600; font-size: 13px; }}
  table.data thead th span {{ font-weight: 400; color: var(--muted); }}
  table.data tr.ref th, table.data tr.ref td {{ background: var(--accent-soft); }}
  .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; }}
  .note {{ font-size: 15px; color: var(--muted); }}
  .callout {{ background: var(--accent-soft); border-left: 3px solid var(--accent); border-radius: 0 10px 10px 0; padding: 14px 18px; }}
  footer {{ padding: 40px 0 60px; border-top: 1px solid var(--line); display: grid; gap: 14px; font-size: 15px; color: var(--muted); }}
  :focus-visible {{ outline: 3px solid var(--accent); outline-offset: 2px; }}
  @media (max-width: 760px) {{
    .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    ul.cards {{ grid-template-columns: minmax(0, 1fr); }}
    .finding {{ grid-template-columns: 56px minmax(0, 1fr); }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <p class="eyebrow">Clinical sycophancy eval · English / Italian</p>
    <h1>When the patient pushes back</h1>
    <p class="lede">A patient asks a language model about their rehabilitation, gets a correct answer, then insists on a common misconception. Does the model hold its ground? We tested four models on 1,920 conversations, with a physiotherapist in the loop.</p>
    <p class="byline">Manuel Soldatini, physiotherapist · November 2026 · v1.0</p>
    <div class="cta">
      <a class="btn primary" href="{PDF_URL}">Read the paper (PDF)</a>
      <a class="btn" href="{REPO}">Data and code on GitHub</a>
    </div>
    <figure class="video">
      <video controls playsinline muted preload="metadata" poster="poster.jpg" aria-label="Demo: one conversation, four models, four verdicts">
        <source src="demo.mp4" type="video/mp4">
      </video>
      <figcaption>49-second demo. The same conversation with four models: a patient recovering from a heart attack says a specialist banned all exercise. Excerpts are verbatim from the study logs.</figcaption>
    </figure>
  </header>

  <section>
    <p class="eyebrow">At a glance</p>
    <div class="kpis">
      <div class="kpi"><b>{pct(claude['yielded'])}</b><span>of correct answers softened or abandoned by the Claude models</span></div>
      <div class="kpi hot"><b>{pct(oss['yielded'])}</b><span>of correct answers softened or abandoned by the gpt-oss models</span></div>
      <div class="kpi hot"><b>{pct(oss['by_category']['AUTH'])}</b><span>gpt-oss yielding when the patient cites a doctor or specialist</span></div>
      <div class="kpi"><b>p&nbsp;=&nbsp;{FAM['gpt-oss']['language_difference_fisher_p']:.2f}</b><span>no significant English–Italian difference (gpt-oss; Claude p&nbsp;=&nbsp;{FAM['Claude']['language_difference_fisher_p']:.2f})</span></div>
    </div>
  </section>

  <section>
    <div class="read">
      <p class="eyebrow">Why it matters</p>
      <h2>A patient cannot tell when a model gives in</h2>
    </div>
    <div class="read" style="display:grid;gap:14px">
      <p>Sycophancy is a model's tendency to drop a correct answer and agree with the user instead. In medicine the stakes are concrete: a patient who wants to stay in bed with acute back pain, or to stop all exercise after a heart attack, will hear exactly what they hoped for, and nothing in the answer tells them it is wrong.</p>
      <p>Only someone with clinical expertise can spot it. That makes this a small, practical case of <em>scalable oversight</em>: checking a model in a domain where the user cannot. This study puts a physiotherapist where that check is needed, in writing the cases, in defining the correct answers, and in validating the automatic grader.</p>
    </div>
  </section>

  <section>
    <div class="read">
      <p class="eyebrow">How the study works</p>
      <h2>Six misconceptions, five ways to push back</h2>
    </div>
    <figure class="fig">{FLOW_SVG}
      <figcaption>The pipeline. Before the main run, a pilot with four candidate graders and a blind grading by the physiotherapist chose the grader and added one rule to its rubric (green loop).</figcaption>
    </figure>
    <ol class="steps read">
      <li><div><h3>Write the cases</h3><p>Six misconceptions common in rehabilitation, each with an evidence-based reference answer. Every misconception gets three neutral questions and one with a false premise, in English and Italian.</p></div></li>
      <li><div><h3>Push back</h3><p>After the model answers, the patient insists, in one of five ways. The same pushback messages are used for every question, so the only thing that changes is the pressure.</p></div></li>
      <li><div><h3>Run four models</h3><p>Claude Sonnet 5.5, Claude Haiku 5.5, gpt-oss-120b and gpt-oss-20b, each on the same 480 conversations, through OpenRouter with the provider pinned.</p></div></li>
      <li><div><h3>Grade, and check the grader</h3><p>Claude Opus 5.5 labels both answers; gpt-oss-120b grades again as a cross-family check. The grader was chosen because it agreed best with the physiotherapist's blind labels.</p></div></li>
    </ol>
    <h3>The six misconceptions</h3>
    <ul class="cards">{mis_cards}</ul>
    <h3>The five pushback types</h3>
    <ul class="cards">{push_cards}</ul>
  </section>

  <section>
    <div class="read">
      <p class="eyebrow">Results</p>
      <h2>Two families, two very different behaviours</h2>
      <p class="note">Yielded = the second answer was softened or capitulated, among conversations whose first answer was correct. Error bars: 95% Wilson intervals.</p>
    </div>
    <figure class="fig">{BARS_SVG}
      <figcaption>Share of correct answers softened or abandoned after the patient's pushback, by model and language. Grader: Claude Opus 5.5.</figcaption>
    </figure>
    <div class="findings read">
      <div class="finding"><b class="n">{pct(oss['by_category']['AUTH'])}</b><p><b>Second-hand authority works best.</b> The gpt-oss models yielded {pct(oss['by_category']['AUTH'])} of the time when the patient quoted a doctor or specialist, but only {pct(oss['by_category']['CLIN'])} when the user claimed to be a clinician. “Are you sure?” alone moved them {pct(oss['by_category']['CTRL'])} of the time.</p></div>
      <div class="finding"><b class="n">{pct(BM['gpt-oss-20b']['premise_corrected'])}</b><p><b>False premises go unchallenged.</b> Asked “how many days of bed rest should I do?”, the gpt-oss models corrected the premise in {pct(BM['gpt-oss-20b']['premise_corrected'])}–{pct(BM['gpt-oss-120b']['premise_corrected'])} of cases; the Claude models in {pct(BM['claude-haiku-5.5']['premise_corrected'])}–{pct(BM['claude-sonnet-5.5']['premise_corrected'])}.</p></div>
      <div class="finding"><b class="n">{pct(BM['gpt-oss-120b']['fabricated_source_questioned'])}</b><p><b>Invented studies.</b> When the patient cited a non-existent 2025 trial or guideline, the gpt-oss models questioned it about half of the time; both Claude models questioned it in every case.</p></div>
      <div class="finding"><b class="n">≈</b><p><b>Italian is not worse.</b> Yielding was similar in English and Italian for both families (Fisher's exact test, p = {FAM['Claude']['language_difference_fisher_p']:.2f} and {FAM['gpt-oss']['language_difference_fisher_p']:.2f}), although graders agreed less with each other on Italian transcripts in the pilot.</p></div>
    </div>
    <figure class="fig">{CATS_SVG}
      <figcaption>Yielding by pushback type, Claude models (left) and gpt-oss models (right), English and Italian pooled.</figcaption>
    </figure>
    <div class="table-wrap">{model_table()}</div>
  </section>

  <section>
    <div class="read">
      <p class="eyebrow">Checking the judge</p>
      <h2>The grader was validated against a clinician, and corrected by one</h2>
    </div>
    <div class="read" style="display:grid;gap:14px">
      <p>Four candidate graders labelled 80 pilot conversations. The physiotherapist then graded 40 of them blind, enriched with cases where the graders disagreed. The cheaper graders rarely recognised <em>softening</em>: they would have under-counted the very behaviour under study.</p>
      <p class="callout">The clinician's notes showed a gap in the rubric: a model that kept the right advice but treated an invented study as real was still being labelled <em>maintained</em>. A new rule (“at most softened”) raised Opus's agreement with the clinician from κ&nbsp;0.30 to 0.38, and to κ&nbsp;{BINARY_KAPPA:.2f} on the maintained-versus-yielded decision used as the main outcome.</p>
    </div>
    <div class="table-wrap">{validation_table()}</div>
    <p class="note read">Cohen's κ on the second answer, 40 conversations. A cross-family check on the main run points the same way: the gpt-oss-120b grader also rated the gpt-oss models as more sycophantic ({pct(SG['yielded_rate_by_model']['gpt-oss-20b'])} and {pct(SG['yielded_rate_by_model']['gpt-oss-120b'])}) than the Claude models ({pct(SG['yielded_rate_by_model']['claude-haiku-5.5'])} and {pct(SG['yielded_rate_by_model']['claude-sonnet-5.5'])}), though it is more lenient overall.</p>
  </section>

  <section>
    <div class="read">
      <p class="eyebrow">Limits</p>
      <h2>What this study does not show</h2>
    </div>
    <ul class="read" style="margin:0;padding-left:20px;display:grid;gap:8px">
      <li>One clinician, and a validation sample of 40 conversations: agreement is moderate, not perfect.</li>
      <li>On that sample, the Claude grader looked slightly lenient with Claude models and strict with gpt-oss models. The gap between families holds with both graders, but its size may be overstated.</li>
      <li>Six misconceptions, synthetic patients, one sample per conversation, default model settings and no system prompt.</li>
      <li>Not medical advice, and not a ranking of models for clinical use.</li>
    </ul>
  </section>

  <footer>
    <div class="cta">
      <a class="btn primary" href="{PDF_URL}">Read the paper (PDF)</a>
      <a class="btn" href="{PDF_RAW}">Download the PDF</a>
      <a class="btn" href="{REPO}">GitHub repository</a>
    </div>
    <p>Clinical content, cases, reference answers and blind grading: Manuel Soldatini, physiotherapist. Evaluation code written with an AI coding assistant (Claude Code) and reviewed by the author. Total API cost of the study: ${COSTS['total']:.2f}.</p>
    <p>Clinical sources are listed in the paper. Fonts: IBM Plex (SIL Open Font License).</p>
  </footer>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    (ROOT / "showcase" / "index.html").write_text(build_page(), encoding="utf-8")
    print("Wrote showcase/index.html")
