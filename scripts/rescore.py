"""Re-grade existing eval logs with the current grader prompt, without regenerating answers.

Usage:
  python scripts/rescore.py --log-dir logs/trial --out logs/rescore \
      --graders claude-opus-5.5 claude-opus-5.5-low --only human_review/answer_key.csv

--only restricts re-grading to the conversations listed in a CSV with model and
sample_id columns (e.g. the clinician's answer key), to keep validation cheap.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
from inspect_ai import score  # noqa: E402
from inspect_ai.log import list_eval_logs, read_eval_log, write_eval_log  # noqa: E402

from clinical_sycophancy import clinical_grader  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--graders", nargs="+", required=True)
    parser.add_argument("--only", help="CSV with model and sample_id columns")
    args = parser.parse_args()

    os.environ.setdefault("OPENROUTER_API_KEY", "proxy-injected")
    keep = None
    if args.only:
        only = pd.read_csv(args.only)
        keep = set(zip(only.model, only.sample_id))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for info in list_eval_logs(args.log_dir):
        target = out / Path(info.name).name
        if target.exists():
            print(f"skipping {target.name}: already re-graded")
            continue
        log = read_eval_log(info)
        if log.status != "success" or not log.samples:
            continue
        model = (log.eval.metadata or {}).get("target_key") or log.eval.model
        if keep is not None:
            log.samples = [s for s in log.samples if (model, s.id) in keep]
        if not log.samples:
            continue
        print(f"{model}: re-grading {len(log.samples)} conversations with {', '.join(args.graders)}")
        scored = score(log, scorers=[clinical_grader(graders=args.graders)], action="overwrite", display="none")
        write_eval_log(scored, str(target))


if __name__ == "__main__":
    main()
